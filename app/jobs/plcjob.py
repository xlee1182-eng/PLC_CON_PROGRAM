import asyncio
from fastapi import APIRouter, Request
from app.plc_drivers.opcua_async import AsyncOPCUAPLC
from app.plc_drivers.mitsubishi_async import AsyncMitsubishiPLC
from app.plc_ctl.plc_manager import AsyncPLCManager
import app.configs.AppConfig as __CONFIG_APPCONFIG

APPCONFIG = __CONFIG_APPCONFIG.GET()


async def START():
    try:
         
        plc_list = []

        for plc_type, plc_config in APPCONFIG['PLC_INFO'].items():
            if plc_config['USEYN'] == 'Y':
                    if plc_type == 'OPCUA':
                        plc = AsyncOPCUAPLC(
                            name=plc_config['NAME'],
                            ip=plc_config['IP'],
                            port=plc_config['PORT'],
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
        manager = AsyncPLCManager(plc_list)
        await manager.start()

    except Exception as e:
        print({e})


