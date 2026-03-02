import asyncio
import signal
from loguru import logger

class AsyncPLCManager:

    def __init__(self, plc_list):
        self.plc_list = plc_list
        self.running = True
        self._tasks = []

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

        self._tasks = [asyncio.create_task(self.poll_plc(plc)) for plc in self.plc_list]
        try:
            await asyncio.gather(*self._tasks)
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