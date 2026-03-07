from fastapi import APIRouter
from loguru import logger
## functions
import app.functions.CommonFunction as __FUNCTION_COMMON

import app.db.DBManager as __DB_MANAGER
db = __DB_MANAGER.DBManager()

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
                
@router.get('/api')
def health():
  try:
    data = "model.model_dump()"

    result = data

    return result
  except Exception as e:
                logger.error(f"API route fatal error: {e}")

@router.get('/select')
def select():
  try:
    rows = db.EXECUTE(
    "MES",
    "GET",
    "SELECT * FROM MES_TABLE WHERE ID = :id",
    {"id":1}
    )

    print(rows)

    data = rows

    result = data

    return result
  except Exception as e:
                logger.error(f"API route fatal error: {e}")
@router.get('/insert')
def insert():
  try:
    rows = db.EXECUTE(
    "MES",
    "SET",
    "INSERT INTO TEST_TABLE(ID,NAME) VALUES(:id,:name)",
    {"id":10,"name":"TEST"}
)

    print(rows)

    data = rows

    result = data

    return result
  except Exception as e:
                logger.error(f"API route fatal error: {e}")
@router.get('/reconnect')
def reconnect():
  try:
    db.RECONNECT("MES")
    rows = "reconnected"
    print(rows)

    data = rows

    result = data

    return result
  except Exception as e:
                logger.error(f"API route fatal error: {e}")
@router.get('/create_cursor')
def create_cursor():
  try:
    cursor = db.CREATECURSOR("MES")
    rows = "cursor created"
    print(rows)

    data = rows

    result = data

    return result
  except Exception as e:
                logger.error(f"API route fatal error: {e}")