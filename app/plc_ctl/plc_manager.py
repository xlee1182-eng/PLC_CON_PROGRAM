import asyncio
import signal
from loguru import logger

class AsyncPLCManager:

    def __init__(self, plc_list):
        self.plc_list = plc_list
        self.running = True
        self._tasks = []
        self._change_queue = asyncio.Queue()
        self._change_handlers = []

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
        plc = next((p for p in self.plc_list if p.name == plc_name), None)

        if plc is None:
            raise Exception(f"PLC '{plc_name}' not found")

        return await self.write_once(plc, data)      

    async def read_by_name(self, plc_name: str, tag: str):
        """
        PLC 이름과 태그로 1회 읽기
        """
        plc = next((p for p in self.plc_list if p.name == plc_name), None)

        if plc is None:
            raise Exception(f"PLC '{plc_name}' not found")

        return await self.read_once(plc, tag)

    async def read_once(self, plc, tag: str):
        """
        특정 PLC의 특정 태그 1회 읽기
        """
        try:
            if hasattr(plc, "read_tag"):
                value = await plc.read_tag(tag)
            else:
                data = await plc.read()
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
                await plc.write(tag, value)
                tag_type = self._classify_tag(tag)
                formatted = self._format_value(tag, value)
                logger.info(f"[WRITE] {plc.name}.{tag} [{tag_type}] <- {formatted}")

            return True

        except Exception as e:
            logger.error(f"{plc.name} write_once error: {e}")
            return False