import asyncio
from importlib import import_module
from app.plc_drivers.base_plc import BaseAsyncPLC
from app.plc_drivers.reconnect import backoff_retry
from loguru import logger


def _optional_import(module_name):
    try:
        return import_module(module_name)
    except Exception:
        return None


_OPENOPC = _optional_import("OpenOPC")
_WIN32_CLIENT = _optional_import("win32com.client")
HAS_OPENOPC = _OPENOPC is not None
HAS_WIN32 = _WIN32_CLIENT is not None


class AsyncOPCDA(BaseAsyncPLC):

    def __init__(self, name, ip, port=0, prog_id=None, tags=None):
        super().__init__(name, ip, port, tags=tags)
        self.prog_id = prog_id
        self.client = None
        self._driver = None
        self._io_lock = asyncio.Lock()
        self._subscription_task = None
        self._change_callback = None
        self._last_values = {}

    async def _invalidate_connection(self):
        self.connected = False
        self._driver = None
        self._last_values = {}

        if self.client is None:
            return

        loop = asyncio.get_running_loop()
        try:
            if hasattr(self.client, "close") and callable(self.client.close):
                await loop.run_in_executor(None, self.client.close)
        except Exception:
            pass
        finally:
            self.client = None

    def _extract_openopc_value(self, result):
        if result is None:
            return None

        # OpenOPC often returns tuples like: (tag, value, quality, timestamp)
        if isinstance(result, tuple):
            if len(result) >= 2 and isinstance(result[0], str):
                return result[1]
            if len(result) > 0:
                return result[0]
            return None

        if isinstance(result, list):
            if not result:
                return None

            first = result[0]
            if isinstance(first, tuple) and len(result) == 1:
                return self._extract_openopc_value(first)

            return first

        return result

    async def _read_single(self, address):
        loop = asyncio.get_running_loop()

        if self._driver == "openopc":
            raw = await loop.run_in_executor(None, lambda: self.client.read(address))
            return self._extract_openopc_value(raw)

        read_fn = getattr(self.client, "Read", None)
        if not callable(read_fn):
            raise Exception("win32com client has no Read method")
        return await loop.run_in_executor(None, lambda: read_fn(address))

    async def _write_single(self, address, value):
        loop = asyncio.get_running_loop()

        if self._driver == "openopc":
            await loop.run_in_executor(None, lambda: self.client.write((address, value)))
            return

        write_fn = getattr(self.client, "Write", None)
        if not callable(write_fn):
            raise Exception("win32com client has no Write method")
        await loop.run_in_executor(None, lambda: write_fn(address, value))

    def _normalize_read_result(self, data):
        if data is None:
            return {}
        if isinstance(data, dict):
            return data
        tag = self.tags if not isinstance(self.tags, (list, tuple)) else "__value__"
        return {tag: data}

    async def _monitor_changes(self, interval):
        while self.connected and self._change_callback is not None:
            try:
                data = await self.read()
                values = self._normalize_read_result(data)
                for tag, value in values.items():
                    old_value = self._last_values.get(tag)
                    if tag in self._last_values and old_value != value:
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
                logger.error(f"{self.name} OPC DA subscription monitor error: {e}")

            await asyncio.sleep(interval)

    async def subscribe_datachange(self, callback, publishing_interval=100):
        self._change_callback = callback
        interval = max(publishing_interval / 1000, 0.1)

        if not self.connected:
            await self.connect()
            if not self.connected:
                return False

        if self._subscription_task is None or self._subscription_task.done():
            self._subscription_task = asyncio.create_task(self._monitor_changes(interval))

        logger.info(f"{self.name} OPC DA subscription monitor started ({interval}s)")
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

    async def connect(self):
        try:
            loop = asyncio.get_running_loop()

            if self.client is not None:
                await self._invalidate_connection()

            if HAS_OPENOPC:
                self.client = await loop.run_in_executor(None, _OPENOPC.client)
                if not self.prog_id:
                    logger.error(f"{self.name} OPC DA prog_id not provided (OpenOPC)")
                    self.connected = False
                    return
                await loop.run_in_executor(None, lambda: self.client.connect(self.prog_id))
                self._driver = "openopc"

            elif HAS_WIN32:
                if not self.prog_id:
                    logger.error(f"{self.name} OPC DA prog_id required for win32com")
                    self.connected = False
                    return

                def _connect_win():
                    return _WIN32_CLIENT.Dispatch(self.prog_id)

                self.client = await loop.run_in_executor(None, _connect_win)
                self._driver = "win32"

            else:
                logger.error(f"{self.name} No OpenOPC or pywin32 available for OPC DA")
                self.connected = False
                raise Exception("No OPC DA client library available")
                # await self._invalidate_connection()
                # self.retry_count += 1
                # await backoff_retry(self.retry_count)
                # return

            self.connected = True
            self.retry_count = 0
            logger.info(f"{self.name} connected (OPC DA)")

        except Exception as e:
            logger.error(f"{self.name} OPC DA connect error: {e}")
            await self._invalidate_connection()
            self.retry_count += 1
            await backoff_retry(self.retry_count)

    async def read(self):
        async with self._io_lock:
            if not self.connected or self.client is None:
                await self.connect()
                if not self.connected or self.client is None:
                    return None

            try:
                if isinstance(self.tags, (list, tuple)):
                    values = {}
                    for tag in self.tags:
                        values[tag] = await self._read_single(tag)
                    return values

                tag = self.tags
                if tag is None:
                    return None
                return await self._read_single(tag)

            except Exception as e:
                logger.error(f"{self.name} OPC DA read error: {e}")
                await self._invalidate_connection()
                self.retry_count += 1
                await backoff_retry(self.retry_count)
                return None

    async def read_tag(self, address):
        async with self._io_lock:
            if not self.connected or self.client is None:
                await self.connect()
                if not self.connected or self.client is None:
                    return None

            try:
                return await self._read_single(address)
            except Exception as e:
                logger.error(f"{self.name} OPC DA read_tag error: {e}")
                await self._invalidate_connection()
                self.retry_count += 1
                await backoff_retry(self.retry_count)
                return None

    async def write(self, address, value):
        async with self._io_lock:
            if not self.connected or self.client is None:
                await self.connect()
                if not self.connected or self.client is None:
                    raise Exception(f"{self.name} OPC DA not connected")

            try:
                await self._write_single(address, value)
            except Exception as e:
                logger.error(f"{self.name} OPC DA write error: {e}")
                await self._invalidate_connection()
                self.retry_count += 1
                await backoff_retry(self.retry_count)
                raise

    async def close(self):
        try:
            await self.unsubscribe_datachange()
            await self._invalidate_connection()
        except Exception:
            pass
