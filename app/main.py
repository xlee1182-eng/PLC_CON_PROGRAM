from pathlib import Path
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import asyncio

#jobs
import app.jobs.PlcJob as __JOB_PLC

import app.jobs.MyJob as __JOB_MY

## routes
import app.routes.index as __ROUTE_INDEX




@asynccontextmanager
async def lifespan(app: FastAPI):
  # START() 호출 - MyJob과 PlcJob 초기화
  __JOB_MY.START()
  task = asyncio.create_task(__JOB_PLC.START())
  app.state.plc_task = task
  yield
  # 서버 종료 시 매니저 정리 후 백그라운드 task 취소
  __JOB_MY.STOP()
  await __JOB_PLC.STOP()
  task.cancel()
  try:
    await task
  except asyncio.CancelledError:
    pass

app = FastAPI(lifespan=lifespan)


def _resolve_web_root() -> Path:
  if getattr(sys, 'frozen', False):
    meipass = getattr(sys, '_MEIPASS', None)
    if meipass:
      return Path(meipass) / 'app' / 'web'
  return Path(__file__).resolve().parent / 'web'


WEB_ROOT = _resolve_web_root()
if WEB_ROOT.exists():
  app.mount('/static', StaticFiles(directory=str(WEB_ROOT)), name='web-static')

origins = [ '*' ]
app.add_middleware(
  CORSMiddleware,
  allow_origins = origins,
  allow_credentials = True,
  allow_methods = ['*'],
  allow_headers = ['*'],
)

app.include_router(__ROUTE_INDEX.router)