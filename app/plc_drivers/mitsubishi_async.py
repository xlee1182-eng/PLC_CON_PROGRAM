import asyncio
from loguru import logger

from app.plc_ctl.base_plc import BaseAsyncPLC
from app.plc_ctl.reconnect import backoff_retry


class AsyncMitsubishiPLC(BaseAsyncPLC):
    """Asynchronous wrapper around a Mitsubishi MC protocol client.

    Uses :class:`pymcprotocol.type3e.Type3E` internally.  Since the
    underlying library is strictly synchronous we delegate all I/O
    operations to ``asyncio.to_thread`` which keeps the public API
    non‑blocking.

    ``tags`` are expected to be a string (single device) or an iterable
    of device addresses (e.g. ``"D100"``, ``"C0"``).  Only word reads
    are implemented for simplicity; bit devices could be added later by
    calling ``batchread_bitunits`` when the tag starts with ``X``/``Y``.
    """

    def __init__(self, name, ip, port=5006, plctype="Q", tags=None):
        super().__init__(name, ip, port, tags=tags)
        self.plctype = plctype
        self.client = None
        self._io_lock = asyncio.Lock()
        self._subscription_task = None
        self._change_callback = None
        self._last_values = {}
        self._baseline_initialized = False

    def _normalize_read_result(self, data):
        if data is None:
            return {}
        if isinstance(data, dict):
            return data
        tag = self.tags if not isinstance(self.tags, (list, tuple)) else "__value__"
        return {tag: data}

    def _is_bit_device(self, address):
        if not isinstance(address, str) or not address:
            return False
        return address[0].upper() in ("X", "Y", "M", "L", "F", "B")

    def _coerce_scalar_for_write(self, value, is_bit):
        if is_bit:
            if isinstance(value, bool):
                return 1 if value else 0
            if isinstance(value, (int, float)):
                iv = int(value)
                if iv not in (0, 1):
                    raise ValueError(f"bit device value must be 0 or 1, got {value}")
                return iv
            if isinstance(value, str):
                s = value.strip().lower()
                if s in ("1", "true", "t", "y", "yes", "on"):
                    return 1
                if s in ("0", "false", "f", "n", "no", "off"):
                    return 0
            raise ValueError(f"unsupported bit device value: {value}")

        # word device
        if isinstance(value, bool):
            iv = 1 if value else 0
        elif isinstance(value, int):
            iv = value
        elif isinstance(value, float):
            if not value.is_integer():
                raise ValueError(f"word device value must be integer-like, got {value}")
            iv = int(value)
        elif isinstance(value, str):
            s = value.strip()
            if s == "":
                raise ValueError("word device value cannot be empty string")
            iv = int(float(s)) if "." in s else int(s)
        else:
            raise ValueError(f"unsupported word device value type: {type(value)}")

        # Convert signed 16-bit range to unsigned representation used by word writes.
        if -32768 <= iv < 0:
            iv = 65536 + iv

        if not (0 <= iv <= 65535):
            raise ValueError(f"word device value out of range (0..65535 or -32768..32767), got {value}")

        return iv

    def _prepare_write_values(self, address, value):
        is_bit = self._is_bit_device(address)
        if isinstance(value, (list, tuple)):
            values = [self._coerce_scalar_for_write(v, is_bit) for v in value]
        else:
            values = [self._coerce_scalar_for_write(value, is_bit)]
        return is_bit, values

    async def _monitor_changes(self, interval):
        while self._change_callback is not None:
            try:
                if not self.connected:
                    await self.connect()
                    if not self.connected:
                        await asyncio.sleep(interval)
                        continue

                data = await self.read()
                values = self._normalize_read_result(data)

                # First successful snapshot is baseline only (no event emit).
                if not self._baseline_initialized:
                    self._last_values.update(values)
                    self._baseline_initialized = True
                    await asyncio.sleep(interval)
                    continue

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
                logger.error(f"{self.name} Mitsubishi subscription monitor error: {e}")

            await asyncio.sleep(interval)

    async def subscribe_datachange(self, callback, publishing_interval=100):
        self._change_callback = callback
        interval = max(publishing_interval / 1000, 0.1)
        self._baseline_initialized = False
        self._last_values = {}

        if self._subscription_task is None or self._subscription_task.done():
            self._subscription_task = asyncio.create_task(self._monitor_changes(interval))

        logger.info(f"{self.name} Mitsubishi subscription monitor started ({interval}s)")
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

    async def connect(self):
        try:
            self.client = await asyncio.to_thread(self._create_client)
            self.connected = True
            self.retry_count = 0
            logger.info(f"{self.name} connected (Mitsubishi MC protocol)")
        except Exception as e:
            logger.error(f"{self.name} Mitsubishi connect error: {e}")
            self.connected = False
            self.retry_count += 1
            await backoff_retry(self.retry_count)

    def _create_client(self):
        # this runs in a thread pool
        from pymcprotocol import Type3E

        client = Type3E(self.plctype)
        client.connect(self.ip, self.port)
        return client

    async def read(self):
        async with self._io_lock:
            if not self.connected:
                await self.connect()
                return None

            try:
                if isinstance(self.tags, (list, tuple)):
                    values = {}
                    for tag in self.tags:
                        res = await asyncio.to_thread(
                            self.client.batchread_wordunits, tag, 1
                        )
                        values[tag] = res[0] if res else None
                    return values

                res = await asyncio.to_thread(
                    self.client.batchread_wordunits, self.tags, 1
                )
                return res[0] if res else None
            except Exception as e:
                logger.error(f"{self.name} Mitsubishi read error: {e}")
                self.connected = False
                self.retry_count += 1
                await backoff_retry(self.retry_count)
                return None

    async def read_tag(self, address):
        async with self._io_lock:
            if not self.connected:
                await self.connect()
                if not self.connected:
                    return None

            try:
                res = await asyncio.to_thread(
                    self.client.batchread_wordunits, address, 1
                )
                return res[0] if res else None
            except Exception as e:
                logger.error(f"{self.name} Mitsubishi read_tag error: {e}")
                self.connected = False
                self.retry_count += 1
                await backoff_retry(self.retry_count)
                return None

    async def write(self, address, value):
        async with self._io_lock:
            try:
                is_bit, values = self._prepare_write_values(address, value)
                if is_bit:
                    await asyncio.to_thread(
                        self.client.batchwrite_bitunits, address, values
                    )
                else:
                    await asyncio.to_thread(
                        self.client.batchwrite_wordunits, address, values
                    )
            except Exception as e:
                logger.error(f"{self.name} Mitsubishi write error: {e}")

    async def close(self):
        try:
            await self.unsubscribe_datachange()
            await asyncio.to_thread(self.client.close)
        except Exception:
            pass
