# 개발 가이드

새로운 기능을 추가하고 PLC_CON_PROGRAM을 확장하는 방법을 설명합니다.

## 🏗️ 개발 환경 설정

### 1. 저장소 클론 및 설정

```bash
git clone <repository-url>
cd PLC_CON_PROGRAM

# 가상환경 생성
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 개발 의존성 설치
pip install -r requirements.txt
pip install pytest pytest-asyncio black flake8
```

### 2. IDE 설정 (VS Code 권장)

```json
// .vscode/settings.json
{
  "python.linting.enabled": true,
  "python.linting.flake8Enabled": true,
  "python.formatting.provider": "black",
  "python.linting.flake8Args": ["--max-line-length=100"],
  "editor.formatOnSave": true
}
```

### 3. 코드 스타일

- **Python**: PEP 8 (Black 포매터 사용)
- **들여쓰기**: 2 스페이스
- **라인 길이**: 100 자 제한
- **인코딩**: UTF-8

---

## 🔌 새로운 PLC 드라이버 추가

### 1단계: 드라이버 클래스 생성

`app/plc_drivers/new_driver.py` 파일 생성:

```python
import asyncio
from loguru import logger
from app.plc_drivers.base_plc import BasePLC


class AsyncNewPLC(BasePLC):
  """New PLC Driver"""

  def __init__(self, name, ip, port, tags, **kwargs):
    super().__init__(name, ip, port, tags)
    self.connection = None
    # 추가 초기화
    self.extra_config = kwargs.get('extra_config')

  async def connect(self):
    """Connect to PLC"""
    try:
      # 실제 연결 로직
      logger.info(f'{self.name} connecting to {self.ip}:{self.port}')
      # await self._create_connection()
      self._connected = True
      logger.info(f'{self.name} connected successfully')
    except Exception as e:
      logger.error(f'{self.name} connection error: {e}')
      self._connected = False
      raise

  async def disconnect(self):
    """Disconnect from PLC"""
    try:
      if self.connection:
        # await self.connection.close()
        self.connection = None
      self._connected = False
      logger.info(f'{self.name} disconnected')
    except Exception as e:
      logger.error(f'{self.name} disconnect error: {e}')

  async def read_tag(self, tag):
    """Read tag value"""
    if not self.connected:
      raise Exception(f'{self.name} is not connected')
    
    try:
      # 실제 읽기 로직
      # value = await self.connection.read(tag)
      value = 0  # 예시
      return value
    except Exception as e:
      logger.error(f'{self.name} read error on {tag}: {e}')
      raise

  async def write_tag(self, tag, value):
    """Write tag value"""
    if not self.connected:
      raise Exception(f'{self.name} is not connected')
    
    try:
      # 실제 쓰기 로직
      # await self.connection.write(tag, value)
      logger.info(f'{self.name} wrote {value} to {tag}')
    except Exception as e:
      logger.error(f'{self.name} write error on {tag}: {e}')
      raise
```

### 2단계: 팩토리 함수 추가

`app/plc_drivers/driver_factory.py` 수정:

```python
from app.plc_drivers.new_driver import AsyncNewPLC

def _build_new_protocol(config):
  return AsyncNewPLC(
    name=_require(config, "NAME"),
    ip=_require(config, "IP"),
    port=config.get("PORT", 5000),  # 기본 포트
    tags=config.get("TAGS"),
    extra_config=config.get("EXTRA_CONFIG")
  )

DRIVER_BUILDERS = {
  "OPCUA": _build_opcua,
  "OPCDA": _build_opcda,
  "MITSUBISHI": _build_mitsubishi,
  "SIEMENS": _build_siemens,
  "ROCKWELL": _build_rockwell,
  "NEW_PROTOCOL": _build_new_protocol,  # ← 추가
}
```

### 3단계: Config.json에 설정 추가

```json
{
  "PLC_INFO": {
    "NEW_PROTOCOL": {
      "USEYN": "Y",
      "NAME": "NEW_PLC_1",
      "IP": "192.168.1.100",
      "PORT": 5000,
      "TAGS": ["tag1", "tag2"],
      "EXTRA_CONFIG": { /* 추가 옵션 */ }
    }
  }
}
```

### 4단계: 테스트

```python
# test_new_driver.py
import pytest
import asyncio
from app.plc_drivers.new_driver import AsyncNewPLC

@pytest.mark.asyncio
async def test_connect():
  plc = AsyncNewPLC(
    name="TEST_PLC",
    ip="localhost",
    port=5000,
    tags=["tag1"]
  )
  await plc.connect()
  assert plc.connected == True
  await plc.disconnect()

@pytest.mark.asyncio
async def test_read():
  plc = AsyncNewPLC(
    name="TEST_PLC",
    ip="localhost",
    port=5000,
    tags=["tag1"]
  )
  await plc.connect()
  value = await plc.read_tag("tag1")
  assert value is not None
  await plc.disconnect()
```

테스트 실행:

```bash
pytest test_new_driver.py -v
```

---

## 🌐 새로운 API 엔드포인트 추가

### 1단계: RootApi에 함수 추가

`app/routes/api/RootApi.py`:

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import app.jobs.plcjob as __JOB_PLC
import app.functions.CommonFunction as __FUNCTION_COMMON

router = APIRouter()

class CustomRequest(BaseModel):
  plc_name: str
  custom_param: str

@router.post('/api/custom-endpoint')
async def custom_endpoint(payload: CustomRequest):
  """Custom API endpoint"""
  try:
    plc_manager = __JOB_PLC.GET_PLC_MANAGER()
    
    if plc_manager is None:
      raise HTTPException(
        status_code=503,
        detail='PLC manager is not ready'
      )
    
    # 커스텀 로직
    result = {
      'custom_data': payload.custom_param,
      'timestamp': asyncio.get_event_loop().time()
    }
    
    return __FUNCTION_COMMON.RESPONSEFORMAT(
      'OK',
      'Custom request processed',
      result
    )
  except HTTPException:
    raise
  except Exception as e:
    logger.error(f"API error: {e}")
    raise HTTPException(status_code=500, detail=str(e))
```

### 2단계: 테스트

```bash
# 서버 실행
python server.py

# 다른 터미널에서 테스트
curl -X POST http://localhost:5000/api/custom-endpoint \
  -H "Content-Type: application/json" \
  -d '{"plc_name":"MITSU_PLC_1","custom_param":"test"}'
```

---

## 🧪 단위 테스트 작성

### 테스트 구조

```
tests/
├── __init__.py
├── test_drivers.py      # 드라이버 테스트
├── test_api.py          # API 테스트
├── test_config.py       # 설정 테스트
└── fixtures.py          # 테스트 픽스처
```

### 예시: API 테스트

```python
# tests/test_api.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_read_root():
  response = client.get("/")
  assert response.status_code == 200
  assert response.json()["status"] == "OK"

def test_plc_list():
  response = client.get("/plc_list")
  assert response.status_code == 200
  assert "data" in response.json()
```

### 테스트 실행

```bash
# 모든 테스트 실행
pytest

# 특정 파일만
pytest tests/test_api.py

# 상세 출력
pytest -v

# 커버리지 확인
pytest --cov=app
```

---

## 🔄 비동기 프로그래밍

### 기본 패턴

```python
import asyncio

# 1. async 함수 정의
async def async_operation():
  await asyncio.sleep(1)
  return "완료"

# 2. 실행
result = asyncio.run(async_operation())

# 3. 여러 작업 동시 실행
async def multiple_tasks():
  results = await asyncio.gather(
    async_operation(),
    async_operation(),
    async_operation()
  )
  return results
```

### PLC Reader 예시

```python
async def read_multiple_tags(plc_manager, plc_name, tags):
  """여러 태그 동시 읽기"""
  tasks = [
    plc_manager.read_by_name(plc_name, tag)
    for tag in tags
  ]
  values = await asyncio.gather(*tasks)
  return dict(zip(tags, values))
```

---

## 📊 로깅

### loguru 사용

```python
from loguru import logger

# 기본 로깅
logger.info("정보 메시지", extra={"module": "plc_driver"})
logger.warning("경고 메시지")
logger.error("에러 메시지")
logger.debug("디버그 메시지")

# 예외와 함께
try:
  1 / 0
except Exception as e:
  logger.exception("예외 발생")

# 구조화된 로깅
logger.info("PLC 연결", plc_name="MITSU_PLC_1", ip="192.168.1.100")
```

### 환경 변수로 레벨 조정

```bash
set LOGURU_LEVEL=DEBUG
python server.py
```

---

## 🚀 성능 최적화

### 배치 읽기

```python
# ❌ 나쁜 예
for tag in tags:
  value = await plc_manager.read_by_name(plc_name, tag)
  process(value)

# ✅ 좋은 예
values = await asyncio.gather(*[
  plc_manager.read_by_name(plc_name, tag)
  for tag in tags
])
for tag, value in zip(tags, values):
  process(value)
```

### 캐싱

```python
from functools import lru_cache

@lru_cache(maxsize=128)
def get_config_cached(key):
  return APPCONFIG.get(key)
```

### 연결 풀

```python
class ConnectionPool:
  def __init__(self, max_connections=10):
    self.semaphore = asyncio.Semaphore(max_connections)
  
  async def acquire(self):
    async with self.semaphore:
      # 연결 수 제한
      yield
```

---

## 🔍 디버깅

### VS Code 디버거 설정

`.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: 서버",
      "type": "python",
      "request": "launch",
      "program": "${workspaceFolder}/server.py",
      "console": "integratedTerminal",
      "justMyCode": false
    }
  ]
}
```

### 사용

1. 중단점 설정 (F9)
2. F5로 디버그 시작
3. 변수 확인, 단계 실행 등

### 로그 기반 디버깅

```python
logger.debug(f"현재 상태: {plc_manager.get_manager_status()}")
```

---

## 📦 패킹 및 배포

### PyInstaller로 EXE 생성

```bash
# server.spec 파일 사용
pyinstaller server.spec

# 또는 직접 생성
pyinstaller --onefile --windowed server.py
```

### Docker로 배포

```dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 5000

CMD ["python", "server.py"]
```

Build:
```bash
docker build -t plc_con_program .
docker run -p 5000:5000 plc_con_program
```

---

## 🔧 코드 리뷰 체크리스트

- [ ] PEP 8 준수 (Black 포매팅 확인)
- [ ] 타입 힌트 추가
- [ ] 에러 처리 적절
- [ ] 로깅 추가
- [ ] 단위 테스트 작성
- [ ] 문서 업데이트
- [ ] 보안 이슈 확인
- [ ] 성능 영향 확인

---

## 📚 유용한 리소스

- **FastAPI**: https://fastapi.tiangolo.com/
- **asyncio**: https://docs.python.org/3/library/asyncio.html
- **OPC UA**: https://reference.opcfoundation.org/
- **pytest**: https://pytest.org/

---

## 🤝 기여 가이드

1. Fork 저장소
2. 기능 브랜치 생성 (`git checkout -b feature/AmazingFeature`)
3. 변경사항 커밋 (`git commit -m 'Add some AmazingFeature'`)
4. 브랜치 Push (`git push origin feature/AmazingFeature`)
5. Pull Request 생성

---

## 📞 도움이 필요한 경우

- GitHub Issues
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- 프로젝트 커뮤니티
