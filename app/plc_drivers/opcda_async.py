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
                        # OpenOPC returns (value, quality, timestamp) for single reads
                        values[tag] = res[0] if isinstance(res, (list, tuple)) and len(res) > 0 else res
                    else:
                        val = await loop.run_in_executor(None, lambda t=tag: getattr(self.client, 'Read', lambda x: None)(t))
                        values[tag] = val
                return values

            tag = self.tags
            if HAS_OPENOPC:
                res = await loop.run_in_executor(None, lambda: self.client.read(tag))
                return res[0] if isinstance(res, (list, tuple)) and len(res) > 0 else res
            else:
                return await loop.run_in_executor(None, lambda: getattr(self.client, 'Read', lambda x: None)(tag))

        except Exception as e:
            logger.error(f"{self.name} OPC DA read error: {e}")
            self.connected = False
            self.retry_count += 1
            await backoff_retry(self.retry_count)

    async def write(self, address, value):
        loop = asyncio.get_running_loop()
        try:
            if HAS_OPENOPC:
                # OpenOPC write API accepts tuple or list
                await loop.run_in_executor(None, lambda: self.client.write((address, value)))
            else:
                await loop.run_in_executor(None, lambda: getattr(self.client, 'Write', lambda a, v: None)(address, value))
        except Exception as e:
            logger.error(f"{self.name} OPC DA write error: {e}")

    async def close(self):
        try:
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
