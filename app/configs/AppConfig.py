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
            'WAS_IP': configData['WAS_IP'],
            'WAS_PORT': configData['WAS_PORT'],
            'PLC_TAGS': configData['PLC_TAGS'],
        }
        
            
        logger.info(f'================================================================')
        logger.info(f'LAST UPDATED DATE: 2025-07-14')
        logger.info(f'WAS - IP: {configData["WAS_IP"]}')
        logger.info(f'WAS - PORT: {configData["WAS_PORT"]}')
        logger.info(f'================================================================')
    except Exception as e:
        logger.error(f"AppConfig SET error: {e}")

def GET():
  return APPCONFIG