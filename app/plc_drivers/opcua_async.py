import asyncio
from asyncua import Client, ua
from app.plc_drivers.base_plc import BaseAsyncPLC
from app.plc_drivers.reconnect import backoff_retry
from loguru import logger


class _OPCUADataChangeHandler:
    def __init__(self, plc):
        self._plc = plc

    def datachange_notification(self, node, val, data):
        self._plc.on_datachange(node, val, data)


class AsyncOPCUAPLC(BaseAsyncPLC):

    def __init__(self, name, ip, port=4840, node_id="ns=2;i=2", tags=None):
        # ``node_id`` is kept for backwards compatibility. ``tags`` may be a
        # list of node ids.  The base class stores ``tags`` generically.
        super().__init__(name, ip, port, tags=tags or node_id)
        self.node_id = node_id
        self.client = None
        self._io_lock = asyncio.Lock()
        self._subscription = None
        self._subscription_handles = []
        self._change_callback = None
        self._publishing_interval = 100

    async def _invalidate_connection(self):
        self.connected = False
        if self._subscription is not None:
            try:
                await self._subscription.delete()
            except Exception:
                pass
        self._subscription = None
        self._subscription_handles = []
        if self.client is not None:
            try:
                await self.client.disconnect()
            except Exception:
                pass
        self.client = None

    def _coerce_write_value(self, value, variant_type):
        # Convert basic inbound types to match node datatype when possible.
        if variant_type == ua.VariantType.Boolean:
            if isinstance(value, str):
                return value.strip().lower() in ("1", "true", "t", "y", "yes", "on")
            return bool(value)

        if variant_type in (
            ua.VariantType.SByte,
            ua.VariantType.Byte,
            ua.VariantType.Int16,
            ua.VariantType.UInt16,
            ua.VariantType.Int32,
            ua.VariantType.UInt32,
            ua.VariantType.Int64,
            ua.VariantType.UInt64,
        ):
            return int(value)

        if variant_type in (ua.VariantType.Float, ua.VariantType.Double):
            return float(value)

        if variant_type == ua.VariantType.String:
            return str(value)

        return value

    async def connect(self):
        try:
            if self.client is not None:
                try:
                    await self.client.disconnect()
                except Exception:
                    pass
            self.client = Client(f"opc.tcp://{self.ip}:{self.port}")
            await self.client.connect()
            self.connected = True
            self.retry_count = 0

            # Re-create datachange subscription automatically after reconnect.
            if self._change_callback is not None and self._subscription is None:
                await self._subscribe_datachange_no_lock(
                    callback=self._change_callback,
                    publishing_interval=self._publishing_interval,
                )

            logger.info(f"{self.name} connected (OPC UA)")
        except Exception as e:
            logger.error(f"{self.name} OPC UA connect error: {e}")
            await self._invalidate_connection()
            self.retry_count += 1
            await backoff_retry(self.retry_count)

    async def _subscribe_datachange_no_lock(self, callback, publishing_interval=100):
        self._change_callback = callback
        self._publishing_interval = publishing_interval

        if not self.connected or self.client is None:
            return False

        if self._subscription is not None:
            return True

        try:
            handler = _OPCUADataChangeHandler(self)
            self._subscription = await self.client.create_subscription(publishing_interval, handler)

            node_ids = self.tags if isinstance(self.tags, (list, tuple)) else [self.node_id]
            nodes = [self.client.get_node(nid) for nid in node_ids]
            handles = await self._subscription.subscribe_data_change(nodes)
            if isinstance(handles, list):
                self._subscription_handles = handles
            else:
                self._subscription_handles = [handles]

            logger.info(f"{self.name} OPC UA datachange subscribed ({len(nodes)} nodes)")
            return True
        except Exception as e:
            logger.error(f"{self.name} OPC UA subscribe error: {e}")
            if self._subscription is not None:
                try:
                    await self._subscription.delete()
                except Exception:
                    pass
            self._subscription = None
            self._subscription_handles = []
            return False

    def on_datachange(self, node, value, data):
        if self._change_callback is None:
            return

        event = {
            "plc": self.name,
            "tag": str(node.nodeid),
            "value": value,
            "source_timestamp": None,
        }

        try:
            monitored = getattr(data, "monitored_item", None)
            if monitored is not None and getattr(monitored, "Value", None) is not None:
                event["source_timestamp"] = monitored.Value.SourceTimestamp
        except Exception:
            pass

        try:
            result = self._change_callback(event)
            if asyncio.iscoroutine(result):
                asyncio.create_task(result)
        except Exception as e:
            logger.error(f"{self.name} datachange callback error: {e}")

    async def subscribe_datachange(self, callback, publishing_interval=100):
        self._change_callback = callback
        self._publishing_interval = publishing_interval

        async with self._io_lock:
            if not self.connected or self.client is None:
                await self.connect()
                if not self.connected or self.client is None:
                    return False
            return await self._subscribe_datachange_no_lock(callback, publishing_interval)

    async def unsubscribe_datachange(self):
        async with self._io_lock:
            if self._subscription is None:
                return
            try:
                if self._subscription_handles:
                    await self._subscription.unsubscribe(self._subscription_handles)
                await self._subscription.delete()
            except Exception:
                pass
            finally:
                self._subscription = None
                self._subscription_handles = []

    async def read(self):
        async with self._io_lock:
            if not self.connected or self.client is None:
                await self.connect()
                if not self.connected or self.client is None:
                    return None

            try:
                # multiple node ids
                if isinstance(self.tags, (list, tuple)):
                    values = {}
                    for nid in self.tags:
                        node = self.client.get_node(nid)
                        values[nid] = await node.read_value()
                    return values

                node = self.client.get_node(self.node_id)
                value = await node.read_value()
                return value
            except Exception as e:
                logger.error(f"{self.name} OPC UA read error: {e}")
                await self._invalidate_connection()
                self.retry_count += 1
                await backoff_retry(self.retry_count)
                return None

    async def read_tag(self, address):
        nid = address or self.node_id
        async with self._io_lock:
            if not self.connected or self.client is None:
                await self.connect()
                if not self.connected or self.client is None:
                    return None

            try:
                node = self.client.get_node(nid)
                return await node.read_value()
            except Exception as e:
                logger.error(f"{self.name} OPC UA read_tag error: {e}")
                await self._invalidate_connection()
                self.retry_count += 1
                await backoff_retry(self.retry_count)
                return None

    async def write(self, address, value):
        nid = address or self.node_id
        async with self._io_lock:
            if not self.connected or self.client is None:
                await self.connect()
                if not self.connected or self.client is None:
                    raise Exception(f"{self.name} OPC UA not connected")

            try:
                node = self.client.get_node(nid)
                variant_type = await node.read_data_type_as_variant_type()
                casted_value = self._coerce_write_value(value, variant_type)
                variant_value = ua.Variant(casted_value, variant_type)
                # Prefer explicit Value-only DataValue to avoid unsupported
                # status/timestamp combinations on strict OPC UA servers.
                dv = ua.DataValue(Value=variant_value)
                try:
                    await node.write_attribute(ua.AttributeIds.Value, dv)
                except Exception as inner_e:
                    if "BadWriteNotSupported" not in str(inner_e):
                        raise
                    # Fallback path for servers with non-standard handling.
                    await node.write_value(casted_value)
            except Exception as e:
                logger.error(f"{self.name} OPC UA write error: {e}")
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
