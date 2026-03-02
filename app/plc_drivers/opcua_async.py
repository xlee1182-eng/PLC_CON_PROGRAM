from asyncua import Client
from app.plc_ctl.base_plc import BaseAsyncPLC
from app.plc_ctl.reconnect import backoff_retry
from loguru import logger


class AsyncOPCUAPLC(BaseAsyncPLC):

    def __init__(self, name, ip, port=4840, node_id="ns=2;i=2", tags=None):
        # ``node_id`` is kept for backwards compatibility. ``tags`` may be a
        # list of node ids.  The base class stores ``tags`` generically.
        super().__init__(name, ip, port, tags=tags or node_id)
        self.node_id = node_id
        self.client = None

    async def connect(self):
        try:
            self.client = Client(f"opc.tcp://{self.ip}:{self.port}")
            await self.client.connect()
            self.connected = True
            self.retry_count = 0
            logger.info(f"{self.name} connected (OPC UA)")
        except Exception as e:
            logger.error(f"{self.name} OPC UA connect error: {e}")
            self.connected = False
            self.retry_count += 1
            await backoff_retry(self.retry_count)

    async def read(self):

        if not self.connected:
            await self.connect()
            return None

        try:
            # multiple node ids
            if isinstance(self.tags, (list, tuple)):
                values = {}
                for nid in self.tags:
                    node = self.client.get_node(nid)
                    values[nid] = await node.read_value()
                return values

            node = await self.client.get_node(self.node_id)
            value = await node.read_value()
            return value
        except Exception as e:
            logger.error(f"{self.name} OPC UA read error: {e}")
            self.connected = False
            self.retry_count += 1
            await backoff_retry(self.retry_count)

    async def write(self, value, node_id=None):
        nid = node_id or self.node_id
        try:
            node = await self.client.get_node(nid)
            await node.write_value(value)
        except Exception as e:
            logger.error(f"{self.name} OPC UA write error: {e}")

    async def close(self):
        try:
            await self.client.disconnect()
        except Exception:
            pass
