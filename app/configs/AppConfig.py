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
            'PLC_INFO': configData['PLC_INFO'],
        }
        
            
        logger.info(f'================================================================')
        logger.info(f'LAST UPDATED DATE: 2026-03-17')
        for plc_type, plc_config in APPCONFIG['PLC_INFO'].items():
            if plc_config['USEYN'] == 'Y':
                logger.info(f'PLC_TYPE: {plc_type}')
                logger.info(f'PLC_NAME: {plc_config["NAME"]}')
                logger.info(f'PLC_IP  : {plc_config["IP"]}')
                logger.info(f'PLC_PORT: {plc_config["PORT"]}')
                logger.info(f' ')
        logger.info(f'================================================================')
    except Exception as e:
        logger.error(f"AppConfig SET error: {e}")

def GET():
  return APPCONFIG