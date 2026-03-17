import asyncio

from loguru import logger

from app.plc_drivers.base_plc import BaseAsyncPLC
from app.plc_drivers.reconnect import backoff_retry


def _optional_import(module_name):
    try:
        return __import__(module_name, fromlist=["*"])
    except Exception:
        return None


_PYCOMM3 = _optional_import("pycomm3")
HAS_PYCOMM3 = _PYCOMM3 is not None


class AsyncRockwellPLC(BaseAsyncPLC):
    """Asynchronous Rockwell/Allen-Bradley driver using pycomm3 LogixDriver.

    Tags are Logix symbolic tag names (e.g. "Program:Main.TagA", "TagB[0]").
    """

    def __init__(
        self,
        name,
        ip,
        port=44818,
        slot=0,
        path=None,
        tags=None,
        subscription_mode="auto",
        active_poll_ms=100,
        idle_poll_ms=1000,
        burst_cycles=10,
    ):
        super().__init__(name, ip, port, tags=tags)
        self.slot = slot
        self.path = path
        self.client = None
        self._io_lock = asyncio.Lock()
        self._subscription_task = None
        self._change_callback = None
        self._last_values = {}
        self._baseline_initialized = False
        self.subscription_mode = str(subscription_mode).lower()
        self._active_interval = max(float(active_poll_ms) / 1000.0, 0.05)
        self._idle_interval = max(float(idle_poll_ms) / 1000.0, self._active_interval)
        self._burst_cycles = max(int(burst_cycles), 1)

    def _is_adaptive_mode(self):
        return self.subscription_mode in ("auto", "adaptive", "semi-push")

    def _build_connection_path(self):
        if self.path:
            return self.path
        return f"{self.ip}:{self.port}/{self.slot}"

    def _normalize_read_result(self, data):
        if data is None:
            return {}
        if isinstance(data, dict):
            return data
        tag = self.tags if not isinstance(self.tags, (list, tuple)) else "__value__"
        return {tag: data}

    def _extract_tag_result(self, result):
        if result is None:
            return None

        # pycomm3 Tag object typically has these attributes.
        tag_name = getattr(result, "tag", None)
        error = getattr(result, "error", None)
        value = getattr(result, "value", None)

        if error:
            raise RuntimeError(f"read error ({tag_name}): {error}")

        if tag_name is not None:
            return tag_name, value

        return None, result

    def _read_sync(self, tags):
        if isinstance(tags, (list, tuple)):
            return self.client.read(*tags)
        return self.client.read(tags)

    def _write_sync(self, address, value):
        return self.client.write((address, value))

    async def _monitor_changes(self, interval):
        adaptive = self._is_adaptive_mode()
        current_interval = self._idle_interval if adaptive else interval
        burst_left = 0

        while self._change_callback is not None:
            try:
                if not self.connected:
                    await self.connect()
                    if not self.connected:
                        await asyncio.sleep(current_interval)
                        continue

                data = await self.read()
                values = self._normalize_read_result(data)
                has_change = False

                if not self._baseline_initialized:
                    self._last_values.update(values)
                    self._baseline_initialized = True
                    await asyncio.sleep(current_interval)
                    continue

                for tag, value in values.items():
                    old_value = self._last_values.get(tag)
                    if tag in self._last_values and old_value != value:
                        has_change = True
                        event = {
                            "plc": self.name,
                            "tag": tag,
                            "value": value,
                            "old_value": old_value,
                        }
                        result = self._change_callback(event)
                        if asyncio.iscoroutine(result):
                            asyncio.create_task(result)
                    self._last_values[tag] = value
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error(f"{self.name} Rockwell subscription monitor error: {e}")

            if adaptive:
                if has_change:
                    burst_left = self._burst_cycles
                    current_interval = self._active_interval
                elif burst_left > 0:
                    burst_left -= 1
                    current_interval = self._active_interval
                else:
                    current_interval = self._idle_interval

            await asyncio.sleep(current_interval)

    async def subscribe_datachange(self, callback, publishing_interval=100):
        self._change_callback = callback
        interval = max(publishing_interval / 1000, 0.1)

        if self.subscription_mode == "push":
            logger.warning(f"{self.name} Rockwell native push is unavailable, fallback to adaptive polling")
            self.subscription_mode = "auto"

        self._baseline_initialized = False
        self._last_values = {}

        if self._subscription_task is None or self._subscription_task.done():
            self._subscription_task = asyncio.create_task(self._monitor_changes(interval))

        logger.info(f"{self.name} Rockwell subscription monitor started ({interval}s)")
        return True

    async def unsubscribe_datachange(self):
        self._change_callback = None
        if self._subscription_task is not None:
            self._subscription_task.cancel()
            try:
                await self._subscription_task
            except asyncio.CancelledError:
                pass
        self._subscription_task = None
        self._last_values = {}
        self._baseline_initialized = False

    def _create_client(self):
        if not HAS_PYCOMM3:
            raise RuntimeError("pycomm3 is not installed")

        driver = _PYCOMM3.LogixDriver(self._build_connection_path())
        driver.open()
        return driver

    async def connect(self):
        try:
            if self.client is not None:
                await asyncio.to_thread(self.client.close)
            self.client = await asyncio.to_thread(self._create_client)
            self.connected = True
            self.retry_count = 0
            logger.info(f"{self.name} connected (Rockwell Logix)")
        except Exception as e:
            logger.error(f"{self.name} Rockwell connect error: {e}")
            self.connected = False
            self.retry_count += 1
            await backoff_retry(self.retry_count)

    async def read_tag(self, address):
        async with self._io_lock:
            if not self.connected:
                await self.connect()
                if not self.connected:
                    return None

            try:
                raw = await asyncio.to_thread(self._read_sync, address)
                _, value = self._extract_tag_result(raw)
                return value
            except Exception as e:
                logger.error(f"{self.name} Rockwell read_tag error: {e}")
                self.connected = False
                self.retry_count += 1
                await backoff_retry(self.retry_count)
                return None

    async def read(self):
        async with self._io_lock:
            if not self.connected:
                await self.connect()
                if not self.connected:
                    return None

            try:
                if isinstance(self.tags, (list, tuple)):
                    raw_results = await asyncio.to_thread(self._read_sync, self.tags)
                    values = {}
                    for item in raw_results:
                        tag_name, value = self._extract_tag_result(item)
                        if tag_name is not None:
                            values[tag_name] = value
                    return values

                if self.tags is None:
                    return None

                raw = await asyncio.to_thread(self._read_sync, self.tags)
                _, value = self._extract_tag_result(raw)
                return value
            except Exception as e:
                logger.error(f"{self.name} Rockwell read error: {e}")
                self.connected = False
                self.retry_count += 1
                await backoff_retry(self.retry_count)
                return None

    async def write(self, address, value):
        async with self._io_lock:
            if not self.connected:
                await self.connect()
                if not self.connected:
                    raise Exception(f"{self.name} Rockwell not connected")

            try:
                result = await asyncio.to_thread(self._write_sync, address, value)
                error = getattr(result, "error", None)
                if error:
                    raise RuntimeError(f"write error ({address}): {error}")
            except Exception as e:
                logger.error(f"{self.name} Rockwell write error: {e}")
                self.connected = False
                self.retry_count += 1
                await backoff_retry(self.retry_count)
                raise

    async def close(self):
        try:
            await self.unsubscribe_datachange()
            if self.client is not None:
                await asyncio.to_thread(self.client.close)
        except Exception:
            pass
        finally:
            self.connected = False
            self.client = None
