import asyncio
from app.plc_ctl.base_plc import BaseAsyncPLC
from app.plc_ctl.reconnect import backoff_retry
from loguru import logger

try:
    import OpenOPC
    HAS_OPENOPC = True
except Exception:
    HAS_OPENOPC = False

try:
    import win32com.client as win32
    HAS_WIN32 = True
except Exception:
    HAS_WIN32 = False


class AsyncOPCDA(BaseAsyncPLC):

    def __init__(self, name, ip, port=0, prog_id=None, tags=None):
        super().__init__(name, ip, port, tags=tags)
        self.prog_id = prog_id
        self.client = None
        self._io_lock = asyncio.Lock()
        self._subscription_task = None
        self._change_callback = None
        self._last_values = {}

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
            if HAS_OPENOPC:
                # OpenOPC.client() is blocking; run in executor
                self.client = await loop.run_in_executor(None, OpenOPC.client)
                print(self.client.servers())
                if not self.prog_id:
                    logger.error(f"{self.name} OPC DA prog_id not provided (OpenOPC)")
                    self.connected = False
                    return
                await loop.run_in_executor(None, lambda: self.client.connect(self.prog_id))

            elif HAS_WIN32:
                if not self.prog_id:
                    logger.error(f"{self.name} OPC DA prog_id required for win32com")
                    self.connected = False
                    return
                def _connect_win():
                    return win32.Dispatch(self.prog_id)
                self.client = await loop.run_in_executor(None, _connect_win)

            else:
                logger.error(f"{self.name} No OpenOPC or pywin32 available for OPC DA")
                self.connected = False
                return

            self.connected = True
            self.retry_count = 0
            logger.info(f"{self.name} connected (OPC DA)")

        except Exception as e:
            logger.error(f"{self.name} OPC DA connect error: {e}")
            self.connected = False
            self.retry_count += 1
            await backoff_retry(self.retry_count)

    async def read(self):
        async with self._io_lock:
            if not self.connected:
                await self.connect()
                if not self.connected:
                    return None

            loop = asyncio.get_running_loop()
            try:
                if isinstance(self.tags, (list, tuple)):
                    values = {}
                    for tag in self.tags:
                        if HAS_OPENOPC:
                            res = await loop.run_in_executor(None, lambda t=tag: self.client.read(t))
                            values[tag] = res[0] if isinstance(res, (list, tuple)) and len(res) > 0 else res
                        else:
                            val = await loop.run_in_executor(None, lambda t=tag: getattr(self.client, 'Read', lambda x: None)(t))
                            values[tag] = val
                    return values

                tag = self.tags
                if HAS_OPENOPC:
                    res = await loop.run_in_executor(None, lambda: self.client.read(tag))
                    return res[0] if isinstance(res, (list, tuple)) and len(res) > 0 else res
                return await loop.run_in_executor(None, lambda: getattr(self.client, 'Read', lambda x: None)(tag))

            except Exception as e:
                logger.error(f"{self.name} OPC DA read error: {e}")
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

            loop = asyncio.get_running_loop()
            try:
                if HAS_OPENOPC:
                    res = await loop.run_in_executor(None, lambda: self.client.read(address))
                    return res[0] if isinstance(res, (list, tuple)) and len(res) > 0 else res
                return await loop.run_in_executor(None, lambda: getattr(self.client, 'Read', lambda x: None)(address))
            except Exception as e:
                logger.error(f"{self.name} OPC DA read_tag error: {e}")
                self.connected = False
                self.retry_count += 1
                await backoff_retry(self.retry_count)
                return None

    async def write(self, address, value):
        async with self._io_lock:
            loop = asyncio.get_running_loop()
            try:
                if HAS_OPENOPC:
                    await loop.run_in_executor(None, lambda: self.client.write((address, value)))
                else:
                    await loop.run_in_executor(None, lambda: getattr(self.client, 'Write', lambda a, v: None)(address, value))
            except Exception as e:
                logger.error(f"{self.name} OPC DA write error: {e}")

    async def close(self):
        try:
            await self.unsubscribe_datachange()
            if not self.client:
                return
            loop = asyncio.get_running_loop()
            if HAS_OPENOPC:
                await loop.run_in_executor(None, self.client.close)
            else:
                # win32com Dispatch objects do not need explicit close in many cases
                await loop.run_in_executor(None, lambda: None)
        except Exception:
            pass
