import asyncio
# from fastapi import APIRouter, Request
from app.plc_drivers.opcua_async import AsyncOPCUAPLC
from app.plc_drivers.opcda_async import AsyncOPCDA
from app.plc_drivers.mitsubishi_async import AsyncMitsubishiPLC
from app.plc_ctl.plc_manager import AsyncPLCManager
import app.configs.AppConfig as __CONFIG_APPCONFIG

APPCONFIG = __CONFIG_APPCONFIG.GET()
PLC_MANAGER = None


def GET_PLC_MANAGER():
    return PLC_MANAGER



async def START():
    global PLC_MANAGER

    plc_list = []
    
    try:

        for plc_type, plc_config in APPCONFIG['PLC_INFO'].items():
            if plc_config['USEYN'] == 'Y':
                    if plc_type == 'OPCUA':
                        plc = AsyncOPCUAPLC(
                            name=plc_config['NAME'],
                            ip=plc_config['IP'],
                            port=plc_config['PORT'],
                            tags=plc_config['TAGS']
                        )
                    elif plc_type == 'OPCDA':
                        plc = AsyncOPCDA(
                            name=plc_config['NAME'],
                            ip=plc_config['IP'],
                            port=plc_config['PORT'],
                            prog_id=plc_config.get('PROG_ID'),
                            tags=plc_config['TAGS']
                        )
                    elif plc_type == 'MITSUBISHI':
                        plc = AsyncMitsubishiPLC(
                            name=plc_config['NAME'],
                            ip=plc_config['IP'],
                            port=plc_config['PORT'],
                            tags=plc_config['TAGS']
                        )
                    plc_list.append(plc)

        # ------------------------------------------------------------------
        # start the manager with all configured PLCs
        PLC_MANAGER = AsyncPLCManager(plc_list)
        await PLC_MANAGER.start()

    except Exception as e:
        print({e})


