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

            # single tag
            res = await asyncio.to_thread(
                self.client.batchread_wordunits, self.tags, 1
            )
            return res[0] if res else None
        except Exception as e:
            logger.error(f"{self.name} Mitsubishi read error: {e}")
            self.connected = False
            self.retry_count += 1
            await backoff_retry(self.retry_count)

    async def write(self, address, value):
        try:
            if isinstance(value, (list, tuple)):
                values = list(value)
            else:
                values = [value]
            await asyncio.to_thread(
                self.client.batchwrite_wordunits, address, values
            )
        except Exception as e:
            logger.error(f"{self.name} Mitsubishi write error: {e}")

    async def close(self):
        try:
            await asyncio.to_thread(self.client.close)
        except Exception:
            pass
