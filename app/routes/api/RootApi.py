from fastapi import APIRouter, HTTPException
from loguru import logger
## functions
import app.functions.CommonFunction as __FUNCTION_COMMON
import app.jobs.plcjob as __JOB_PLC

router = APIRouter()

@router.get('/')
def root():
  return __FUNCTION_COMMON.RESPONSEFORMAT('OK', 'The PLC_CON_Program is running now.', None)

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

