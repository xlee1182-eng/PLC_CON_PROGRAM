import asyncio
import re
import struct

from loguru import logger

from app.plc_drivers.base_plc import BaseAsyncPLC
from app.plc_drivers.reconnect import backoff_retry


def _optional_import(module_name):
    try:
        return __import__(module_name, fromlist=["*"])
    except Exception:
        return None


_SNAP7 = _optional_import("snap7")
HAS_SNAP7 = _SNAP7 is not None


class AsyncSiemensPLC(BaseAsyncPLC):
    """Asynchronous Siemens S7 driver using python-snap7.

    Address examples:
    - DB1.DBW0, DB1.DBD4, DB1.DBX0.0, DB1.DBB10
    - M10.0, MB20, MW30, MD40
    - I0.0, IB2, IW4, ID8
    - Q0.0, QB2, QW4, QD8
    """

    _DB_RE = re.compile(r"^DB(\d+)\.DB([XBWDI])(\d+)(?:\.(\d+))?$", re.IGNORECASE)
    _AREA_RE = re.compile(r"^([MIQ])([XBWDI]?)(\d+)(?:\.(\d+))?$", re.IGNORECASE)

    _AREA_DB = 0x84
    _AREA_PE = 0x81
    _AREA_PA = 0x82
    _AREA_MK = 0x83

    def __init__(
        self,
        name,
        ip,
        port=102,
        rack=0,
        slot=1,
        tags=None,
        subscription_mode="auto",
        active_poll_ms=100,
        idle_poll_ms=1000,
        burst_cycles=10,
    ):
        super().__init__(name, ip, port, tags=tags)
        self.rack = rack
        self.slot = slot
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

    def _normalize_read_result(self, data):
        if data is None:
            return {}
        if isinstance(data, dict):
            return data
        tag = self.tags if not isinstance(self.tags, (list, tuple)) else "__value__"
        return {tag: data}

    def _parse_address(self, address):
        if not isinstance(address, str) or not address.strip():
            raise ValueError("Invalid Siemens address")

        raw = address.strip().upper()

        m = self._DB_RE.match(raw)
        if m:
            db_num = int(m.group(1))
            dtype = m.group(2)
            offset = int(m.group(3))
            bit = int(m.group(4)) if m.group(4) is not None else None
            if dtype == "X":
                if bit is None:
                    raise ValueError(f"Bit index required for {address}")
                if bit < 0 or bit > 7:
                    raise ValueError(f"Bit index out of range for {address}")
                return {
                    "is_db": True,
                    "db": db_num,
                    "area": self._AREA_DB,
                    "offset": offset,
                    "bit": bit,
                    "dtype": "X",
                    "size": 1,
                }
            size = {"B": 1, "W": 2, "D": 4, "I": 2}[dtype]
            return {
                "is_db": True,
                "db": db_num,
                "area": self._AREA_DB,
                "offset": offset,
                "bit": None,
                "dtype": dtype,
                "size": size,
            }

        m = self._AREA_RE.match(raw)
        if m:
            area_letter = m.group(1)
            dtype = m.group(2) or "X"
            offset = int(m.group(3))
            bit = int(m.group(4)) if m.group(4) is not None else None

            area = {
                "M": self._AREA_MK,
                "I": self._AREA_PE,
                "Q": self._AREA_PA,
            }[area_letter]

            if dtype == "X":
                if bit is None:
                    bit = 0
                if bit < 0 or bit > 7:
                    raise ValueError(f"Bit index out of range for {address}")
                return {
                    "is_db": False,
                    "db": 0,
                    "area": area,
                    "offset": offset,
                    "bit": bit,
                    "dtype": "X",
                    "size": 1,
                }

            size = {"B": 1, "W": 2, "D": 4, "I": 2}[dtype]
            return {
                "is_db": False,
                "db": 0,
                "area": area,
                "offset": offset,
                "bit": None,
                "dtype": dtype,
                "size": size,
            }

        raise ValueError(f"Unsupported Siemens address format: {address}")

    def _decode_value(self, spec, data):
        dtype = spec["dtype"]

        if dtype == "X":
            return bool((data[0] >> spec["bit"]) & 1)
        if dtype == "B":
            return int(data[0])
        if dtype == "W":
            return int.from_bytes(data, byteorder="big", signed=False)
        if dtype == "I":
            return int.from_bytes(data, byteorder="big", signed=True)
        if dtype == "D":
            return struct.unpack(">f", bytes(data))[0]

        return int.from_bytes(data, byteorder="big", signed=False)

    def _encode_value(self, spec, value, current_data=None):
        dtype = spec["dtype"]

        if dtype == "X":
            if isinstance(value, str):
                v = value.strip().lower() in ("1", "true", "t", "y", "yes", "on")
            else:
                v = bool(value)
            base = bytearray(current_data if current_data is not None else b"\x00")
            if v:
                base[0] |= 1 << spec["bit"]
            else:
                base[0] &= ~(1 << spec["bit"])
            return bytes(base)

        if dtype == "B":
            iv = int(value)
            if not (0 <= iv <= 255):
                raise ValueError("Byte value out of range (0..255)")
            return iv.to_bytes(1, byteorder="big", signed=False)

        if dtype == "W":
            iv = int(value)
            if not (0 <= iv <= 65535):
                raise ValueError("Word value out of range (0..65535)")
            return iv.to_bytes(2, byteorder="big", signed=False)

        if dtype == "I":
            iv = int(value)
            if not (-32768 <= iv <= 32767):
                raise ValueError("Int16 value out of range (-32768..32767)")
            return iv.to_bytes(2, byteorder="big", signed=True)

        if dtype == "D":
            return struct.pack(">f", float(value))

        raise ValueError(f"Unsupported dtype for encode: {dtype}")

    def _read_block(self, spec):
        if spec["is_db"]:
            return self.client.db_read(spec["db"], spec["offset"], spec["size"])
        return self.client.read_area(spec["area"], spec["db"], spec["offset"], spec["size"])

    def _write_block(self, spec, payload):
        if spec["is_db"]:
            self.client.db_write(spec["db"], spec["offset"], payload)
            return
        self.client.write_area(spec["area"], spec["db"], spec["offset"], payload)

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
                logger.error(f"{self.name} Siemens subscription monitor error: {e}")

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
            logger.warning(f"{self.name} Siemens native push is unavailable, fallback to adaptive polling")
            self.subscription_mode = "auto"

        self._baseline_initialized = False
        self._last_values = {}

        if self._subscription_task is None or self._subscription_task.done():
            self._subscription_task = asyncio.create_task(self._monitor_changes(interval))

        logger.info(f"{self.name} Siemens subscription monitor started ({interval}s)")
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
        if not HAS_SNAP7:
            raise RuntimeError("python-snap7 is not installed")

        client = _SNAP7.client.Client()
        # TCP 102 is implicit in snap7 connect; ip/rack/slot are used.
        client.connect(self.ip, int(self.rack), int(self.slot), int(self.port))
        if not client.get_connected():
            raise RuntimeError("Failed to connect Siemens PLC")
        return client

    async def connect(self):
        try:
            if self.client is not None:
                await asyncio.to_thread(self.client.disconnect)
            self.client = await asyncio.to_thread(self._create_client)
            self.connected = True
            self.retry_count = 0
            logger.info(f"{self.name} connected (Siemens S7)")
        except Exception as e:
            logger.error(f"{self.name} Siemens connect error: {e}")
            self.connected = False
            self.retry_count += 1
            await backoff_retry(self.retry_count)

    async def read_tag(self, address):
        spec = self._parse_address(address)

        async with self._io_lock:
            if not self.connected:
                await self.connect()
                if not self.connected:
                    return None

            try:
                raw = await asyncio.to_thread(self._read_block, spec)
                return self._decode_value(spec, raw)
            except Exception as e:
                logger.error(f"{self.name} Siemens read_tag error: {e}")
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
                    values = {}
                    for tag in self.tags:
                        spec = self._parse_address(tag)
                        raw = await asyncio.to_thread(self._read_block, spec)
                        values[tag] = self._decode_value(spec, raw)
                    return values

                if self.tags is None:
                    return None

                spec = self._parse_address(self.tags)
                raw = await asyncio.to_thread(self._read_block, spec)
                return self._decode_value(spec, raw)
            except Exception as e:
                logger.error(f"{self.name} Siemens read error: {e}")
                self.connected = False
                self.retry_count += 1
                await backoff_retry(self.retry_count)
                return None

    async def write(self, address, value):
        spec = self._parse_address(address)

        async with self._io_lock:
            if not self.connected:
                await self.connect()
                if not self.connected:
                    raise Exception(f"{self.name} Siemens not connected")

            try:
                current = None
                if spec["dtype"] == "X":
                    current = await asyncio.to_thread(self._read_block, spec)
                payload = self._encode_value(spec, value, current_data=current)
                await asyncio.to_thread(self._write_block, spec, payload)
            except Exception as e:
                logger.error(f"{self.name} Siemens write error: {e}")
                self.connected = False
                self.retry_count += 1
                await backoff_retry(self.retry_count)
                raise

    async def close(self):
        try:
            await self.unsubscribe_datachange()
            if self.client is not None:
                await asyncio.to_thread(self.client.disconnect)
        except Exception:
            pass
        finally:
            self.connected = False
            self.client = None
