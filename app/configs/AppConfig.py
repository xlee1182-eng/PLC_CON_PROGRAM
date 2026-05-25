import os
import json
import requests
from loguru import logger

APPCONFIG = None

def SET():
    global APPCONFIG

    try:
        # load app configuration
        file = os.path.join(os.getcwd(), 'Config.json')
        with open(file, 'r', encoding = 'UTF8') as file:
            configData = json.load(file)

        ## local file 사용여부 확인
        if configData['USE_LOCAL_FILE']:

            APPCONFIG = {
                # 'WAS_IP': configData['WAS_IP'],
                # 'WAS_PORT': configData['WAS_PORT'],
                'PLC_LIST': configData['PLC_LIST'],
            }
        else:
        ## DB에 저장되어 있는 값으로 configuration 설정
            headers = {
                'Content-Type': 'application/jsonl charset=utf-8',
                'SITE_ID': configData['SITE_ID'],
                'SYSTEM_ID': configData['SYSTEM_ID'],
                'LOGIN_USER_ID': 'ocu'
            }

            initConfURL = f'http://{configData['WAS_IP']}:{str(configData['WAS_PORT'])}/initconf?IN_WORK_PLACE_CODE={configData['WORK_PLACE_CODE']}&IN_CONFIG_CLASS_GROUP={configData['CONFIG_CLASS_GROUP']}&IN_HA_APP_ID={str(configData['HA_APP_ID'])}'

            configResponse = requests.get(initConfURL, headers = headers)

            if configResponse.json()['isSuccess']:
                APPCONFIG = {
                                'WAS_IP': configData['WAS_IP'],
                                'WAS_PORT': configData['WAS_PORT'],
                                'PLC_LIST': configData['PLC_LIST']
                }
            else:
                logger.error('FAIL', 'Could not get app configuration..')
            
        logger.info(f'================================================================')
        logger.info(f'LAST UPDATED DATE: 2026-05-25')
        logger.info(f'USE LOCAL FILE: {configData['USE_LOCAL_FILE']}')
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