# import time
import traceback
import threading
from loguru import logger
# from app.plc_drivers.plc_manager import PLC_DATA
from app.plc_drivers.plc_manager import PLC_DATA_VIEW

_stop_event = threading.Event()
_job_thread = None

def initialize():
    logger.info("MyJob initialized")

def print_plc_data():
    """PLC_DATA_VIEW를 출력합니다."""
    try:
        while not _stop_event.is_set():

            _stop_event.wait(10)

            if not PLC_DATA_VIEW:
                logger.warning("PLC_DATA_VIEW is empty")
            else:
                for plc_name, plc_info in PLC_DATA_VIEW.items():
                    if not isinstance(plc_info, dict):
                        logger.warning(f"  unexpected data type: {type(plc_info).__name__}")
                        continue

                    connected = plc_info.get("connected", False)
                    tags_map = plc_info.get("tags", {})

                    if not connected:
                        logger.warning(f"PLC {plc_name} is disconnected")
                        continue

                    for tag, entry in tags_map.items():
                        if isinstance(entry, dict):
                            tag_type = entry.get("tag_type", "unknown")
                            value = entry.get("value")
                        else:
                            tag_type = "unknown"
                            value = entry
                        logger.info(f"PLC:[{plc_name}.{tag}] TYPE:[{tag_type}] VALUE:[{value}]")

            # return
    except:
        logger.error(traceback.format_exc())

    

if __name__ == "__main__":
    logger.info("MyJob standalone test")


def print_plc_data_once():
    """한 번만 PLC_DATA를 출력합니다."""
    if not PLC_DATA_VIEW:
        logger.warning("PLC_DATA_VIEW is empty")
        return

    for plc_name, plc_info in PLC_DATA_VIEW.items():
        if not isinstance(plc_info, dict):
            logger.warning(f"  unexpected data type: {type(plc_info).__name__}")
            continue

        connected = plc_info.get("connected", False)
        tags_map = plc_info.get("tags", {})

        if not connected:
            logger.warning(f"PLC {plc_name} is disconnected")
            continue

        for tag, entry in tags_map.items():
            if isinstance(entry, dict):
                tag_type = entry.get("tag_type", "unknown")
                value = entry.get("value")
            else:
                tag_type = "unknown"
                value = entry
            logger.info(f"PLC:[{plc_name}.{tag}] TYPE:[{tag_type}] VALUE:[{value}]")

def START():
    global _job_thread
    try:
        initialize()
        _stop_event.clear()
        _job_thread = threading.Thread(target=print_plc_data, daemon=True)
        _job_thread.start()
    except Exception:
        logger.error(traceback.format_exc())


def STOP(timeout: float = 5.0):
    """Stop the MyJob background thread cleanly."""
    _stop_event.set()
    if _job_thread is not None:
        _job_thread.join(timeout)
