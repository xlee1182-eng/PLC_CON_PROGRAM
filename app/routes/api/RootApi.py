from pathlib import Path
import sys
from typing import Any
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Body
from fastapi.responses import FileResponse
from loguru import logger
## functions
import app.functions.CommonFunction as __FUNCTION_COMMON
import app.jobs.plcjob as __JOB_PLC

router = APIRouter()


def _resolve_web_page_path() -> Path:
  # PyInstaller onefile/onedir extracts bundled data under _MEIPASS.
  if getattr(sys, 'frozen', False):
    meipass = getattr(sys, '_MEIPASS', None)
    if meipass:
      return Path(meipass) / 'app' / 'web' / 'dashboard.html'
  return Path(__file__).resolve().parents[2] / 'web' / 'dashboard.html'


WEB_PAGE_PATH = _resolve_web_page_path()


class PLCReadRequest(BaseModel):
  plc_name: str
  tag: str


class PLCWriteRequest(BaseModel):
  plc_name: str
  tag: str
  value: Any

@router.get('/')
def root():
  return __FUNCTION_COMMON.RESPONSEFORMAT('OK', 'The PLC_CON_Program is running now.', None)


@router.get('/web')
def web_dashboard():
  if not WEB_PAGE_PATH.exists():
    raise HTTPException(status_code = 404, detail = 'dashboard.html not found')
  return FileResponse(str(WEB_PAGE_PATH))

@router.post('/api')
def api():
  try:
    data = "model.model_dump()"

    result = data

    return result
  except Exception as e:
                logger.error(f"API route fatal error: {e}")
                
@router.get('/plc_write')
async def plc_write(plc_name: str, tag: str, value: str):

  try:
    # 예시: PLC1의 D100 태그에 123을 쓰기
    plc_manager = __JOB_PLC.GET_PLC_MANAGER()

    if plc_manager is None:
      raise HTTPException(status_code = 503, detail = 'PLC manager is not ready')

    await plc_manager.write_by_name(plc_name, {tag: value})

    return __FUNCTION_COMMON.RESPONSEFORMAT('OK', 'Write command sent to PLC.', None)
  except HTTPException:
    raise
  except Exception as e:
    logger.error(f"API route fatal error: {e}")
    raise HTTPException(status_code = 500, detail = str(e))


@router.get('/plc_read')
async def plc_read(plc_name: str, tag: str):

  try:
    plc_manager = __JOB_PLC.GET_PLC_MANAGER()

    if plc_manager is None:
      raise HTTPException(status_code = 503, detail = 'PLC manager is not ready')

    value = await plc_manager.read_by_name(plc_name, tag)

    return __FUNCTION_COMMON.RESPONSEFORMAT('OK', 'Read command success', {
      'plcName': plc_name,
      'tag': tag,
      'value': value
    })
  except HTTPException:
    raise
  except Exception as e:
    logger.error(f"API route fatal error: {e}")
    raise HTTPException(status_code = 500, detail = str(e))


@router.post('/api/plc/read-tag')
async def plc_read_tag(payload: PLCReadRequest):

  try:
    plc_manager = __JOB_PLC.GET_PLC_MANAGER()

    if plc_manager is None:
      raise HTTPException(status_code = 503, detail = 'PLC manager is not ready')

    value = await plc_manager.read_by_name(payload.plc_name, payload.tag)

    return __FUNCTION_COMMON.RESPONSEFORMAT('OK', 'Read command success', {
      'plcName': payload.plc_name,
      'tag': payload.tag,
      'value': value
    })
  except HTTPException:
    raise
  except Exception as e:
    logger.error(f"API route fatal error: {e}")
    raise HTTPException(status_code = 500, detail = str(e))


@router.post('/api/plc/write-tag')
async def plc_write_tag(payload: PLCWriteRequest):

  try:
    plc_manager = __JOB_PLC.GET_PLC_MANAGER()

    if plc_manager is None:
      raise HTTPException(status_code = 503, detail = 'PLC manager is not ready')

    await plc_manager.write_by_name(payload.plc_name, {payload.tag: payload.value})

    return __FUNCTION_COMMON.RESPONSEFORMAT('OK', 'Write command sent to PLC.', {
      'plcName': payload.plc_name,
      'tag': payload.tag,
      'value': payload.value
    })
  except HTTPException:
    raise
  except Exception as e:
    logger.error(f"API route fatal error: {e}")
    raise HTTPException(status_code = 500, detail = str(e))


@router.get('/plc_list')
async def plc_list():

  try:
    plc_manager = __JOB_PLC.GET_PLC_MANAGER()

    if plc_manager is None:
      raise HTTPException(status_code = 503, detail = 'PLC manager is not ready')

    data = plc_manager.list_plcs()
    return __FUNCTION_COMMON.RESPONSEFORMAT('OK', 'PLC list success', data)
  except HTTPException:
    raise
  except Exception as e:
    logger.error(f"API route fatal error: {e}")
    raise HTTPException(status_code = 500, detail = str(e))


@router.get('/plc_status')
async def plc_status():

  try:
    plc_manager = __JOB_PLC.GET_PLC_MANAGER()

    if plc_manager is None:
      raise HTTPException(status_code = 503, detail = 'PLC manager is not ready')

    data = plc_manager.get_manager_status()
    return __FUNCTION_COMMON.RESPONSEFORMAT('OK', 'PLC manager status', data)
  except HTTPException:
    raise
  except Exception as e:
    logger.error(f"API route fatal error: {e}")
    raise HTTPException(status_code = 500, detail = str(e))


@router.post('/plc_read_all')
async def plc_read_all(payload: dict = Body(default = None)):
  """
  payload example
  {
    "tags_by_plc": {
      "OPCUA_PLC_1": ["ns=2;s=Channel2.Device2.D1001"],
      "MITSU_PLC_1": ["D1001", "D1002"]
    }
  }
  """

  try:
    plc_manager = __JOB_PLC.GET_PLC_MANAGER()

    if plc_manager is None:
      raise HTTPException(status_code = 503, detail = 'PLC manager is not ready')

    request_data = payload or {}
    tags_by_plc = request_data.get('tags_by_plc') or {}
    data = await plc_manager.read_all_plcs(tags_by_plc)

    return __FUNCTION_COMMON.RESPONSEFORMAT('OK', 'PLC read all success', data)
  except HTTPException:
    raise
  except Exception as e:
    logger.error(f"API route fatal error: {e}")
    raise HTTPException(status_code = 500, detail = str(e))


@router.post('/plc_write_batch')
async def plc_write_batch(payload: dict = Body(...)):
  """
  payload example
  {
    "commands": [
      {
        "plc_name": "OPCUA_PLC_1",
        "data": {
          "ns=2;s=Channel2.Device2.D1001": 1
        }
      },
      {
        "plc_name": "MITSU_PLC_1",
        "data": {
          "D1001": 100
        }
      }
    ]
  }
  """

  try:
    plc_manager = __JOB_PLC.GET_PLC_MANAGER()

    if plc_manager is None:
      raise HTTPException(status_code = 503, detail = 'PLC manager is not ready')

    commands = payload.get('commands') if isinstance(payload, dict) else None
    data = await plc_manager.write_batch(commands)

    return __FUNCTION_COMMON.RESPONSEFORMAT('OK', 'PLC write batch success', data)
  except HTTPException:
    raise
  except Exception as e:
    logger.error(f"API route fatal error: {e}")
    raise HTTPException(status_code = 500, detail = str(e))

