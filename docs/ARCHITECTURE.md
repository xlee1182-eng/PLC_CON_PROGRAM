# 시스템 아키텍처

PLC_CON_PROGRAM의 전체 시스템 아키텍처를 설명합니다.

## 🏗️ 전체 구조도

```
┌─────────────────────────────────────────────────────────────┐
│                      Client Layer                            │
│  (Web UI / API Client / Python Script / External System)    │
└────────────────────┬────────────────────────────────────────┘
                     │ HTTP/REST
                     ↓
┌─────────────────────────────────────────────────────────────┐
│              FastAPI Web Server (server.py)                 │
│    Host: 0.0.0.0, Port: 5000, Async (Uvicorn)             │
└────────────┬──────────────────────────────────────────────┬─┘
             │                                               │
             ↓                                               ↓
    ┌────────────────────┐                        ┌──────────────────────┐
    │   Main Module      │                        │   Configuration      │
    │  (app/main.py)     │                        │  (AppConfig.py)      │
    │                    │                        │  (Config.json)       │
    │ - FastAPI App      │                        │                      │
    │ - CORS Middleware  │                        │ PLC List:            │
    │ - Static Files     │                        │ · OPCUA              │
    │ - Lifespan Handler │                        │ · MITSUBISHI         │
    │   (Async Init)     │                        │ · SIEMENS            │
    └────────┬───────────┘                        │ · ROCKWELL           │
             │                                     │ · OPCDA              │
             ↓                                     └──────────────────────┘
    ┌────────────────────┐
    │  Router Layer      │
    │(routes/index.py)   │
    │(api/RootApi.py)    │
    │                    │
    │ GET /              │
    │ GET /web           │
    │ GET /plc_read      │
    │ GET /plc_write     │
    │ POST /api/plc/*    │
    │ GET /plc_list      │
    │ GET /manager_status│
    └────────┬───────────┘
             │
             ↓
    ┌────────────────────┐
    │   Job Manager      │
    │  (jobs/plcjob.py)  │
    │                    │
    │ - START()          │
    │ - STOP()           │
    │ - GET_PLC_MANAGER()│
    └────────┬───────────┘
             │
             ↓
    ┌────────────────────────────┐
    │  Driver Factory Layer      │
    │ (driver_factory.py)        │
    │                            │
    │ create_driver()            │
    │   ↓ (by type)              │
    │   · OPCUA → AsyncOPCUAPLC  │
    │   · OPCDA → AsyncOPCDA     │
    │   · MITSUBISHI → Async...  │
    │   · SIEMENS → AsyncSiemens │
    │   · ROCKWELL → AsyncRockw  │
    └────────┬───────────────────┘
             │
             ↓
    ┌────────────────────────────┐
    │   PLC Manager              │
    │ (plc_manager.py)           │
    │                            │
    │ - Multiple PLC Instances   │
    │ - read_by_name()           │
    │ - write_by_name()          │
    │ - start()                  │
    │ - stop()                   │
    │ - get_manager_status()     │
    └────────┬───────────────────┘
             │
    ┌────────┴─────────────────────────┬──────────────┬──────────────────┐
    ↓                                  ↓              ↓                  ↓
    ┌────────────────┐    ┌──────────────────┐   ┌──────────────┐   ┌──────────────┐
    │ OPCUA Driver   │    │ Mitsubishi       │   │ Siemens S7   │   │ Rockwell     │
    │ AsyncOPCUAPLC  │    │ AsyncMitsubishi  │   │ AsyncSiemens │   │ AsyncRockwell│
    │                │    │                  │   │              │   │              │
    │ · TCP/IP 4840 │    │ · EthernetIP     │   │ · S7 Comm    │   │ · EthernetIP │
    │ · Async Client│    │ · Port 3000-6000 │   │ · Port 102   │   │ · Port 44818 │
    │ · Subscription│    │ · 5006/3000      │   │ · Rack/Slot  │   │              │
    └────────┬───────┘    └────────┬─────────┘   └──────┬───────┘   └──────┬───────┘
             │                     │                     │                  │
             └─────────────────────┴─────────────────────┴──────────────────┘
                                    │
                                    ↓
                    ┌───────────────────────────────┐
                    │   Reconnection Logic          │
                    │  (reconnect.py)               │
                    │                               │
                    │ - Auto Reconnect on Failure   │
                    │ - Exponential Backoff         │
                    │ - Connection Timeout Handling │
                    └───────────────┬───────────────┘
                                    │
                    ┌───────────────┴────────────────┐
                    │                                │
                    ↓                                ↓
        ┌──────────────────────┐      ┌──────────────────────┐
        │   Physical PLC       │      │   OPC Server         │
        │  (Mitsubishi/Siemens)│      │   (OPC DA/OPC UA)    │
        │                      │      │                      │
        │ Sensors → Processing │      │  Gateway to PLC      │
        │ → Actuators Output   │      │  (Windows Environment)
        └──────────────────────┘      └──────────────────────┘
```

---

## 📊 데이터 흐름

### 1. 서버 시작 흐름

```
server.py 실행
    ↓
AppConfig.SET() → Config.json 로드
    ↓
FastAPI 앱 초기화 (main.py)
    ├─ CORS 미들웨어 추가
    ├─ 정적 파일 마운트 (/static)
    └─ 라우터 등록 (RootApi)
    ↓
lifespan 컨텍스트 매니저
    ├─ asyncio.create_task(plcjob.START())
    └─ 백그라운드에서 PLC 초기화
    ↓
plcjob.START()
    ├─ Config.json에서 'USEYN' == 'Y' 인 PLC만 처리
    ├─ create_driver()로 각 PLC 드라이버 생성
    ├─ AsyncPLCManager에 등록
    └─ PLC Manager.start() 호출
    ↓
각 PLC 드라이버
    ├─ 연결 시도
    ├─ 태그 모니터링 시작
    └─ 상태 업데이트
    ↓
포트 5000 리스닝 시작 ✓
```

### 2. API 요청 처리 흐름

```
클라이언트 요청
    ↓
FastAPI 라우터 (RootApi)
    ↓
플로우 분기:

[GET /plc_read]                 [POST /api/plc/write-tag]
    ↓                                   ↓
RootApi.plc_read() --------+----  RootApi.plc_write_tag()
                            │     (JSON 파싱)
    ↓                       ↓
plcjob.GET_PLC_MANAGER() ←─┘
    ↓
AsyncPLCManager.read_by_name()
    ├─ plc = _plc_map.get(plc_name)
    └─ await plc.read_tag(tag)
    ↓
구체적인 PLC 드라이버 (AsyncOPCUAPLC 등)
    ├─ 실제 통신 수행
    ├─ 타임아웃 처리
    └─ 값 반환
    ↓
CommonFunction.RESPONSEFORMAT()
    ├─ status: "OK" or "ERROR"
    ├─ msg: 메시지
    └─ data: 결과 데이터
    ↓
JSON 응답 반환 → 클라이언트
```

### 3. PLC 통신 흐름

```
Read Request
    ↓
AsyncPLCManager.read_by_name(plc_name, tag)
    ├─ self._run_with_timeout() 호출 (타임아웃 처리)
    └─ plc.read_tag(tag) awaiting
    ↓
각 PLC 드라이버별 처리:

[OPC UA]                    [Mitsubishi]            [Siemens]
await client.get_node()     await comm.read()       await conn.read()
    ↓                           ↓                       ↓
get_value()                 Modbus 프레임          S7 프로토콜
    ↓                           ↓                       ↓
값 반환                     값 반환                  값 반환
    │                           │                       │
    └───────────┬───────────────┴───────────────────────┘
                ↓
        결과 포매팅
            ↓
        API 응답
```

---

## 🔄 클래스 다이어그램

### PLC Driver Hierarchy

```
BasePLC (추상 클래스)
├── __init__(name, ip, port, tags, ...)
├── async connect() → 추상 메서드
├── async disconnect() → 추상 메서드
├── async read_tag(tag) → 추상 메서드
├── async write_tag(tag, value) → 추상 메서드
└── connected: property

    ├─ AsyncOPCUAPLC
    │   ├── asyncua.Client
    │   ├── 비동기 구독 지원
    │   └── 타임아웃 처리
    │
    ├─ AsyncOPCDA
    │   ├── pywin32 COM/DCOM
    │   ├── Windows 전용
    │   └── Legacy 시스템용
    │
    ├─ AsyncMitsubishiPLC
    │   ├── pymcprotocol.McClient
    │   ├── EthernetIP
    │   └── 자동 재연결
    │
    ├─ AsyncSiemensPLC
    │   ├── snap7 library
    │   ├── S7 protocol
    │   └── Rack/Slot 지원
    │
    └─ AsyncRockwellPLC
        ├── Logix 통신
        ├── EthernetIP/IP
        └── 클래스 기반 구조
```

### PLC Manager Architecture

```
AsyncPLCManager
├── plc_list: List[BasePLC]
├── _plc_map: Dict[str, BasePLC]
├── _tasks: List[Task]
├── _change_queue: asyncio.Queue
├── _change_handlers: List[Callable]
├── _operation_timeout: float
│
├─ Public Methods:
│  ├── async start()
│  ├── async stop()
│  ├── get_plc(plc_name) → BasePLC
│  ├── async read_by_name(plc_name, tag) → Any
│  ├── async write_by_name(plc_name, tags_dict)
│  ├── list_plcs() → List[Dict]
│  └── get_manager_status() → Dict
│
└─ Private Methods:
   ├── _register_plcs(plc_list)
   ├── async _run_with_timeout(coro, context)
   ├── _change_notify(...)
   └── change_handler 관리
```

---

## 🔌 의존성 관계

```
server.py
    ↓
app.configs.AppConfig        (Config.json 로데)
    ↓
app.main (FastAPI 앱)
    ├─ app.routes.index
    │   └─ app.routes.api.RootApi
    │       ├─ app.functions.CommonFunction
    │       └─ app.jobs.plcjob
    │           ├─ app.plc_drivers.driver_factory
    │           │   ├─ app.plc_drivers.opcua_async
    │           │   ├─ app.plc_drivers.opcda_async
    │           │   ├─ app.plc_drivers.mitsubishi_async
    │           │   ├─ app.plc_drivers.siemens_async
    │           │   └─ app.plc_drivers.rockwell_async
    │           │
    │           └─ app.plc_drivers.plc_manager
    │               ├─ app.plc_drivers.base_plc
    │               └─ app.plc_drivers.reconnect
    │
    └─ app.web.dashboard.html
        └─ Front-end JavaScript
```

---

## ⚙️ 비동기 처리 모델

### Event Loop Model

```
uvicorn (Async Event Loop)
    │
    ├─ Main Server Task (포트 5000 리스닝)
    │
    ├─ PLC Manager Tasks
    │   ├─ Task 1: OPCUA 폴링
    │   ├─ Task 2: Mitsubishi 폴링
    │   ├─ Task 3: Siemens 폴링
    │   └─ Task 4: Reconnect 모니터링
    │
    ├─ API Request Tasks (동적 생성)
    │   ├─ GET /plc_read
    │   ├─ POST /api/plc/write-tag
    │   └─ ...
    │
    └─ Background Tasks
        ├─ 상태 변경 핸들러
        └─ 로깅
```

### Timeout Handling

```
AsyncPLCManager._run_with_timeout(coro, context)
    ├─ timeout = PLC_OPERATION_TIMEOUT_SEC (기본 3.0초)
    ├─ asyncio.wait_for(coro, timeout=timeout)
    │   ├─ 정상: 결과 반환
    │   └─ TimeoutError: TimeoutError 발생
    │
    └─ 호출자가 TimeoutError 처리
```

---

## 🗄️ 상태 관리

### PLC Connection State

```
초기 상태: DISCONNECTED
    │
    ├─ connect() 호출
    │   ↓
    ├─ CONNECTING (연중)
    │   ├─ 성공
    │   │   ↓
    │   ├─ CONNECTED ✓
    │   │   └─ read/write 가능
    │   │
    │   └─ 실패
    │       ↓
    │   RECONNECT 시도
    │   (exponential backoff)
    │
    └─ disconnect() 호출
        ↓
    DISCONNECTED
```

### Configuration Flow

```
Config.json
    ↓
AppConfig.SET()
    ├─ JSON 파싱
    ├─ PLC_INFO 추출
    └─ Global APPCONFIG 변수에 저장
    ↓
plcjob.START()
    ├─ APPCONFIG 읽음
    ├─ USEYN == 'Y' 필터링
    └─ 드라이버 생성
```

---

## 📈 성능 고려사항

### 폴링 전략

```
각 PLC 드라이버는 subscription_options 지원:
{
  "subscription_mode": "auto",      # auto/manual/disabled
  "active_poll_ms": 100,            # 활동 상태 폴링
  "idle_poll_ms": 1000,             # 유휴 상태 폴링
  "burst_cycles": 10                # 버스트 사이클 수
}
```

### Timeout 설정

```
PLC_OPERATION_TIMEOUT_SEC (환경 변수 또는 기본 3.0초)
├─ 너무 짧음: 느린 네트워크에서 타임아웃
└─ 너무 길음: 응답 시간 증가
```

### Connection Pool

```
AsyncPLCManager
├─ 각 PLC별 1개 연결 유지
├─ 자동 재연결 (exponential backoff)
└─ 타임아웃 처리
```

---

## 🔐 보안 고려사항

### 현재 구현

- CORS: 모든 오리진 허용 (`*`)
- 인증: 없음
- 암호화: 드라이버별 지원 여부 다름

### 프로덕션 권장사항

1. **CORS 제한**
   ```python
   origins = ["https://example.com"]
   ```

2. **인증 추가**
   - API Key
   - JWT Token
   - OAuth2

3. **HTTPS 적용**
   - SSL/TLS 인증서
   - Uvicorn SSL 설정

4. **네트워크**
   - VPN 사용
   - Firewall 규칙
   - IP 화이트리스팅

---

## 📊 모니터링 포인트

### 로깅

```
loguru 사용:
├─ PLC 연결/연결 해제
├─ 읽기/쓰기 작업
├─ 에러 및 예외
└─ 재연결 시도
```

### 메트릭

```
추적 가능한 항목:
├─ PLC 연결 상태
├─ 읽기/쓰기 성공률
├─ 평균 응답 시간
├─ 에러율
└─ 연결 복구 횟수
```

---

## 🚀 확장성

### 새 PLC 드라이버 추가

1. `BasePLC` 상속
2. 필요한 메서드 구현
3. `driver_factory.py`에 빌더 함수 추가
4. `DRIVER_BUILDERS` 딕셔너리에 등록
5. `Config.json`에 설정 추가

### 새 엔드포인트 추가

1. `routes/api/RootApi.py`에 함수 추가
2. `@router.get()` 또는 `@router.post()` 데코레이터 사용
3. `plcjob.GET_PLC_MANAGER()` 호출하여 데이터 접근
4. 응답 포매팅 (`CommonFunction.RESPONSEFORMAT()`)

---

이 아키텍처는 스케일 가능하고 유지보수하기 쉽도록 설계되었습니다.
