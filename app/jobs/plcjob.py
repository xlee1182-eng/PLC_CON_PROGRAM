import asyncio
# from fastapi import APIRouter, Request
from app.plc_drivers.opcua_async import AsyncOPCUAPLC
from app.plc_drivers.mitsubishi_async import AsyncMitsubishiPLC
from app.plc_ctl.plc_manager import AsyncPLCManager
import app.configs.AppConfig as __CONFIG_APPCONFIG

APPCONFIG = __CONFIG_APPCONFIG.GET()

async def START():
    
    plc_list = []
    # OPC UA PLC 예시 (여러 node_id를 모니터링할 수 있도록 tags 리스트 사용)
    for i in range(1, 2):
        plc = AsyncOPCUAPLC(
            name=f"OPCUA_{i}",
            ip=f"127.0.0.{i}",
            port=49320,
            # tags=["ns=2;s=Channel2.Device2.D1001", 
            #       "ns=2;s=Channel2.Device2.D1002",
            #       "ns=2;s=Channel2.Device2.D1003",
            #       "ns=2;s=Channel2.Device2.D1004",
            #       "ns=2;s=Channel2.Device2.D1005",
            #       "ns=2;s=Channel2.Device2.S0000",
            #       "ns=2;s=Channel2.Device2.S0001",]
            tags=APPCONFIG['PLC_TAGS']
        )
        plc_list.append(plc)

    # Mitsubishi PLC 예시 (MC protocol)
    for i in range(1, 2):
        mitsu = AsyncMitsubishiPLC(
            name=f"MITSU_{i}",
            ip="192.168.2.210",
            port=3000,
            tags=["D1001", "D1002", "D1003"]
        )
        plc_list.append(mitsu)

    # ------------------------------------------------------------------
    # start the manager with all configured PLCs
    manager = AsyncPLCManager(plc_list)
    await manager.start()

