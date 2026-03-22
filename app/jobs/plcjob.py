import asyncio
from loguru import logger
# from fastapi import APIRouter, Request
from app.plc_drivers.driver_factory import create_driver
from app.plc_drivers.plc_manager import AsyncPLCManager
import app.configs.AppConfig as __CONFIG_APPCONFIG

APPCONFIG = __CONFIG_APPCONFIG.GET()
PLC_MANAGER = None


def GET_PLC_MANAGER():
    return PLC_MANAGER



async def START():
    global PLC_MANAGER

    plc_list = []
    
    try:

        for plc_config in APPCONFIG.get('PLC_LIST', []):
            if plc_config.get('USEYN') == 'Y':
                try:
                    plc_type = plc_config.get('TYPE')
                    plc = create_driver(plc_type, plc_config)
                    plc_list.append(plc)
                except Exception as e:
                    plc_name = plc_config.get('NAME', 'Unknown')
                    logger.error(f'PLC build error ({plc_name}): {e}')

        # ------------------------------------------------------------------
        # start the manager with all configured PLCs
        PLC_MANAGER = AsyncPLCManager(plc_list)
        logger.info(f'PLC manager initialized: {len(plc_list)} PLC(s)')
        await PLC_MANAGER.start()

    except Exception as e:
        logger.error(f'PLC job start error: {e}')


async def STOP():
    global PLC_MANAGER

    if PLC_MANAGER is None:
        return

    try:
        await PLC_MANAGER.stop()
    finally:
        PLC_MANAGER = None


