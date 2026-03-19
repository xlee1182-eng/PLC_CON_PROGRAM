import asyncio
import signal
import os
from loguru import logger

class AsyncPLCManager:

    def __init__(self, plc_list):
        self.plc_list = plc_list
        self._plc_map = {}
        self.running = True
        self._tasks = []
        self._change_queue = asyncio.Queue()
        self._change_handlers = []
        raw_timeout = os.getenv("PLC_OPERATION_TIMEOUT_SEC", "3.0")
        try:
            parsed_timeout = float(raw_timeout)
        except (TypeError, ValueError):
            parsed_timeout = 3.0
        self._operation_timeout = parsed_timeout if parsed_timeout > 0 else None
        self._register_plcs(plc_list)

    async def _run_with_timeout(self, coro, context: str):
        if self._operation_timeout is None:
            return await coro

        try:
            return await asyncio.wait_for(coro, timeout=self._operation_timeout)
        except asyncio.TimeoutError as e:
            raise TimeoutError(
                f"{context} timeout after {self._operation_timeout:.1f}s"
            ) from e

    def _register_plcs(self, plc_list):
        self._plc_map = {}
        for plc in plc_list:
            if getattr(plc, "name", None) is None:
                raise ValueError("PLC name is required")
            if plc.name in self._plc_map:
                raise ValueError(f"Duplicate PLC name: {plc.name}")
            self._plc_map[plc.name] = plc

    def get_plc(self, plc_name: str):
        plc = self._plc_map.get(plc_name)
        if plc is None:
            raise Exception(f"PLC '{plc_name}' not found")
        return plc

    def list_plcs(self):
        return [
            {
                "name": plc.name,
                "driver_type": getattr(plc, "driver_type", plc.__class__.__name__),
                "ip": plc.ip,
                "port": plc.port,
                "connected": plc.connected,
                "tags": plc.tags,
                "supports_subscription": hasattr(plc, "subscribe_datachange"),
                "supports_read_tag": hasattr(plc, "read_tag"),
            }
            for plc in self.plc_list
        ]

    def get_manager_status(self):
        running_tasks = sum(1 for t in self._tasks if not t.done())
        return {
            "running": self.running,
            "plc_count": len(self.plc_list),
            "active_poll_tasks": running_tasks,
            "plcs": self.list_plcs(),
        }

    def add_change_handler(self, handler):
        if handler not in self._change_handlers:
            self._change_handlers.append(handler)

    def remove_change_handler(self, handler):
        if handler in self._change_handlers:
            self._change_handlers.remove(handler)

    async def get_change_event(self, timeout=None):
        if timeout is None:
            return await self._change_queue.get()
        return await asyncio.wait_for(self._change_queue.get(), timeout=timeout)

    async def _on_change_event(self, event):
        await self._change_queue.put(event)

        plc_name = event.get("plc")
        tag = event.get("tag")
        value = event.get("value")
        tag_type = self._classify_tag(tag)
        formatted = self._format_value(tag, value)
        logger.info(f"[EVENT] {plc_name}.{tag} [{tag_type}] -> {formatted}")

        for handler in list(self._change_handlers):
            try:
                result = handler(event)
                if asyncio.iscoroutine(result):
                    asyncio.create_task(result)
            except Exception as e:
                logger.error(f"change handler error: {e}")

    def _classify_tag(self, tag):
        """Return a simple classification string for the given tag.

        This is used primarily for logging to annotate each entry with a
        human‑readable type hint.  The categories are intentionally loose and
        can be expanded as needed.
        """
        if not isinstance(tag, str):
            return "unknown"
        t = tag.upper()
        if t.startswith(("D", "W", "R", "ZR")):
            return "word"
        if t.startswith(("X", "Y", "M", "L", "F", "B")):
            return "bit"
        if t.startswith("NS=") or ":" in t:
            return "node"
        return "unknown"

    def _format_value(self, tag, value):
        """Format the read value based on its type and (optionally) tag.

        Numeric values are kept unquoted, whereas strings are wrapped in
        quotes so that logs clearly show they are text.  Additional logic can
        be added later (e.g. decode bytes, apply units, etc.).
        """
        # Display strings as-is (no surrounding quotes) per user preference.
        # Keep non-string values unchanged so numbers remain numeric.
        return value

    async def poll_plc(self, plc):

        while self.running:
            try:
                # Startup can begin in polling mode when the first subscribe
                # attempt fails. Retry subscription and stop polling once it succeeds.
                if hasattr(plc, "subscribe_datachange"):
                    try:
                        subscribed = await plc.subscribe_datachange(self._on_change_event)
                        if subscribed:
                            logger.info(f"{plc.name} switched from polling to subscription mode")
                            return
                    except Exception as sub_e:
                        logger.error(f"{plc.name} subscribe retry error: {sub_e}")

                data = await plc.read()
                if data is not None:
                    # if a PLC returns a mapping we assume it represents
                    # multiple tag values.  Log each entry separately so the
                    # output is easier to trace in a long-running poll loop.
                    if isinstance(data, dict):
                        for tag, value in data.items():
                            tag_type = self._classify_tag(tag)
                            formatted = self._format_value(tag, value)
                            logger.info(f"{plc.name}.{tag} [{tag_type}] -> {formatted}")
                    else:
                        logger.info(f"{plc.name} -> {data}")

            except Exception as e:
                logger.error(f"{plc.name} fatal error: {e}")

            await asyncio.sleep(0.1)   # polling interval

    async def start(self):
        if self._tasks:
            return

        # create background tasks for each PLC poll loop and keep references
        loop = asyncio.get_running_loop()
        # register signal handlers to trigger graceful shutdown
        try:
            loop.add_signal_handler(signal.SIGTERM, lambda: asyncio.create_task(self.stop()))
            loop.add_signal_handler(signal.SIGINT, lambda: asyncio.create_task(self.stop()))
        except NotImplementedError:
            # some event loops (Windows) may not support add_signal_handler
            pass

        self._tasks = []
        for plc in self.plc_list:
            subscribed = False
            try:
                if hasattr(plc, "subscribe_datachange"):
                    subscribed = await plc.subscribe_datachange(self._on_change_event)
            except Exception as e:
                logger.error(f"{plc.name} subscribe_datachange error: {e}")

            if not subscribed:
                self._tasks.append(asyncio.create_task(self.poll_plc(plc)))

        try:
            if self._tasks:
                await asyncio.gather(*self._tasks)
            else:
                while self.running:
                    await asyncio.sleep(0.2)
        except asyncio.CancelledError:
            # allow graceful cancellation
            pass

    async def stop(self):
        """Stop polling and close all PLC connections.

        This sets the running flag to False so poll loops exit, then attempts
        to await each PLC's `close()` coroutine. Finally it cancels any
        outstanding poll tasks.
        """
        self.running = False

        # attempt to close all PLCs
        close_tasks = []
        for plc in self.plc_list:
            try:
                if hasattr(plc, "unsubscribe_datachange"):
                    await plc.unsubscribe_datachange()
                # schedule each close; drivers should expose async close()
                close_tasks.append(asyncio.create_task(plc.close()))
            except Exception:
                # ignore scheduling errors
                pass

        if close_tasks:
            await asyncio.gather(*close_tasks, return_exceptions=True)

        # cancel poll tasks
        for t in list(self._tasks):
            if not t.done():
                t.cancel()

        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)

    async def write_by_name(self, plc_name: str, data: dict):
        """
        PLC 이름으로 쓰기
        """
        plc = self.get_plc(plc_name)
        return await self.write_once(plc, data)      

    async def read_by_name(self, plc_name: str, tag: str):
        """
        PLC 이름과 태그로 1회 읽기
        """
        plc = self.get_plc(plc_name)
        return await self.read_once(plc, tag)

    async def read_plc_tags(self, plc_name: str, tags=None):
        plc = self.get_plc(plc_name)

        if tags is None:
            data = await self._run_with_timeout(plc.read(), f"{plc.name} read")
            if isinstance(data, dict):
                return data
            return {"value": data}

        if isinstance(tags, str):
            tags = [tags]

        result = {}
        for tag in tags:
            result[tag] = await self.read_once(plc, tag)
        return result

    async def read_all_plcs(self, tags_by_plc=None):
        if tags_by_plc is None:
            tags_by_plc = {}

        # If specific PLC names are requested, only read those PLCs.
        request_filter = set(tags_by_plc.keys()) if isinstance(tags_by_plc, dict) else set()

        async def _read_single_plc(plc):
            try:
                request_tags = tags_by_plc.get(plc.name)
                data = await self.read_plc_tags(plc.name, request_tags)
                return plc.name, {
                    "ok": True,
                    "data": data,
                }
            except Exception as e:
                return plc.name, {
                    "ok": False,
                    "error": str(e),
                }

        targets = [
            plc for plc in self.plc_list
            if not request_filter or plc.name in request_filter
        ]

        pairs = await asyncio.gather(*(_read_single_plc(plc) for plc in targets))
        return {name: payload for name, payload in pairs}

    async def write_batch(self, commands):
        """
        commands example:
        [
            {"plc_name": "OPCUA_PLC_1", "data": {"ns=2;s=...": 1}},
            {"plc_name": "MITSU_PLC_1", "data": {"D100": 100}},
        ]
        """
        if not isinstance(commands, list):
            raise ValueError("commands must be a list")

        results = []
        for command in commands:
            plc_name = command.get("plc_name")
            data = command.get("data") or {}

            try:
                await self.write_by_name(plc_name, data)
                results.append({
                    "plc_name": plc_name,
                    "ok": True,
                })
            except Exception as e:
                results.append({
                    "plc_name": plc_name,
                    "ok": False,
                    "error": str(e),
                })

        return results

    async def read_once(self, plc, tag: str):
        """
        특정 PLC의 특정 태그 1회 읽기
        """
        try:
            if hasattr(plc, "read_tag"):
                value = await self._run_with_timeout(
                    plc.read_tag(tag),
                    f"{plc.name} read_tag({tag})",
                )
            else:
                data = await self._run_with_timeout(
                    plc.read(),
                    f"{plc.name} read",
                )
                if isinstance(data, dict):
                    value = data.get(tag)
                else:
                    value = data

            tag_type = self._classify_tag(tag)
            formatted = self._format_value(tag, value)
            logger.info(f"[READ] {plc.name}.{tag} [{tag_type}] -> {formatted}")
            return value

        except Exception as e:
            logger.error(f"{plc.name} read_once error: {e}")
            raise
    
    async def write_once(self, plc, data):
        """
        특정 PLC에 1회 쓰기
        data: dict 형태 {"TAG": value}
        """
        try:
            for tag, value in data.items():
                await self._run_with_timeout(
                    plc.write(tag, value),
                    f"{plc.name} write({tag})",
                )
                tag_type = self._classify_tag(tag)
                formatted = self._format_value(tag, value)
                logger.info(f"[WRITE] {plc.name}.{tag} [{tag_type}] <- {formatted}")

            return True

        except Exception as e:
            logger.error(f"{plc.name} write_once error: {e}")
            return False