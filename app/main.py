from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio

#jobs
import app.jobs.plcjob as __JOB_PLC

## routes
import app.routes.index as __ROUTE_INDEX



@asynccontextmanager
async def lifespan(app: FastAPI):
  # START()를 background task로 실행하여 서버 시작 시 블로킹을 방지
  task = asyncio.create_task(__JOB_PLC.START())
  app.state.plc_task = task
  yield
  # 서버 종료 시 백그라운드 task 취소
  task.cancel()
  try:
    await task
  except asyncio.CancelledError:
    pass


app = FastAPI(lifespan=lifespan)

origins = [ '*' ]
app.add_middleware(
  CORSMiddleware,
  allow_origins = origins,
  allow_credentials = True,
  allow_methods = ['*'],
  allow_headers = ['*'],
)

app.include_router(__ROUTE_INDEX.router)