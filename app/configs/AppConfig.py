import os
import json
from loguru import logger

APPCONFIG = None

def SET():
    global APPCONFIG

    try:
        # load app configuration
        file = os.path.join(os.getcwd(), 'Config.json')
        with open(file, 'r', encoding = 'UTF8') as file:
            configData = json.load(file)

        APPCONFIG = {
            # 'WAS_IP': configData['WAS_IP'],
            # 'WAS_PORT': configData['WAS_PORT'],
            'PLC_LIST': configData['PLC_LIST'],
        }
        
            
        logger.info(f'================================================================')
        logger.info(f'LAST UPDATED DATE: 2026-03-17')
        for plc_config in APPCONFIG['PLC_LIST']:
            if plc_config.get('USEYN') == 'Y':
                logger.info(f'PLC_TYPE: {plc_config["TYPE"]}')
                logger.info(f'PLC_NAME: {plc_config["NAME"]}')
                logger.info(f'PLC_IP  : {plc_config["IP"]}')
                logger.info(f'PLC_PORT: {plc_config["PORT"]}')
                logger.info(f' ')
        logger.info(f'================================================================')
    except Exception as e:
        logger.error(f"AppConfig SET error: {e}")

def GET():
  return APPCONFIG