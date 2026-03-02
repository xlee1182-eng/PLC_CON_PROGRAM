from fastapi import APIRouter
from loguru import logger
## functions
import app.functions.CommonFunction as __FUNCTION_COMMON

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
