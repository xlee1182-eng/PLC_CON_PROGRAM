# PLC Communication Program

> FastAPI 기반의 다중 PLC 통신 시스템

## 📌 프로젝트 개요

본 프로젝트는 Python 기반의 비동기 웹 서버로, 여러 종류의 산업용 PLC(Programmable Logic Controller)와 통신하는 통합 플랫폼입니다.

**핵심 기능:**
- ✅ 다양한 PLC 프로토콜 지원 (OPC UA, OPC DA, Mitsubishi, Siemens, Rockwell)
- ✅ 실시간 태그 읽기/쓰기 API
- ✅ 비동기 처리로 높은 성능
- ✅ 웹 대시보드 UI
- ✅ 자동 재연결 기능

---

## 🛠 기술 스택

| 분류 | 기술 |
|------|------|
| **Web Framework** | FastAPI 0.135.1 |
| **Async Runtime** | Uvicorn 0.42.0 |
| **PLC Protocols** | OPC UA, OPC DA, S7, EthernetIP |
| **Protocol Libraries** | asyncua, pymcprotocol |
| **Logging** | loguru |
| **Python Version** | 3.8+ |

**의존성 상세:**
```
asyncua==1.1.8              # OPC UA 클라이언트
fastapi==0.135.1           # 웹 프레임워크
humps==0.2.2               # JSON 변수명 변환
loguru==0.7.3              # 로깅
pymcprotocol==0.3.0        # Mitsubishi 통신
pywin32==308               # Windows COM (OPC DA)
uvicorn==0.42.0            # ASGI 서버
```

---

## 📂 프로젝트 구조

```
PLC_CON_PROGRAM/
│
├── 📄 server.py                          # 진입점 (서버 시작)
├── 📄 Config.json                        # PLC 설정 파일
├── 📄 requirements.txt                   # Python 의존성
│
├── 📁 app/
│   ├── 📄 main.py                        # FastAPI 앱 설정
│   │
│   ├── 📁 configs/
│   │   └── 📄 AppConfig.py               # 설정 로더
│   │
│   ├── 📁 jobs/
│   │   └── 📄 plcjob.py                  # PLC 시작/종료 로직
│   │
│   ├── 📁 plc_drivers/                   # PLC 드라이버 모듈
│   │   ├── 📄 base_plc.py                # 기본 PLC 클래스
│   │   ├── 📄 driver_factory.py          # 드라이버 팩토리
│   │   ├── 📄 plc_manager.py             # PLC 관리자
│   │   ├── 📄 opcua_async.py             # OPC UA 드라이버
│   │   ├── 📄 opcda_async.py             # OPC DA 드라이버
│   │   ├── 📄 mitsubishi_async.py        # Mitsubishi 드라이버
│   │   ├── 📄 siemens_async.py           # Siemens 드라이버
│   │   ├── 📄 rockwell_async.py          # Rockwell 드라이버
│   │   └── 📄 reconnect.py               # 재연결 로직
│   │
│   ├── 📁 routes/
│   │   ├── 📄 index.py                   # 라우터 등록
│   │   └── 📁 api/
│   │       └── 📄 RootApi.py             # HTTP 엔드포인트
│   │
│   ├── 📁 functions/
│   │   └── 📄 CommonFunction.py          # 공용 함수
│   │
│   └── 📁 web/
│       ├── 📄 dashboard.html             # 웹 UI
│       └── 📁 assets/
│
├── 📁 docs/                              # 문서 모음
│   ├── 📄 INSTALLATION.md               # 상세 설치 가이드
│   ├── 📄 API_GUIDE.md                  # API 상세 문서
│   ├── 📄 ARCHITECTURE.md              # 시스템 아키텍처
│   ├── 📄 CONFIG_GUIDE.md              # 설정 상세 가이드
│   ├── 📄 PLC_DRIVERS.md              # PLC 드라이버 설명
│   ├── 📄 DEVELOPMENT.md              # 개발 가이드
│   └── 📄 TROUBLESHOOTING.md         # 문제 해결

```

---

## 🚀 빠른 시작

### 1️⃣ 설치

```bash
# 저장소 클론
git clone <repository-url>
cd PLC_CON_PROGRAM

# 가상환경 생성 (권장)
python -m venv venv

# 가상환경 활성화
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# 의존성 설치
pip install -r requirements.txt
```

### 2️⃣ 설정

`Config.json` 파일에서 PLC 정보 수정:

```json
{
  "PLC_INFO": {
    "OPCUA": {
      "USEYN": "Y",
      "NAME": "OPCUA_PLC_1",
      "IP": "127.0.0.1",
      "PORT": 49320,
      "TAGS": [
        "ns=2;s=Channel2.Device2.B0"
      ]
    },
    "MITSUBISHI": {
      "USEYN": "Y",
      "NAME": "MITSU_PLC_1",
      "IP": "192.168.2.210",
      "PORT": 3000,
      "TAGS": ["D100", "D101"]
    }
  }
}
```

### 3️⃣ 실행

```bash
python server.py
```

서버가 `http://localhost:5000` 에서 시작됩니다.

### 4️⃣ 접속

| URL | 설명 |
|-----|------|
| http://localhost:5000 | 서버 상태 확인 |
| http://localhost:5000/web | 웹 대시보드 |
| http://localhost:5000/plc_list | PLC 목록 조회 |

---

## 📡 API 엔드포인트

### 기본 API

| 메서드 | URL | 설명 |
|--------|-----|------|
| GET | `/` | 서버 상태 확인 |
| GET | `/web` | 대시보드 UI |
| GET | `/plc_list` | PLC 목록 조회 |
| GET | `/manager_status` | 시스템 상태 |

### PLC 읽기/쓰기

| 메서드 | URL | 설명 |
|--------|-----|------|
| GET | `/plc_read?plc_name=NAME&tag=TAG` | PLC 태그 읽기 (Query) |
| GET | `/plc_write?plc_name=NAME&tag=TAG&value=VAL` | PLC 태그 쓰기 (Query) |
| POST | `/api/plc/read-tag` | PLC 태그 읽기 (JSON) |
| POST | `/api/plc/write-tag` | PLC 태그 쓰기 (JSON) |

### 사용 예시

```bash
# PLC 태그 읽기
curl "http://localhost:5000/plc_read?plc_name=MITSU_PLC_1&tag=D100"

# PLC 태그 쓰기 (JSON)
curl -X POST http://localhost:5000/api/plc/write-tag \
  -H "Content-Type: application/json" \
  -d '{"plc_name":"MITSU_PLC_1","tag":"D100","value":123}'
```

---

## 🔄 실행 절차

```
1. server.py 시작
    ↓
2. AppConfig.SET() → Config.json 로드
    ↓
3. FastAPI 앱 초기화 (CORS, 정적파일, 라우터 등록)
    ↓
4. lifespan 컨텍스트 → 비동기 PLC 초기화 시작
    ↓
5. plcjob.START()
   ├─ USEYN: "Y" 인 PLC만 처리
   ├─ driver_factory.create_driver() 호출
   │   ├─ OPCUA   → AsyncOPCUAPLC
   │   ├─ OPCDA   → AsyncOPCDA
   │   ├─ MITSUBISHI → AsyncMitsubishiPLC
   │   ├─ SIEMENS → AsyncSiemensPLC
   │   └─ ROCKWELL → AsyncRockwellPLC
   ├─ AsyncPLCManager 생성
   └─ 각 PLC 연결 시작
    ↓
6. 포트 5000에서 리스닝 시작 ✓
    ↓
7. Ctrl+C → plcjob.STOP() → 서버 종료
```

---

## 🔌 지원 PLC 드라이버

| 드라이버 | 프로토콜 | 기본 포트 | 권장 용도 |
|---------|---------|---------|---------|
| **OPC UA** | TCP/IP | 4840 | 최신 표준, 모든 플랫폼 |
| **OPC DA** | COM/DCOM | - | Windows 레거시 시스템 |
| **Mitsubishi** | EthernetIP | 3000/5006 | 삼중 MELSEC PLC |
| **Siemens** | S7 프로토콜 | 102 | Siemens S7 시리즈 |
| **Rockwell** | EthernetIP | 44818 | Allen-Bradley |

자세한 드라이버 설명은 [docs/PLC_DRIVERS.md](docs/PLC_DRIVERS.md) 참고

---

## 🔧 새로운 PLC 드라이버 추가

1. `app/plc_drivers/` 에 드라이버 파일 생성 (`BasePLC` 상속)
2. [app/plc_drivers/driver_factory.py](app/plc_drivers/driver_factory.py) 에 빌더 함수 작성 및 `DRIVER_BUILDERS`에 등록
3. [Config.json](Config.json) 에서 새 PLC 설정 추가 및 `USEYN: "Y"` 활성화

자세한 방법은 [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) 참고

---

## 📚 문서 목록

| 문서 | 내용 |
|------|------|
| [docs/INSTALLATION.md](docs/INSTALLATION.md) | 상세 설치 가이드 |
| [docs/API_GUIDE.md](docs/API_GUIDE.md) | API 엔드포인트 상세 문서 |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | 시스템 아키텍처 및 데이터 흐름 |
| [docs/CONFIG_GUIDE.md](docs/CONFIG_GUIDE.md) | Config.json 타입별 설정 방법 |
| [docs/PLC_DRIVERS.md](docs/PLC_DRIVERS.md) | PLC 드라이버별 특징 및 사용법 |
| [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) | 신규 기능 개발 가이드 |
| [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) | 자주 발생하는 문제 및 해결책 |

---

## 👤 정보

- **Author**: LI XIONG
- **Created**: 2026-03-17
- **Last Updated**: 2026-03-20
