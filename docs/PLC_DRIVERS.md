# PLC 드라이버 가이드

각 PLC 드라이버의 특징, 설정 방법, 사용 예시를 상세히 설명합니다.

## 📡 지원 드라이버 목록

| 드라이버 | 프로토콜 | 상태 | 권장 용도 |
|---------|---------|------|---------|
| **OPC UA** | TCP/IP | ✅ 안정적 | 최신 표준, 모든 플랫폼 |
| **OPC DA** | COM/DCOM | ⚠️ 레거시 | Windows 레거시 시스템 |
| **Mitsubishi** | Ethernet/IP | ✅ 안정적 | 삼중 PLC |
| **Siemens** | S7 프로토콜 | ✅ 안정적 | Siemens S5/S7 |
| **Rockwell** | Ethernet/IP | ✅ 안정적 | Allen-Bradley CompactLogix |

---

## 🔷 OPC UA (권장)

### 개요

OPC UA (Open Platform Communications Unified Architecture)는 산업 4.0의 표준 통신 프로토콜입니다.

**장점:**
- ✅ 플랫폼 독립 (Windows, Linux, macOS)
- ✅ TCP/IP 기반 (방화벽 친화적)
- ✅ 강력한 보안 (암호화, 인증)
- ✅ 확장성 우수
- ✅ 자동 구독/모니터링 지원

**단점:**
- ❌ 설정 상대적 복잡
- ❌ 메모리 사용량 많음

### 설정

```json
{
  "OPCUA": {
    "USEYN": "Y",
    "NAME": "OPCUA_PLC_1",
    "IP": "192.168.1.100",
    "PORT": 4840,
    "TAGS": [
      "ns=2;s=Channel2.Device2.B0",
      "ns=2;s=Channel2.Device2.D1001"
    ]
  }
}
```

### 노드 ID 찾기

#### 방법 1: UaExpert (추천)

1. UaExpert 다운로드 (Unified Automation)
2. 서버 주소: `opc.tcp://192.168.1.100:4840`
3. 노드 트리에서 원하는 노드 클릭
4. 오른쪽 패널에서 Node ID 확인

#### 방법 2: 시뮬레이터

```python
import logging
import asyncio
from asyncua import Client

logging.basicConfig(level=logging.INFO)

async def browse():
    client = Client("opc.tcp://192.168.1.100:4840")
    await client.connect()
    root = client.get_root_node()
    
    async def browse_node(node, level=0):
        print("  " * level + (await node.read_display_name()).Text)
        for child in await node.get_children():
            await browse_node(child, level + 1)
    
    await browse_node(root)
    await client.disconnect()

asyncio.run(browse())
```

### 사용 예시

#### Python Client

```python
import requests

# OPC UA 읽기
response = requests.post(
    'http://localhost:5000/api/plc/read-tag',
    json={
        'plc_name': 'OPCUA_PLC_1',
        'tag': 'ns=2;s=Channel2.Device2.B0'
    }
)
print(response.json())

# OPC UA 쓰기
response = requests.post(
    'http://localhost:5000/api/plc/write-tag',
    json={
        'plc_name': 'OPCUA_PLC_1',
        'tag': 'ns=2;s=Channel2.Device2.D1001',
        'value': 100
    }
)
print(response.json())
```

#### cURL

```bash
# 읽기
curl -X POST http://localhost:5000/api/plc/read-tag \
  -H "Content-Type: application/json" \
  -d '{"plc_name":"OPCUA_PLC_1","tag":"ns=2;s=Channel2.Device2.B0"}'

# 쓰기
curl -X POST http://localhost:5000/api/plc/write-tag \
  -H "Content-Type: application/json" \
  -d '{"plc_name":"OPCUA_PLC_1","tag":"ns=2;s=Channel2.Device2.D1001","value":100}'
```

### 인증 설정

OPC UA 보안이 활성화된 경우:

```json
{
  "OPCUA": {
    "USEYN": "Y",
    "NAME": "OPCUA_SECURE",
    "IP": "192.168.1.100",
    "PORT": 4840,
    "USERNAME": "admin",
    "PASSWORD": "password",
    "TAGS": [...]
  }
}
```

### 성능 팁

- 폴링 간격: 100-500ms
- 대량 태그: 배치 읽기 줄임
- 시간 초과: 환경 변수 조정

---

## 🔴 OPC DA (레거시)

### 개요

OPC DA (Data Access)는 초기 OPC 표준입니다.

**장점:**
- ✅ 오래된 시스템과 호환
- ✅ 많은 기기에서 지원
- ✅ 설정 간단

**단점:**
- ❌ Windows 전용
- ❌ COM/DCOM 설정 복잡
- ❌ 보안 취약
- ❌ 네트워크 투과 어려움

### 설정

```json
{
  "OPCDA": {
    "USEYN": "Y",
    "NAME": "OPCDA_PLC_1",
    "IP": "localhost",
    "PORT": 0,
    "PROG_ID": "Takebishi.Melsec.1",
    "TAGS": [
      "Channel1.Device1.D1001",
      "Channel1.Device1.D1002"
    ]
  }
}
```

### PROG_ID 확인 (Windows)

#### 방법 1: Registry Editor

```
HKEY_CLASSES_ROOT\
  ProgID (찾는 항목)
  
예시:
- Takebishi.Melsec.1
- Siemens.SimaticNET.1
- HMS.KepServerEX.V6
```

#### 방법 2: Python

```python
import winreg

hkey = winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, "ProgID")
for i in range(100):
    try:
        name = winreg.EnumKey(hkey, i)
        if "opc" in name.lower():
            print(name)
    except:
        break
winreg.CloseKey(hkey)
```

### 일반적인 PROG_ID

| 제조사 | PROG_ID |
|--------|---------|
| 삼중 (Mitsubishi) | `Takebishi.Melsec.1` |
| Siemens | `Siemens.SimaticNET.1` |
| Rockwell | `RSI.OPCServer.1` |
| Wonderware | `WonderWare.DataServer.1` |
| MatrikonOPC | `Matrikon.OPC.Simulation.1` |

### 사용 예시

```python
# 일반적인 사용법과 동일
response = requests.post(
    'http://localhost:5000/api/plc/read-tag',
    json={
        'plc_name': 'OPCDA_PLC_1',
        'tag': 'Channel1.Device1.D1001'
    }
)
```

### 문제 해결

**COM 초기화 오류:**

```bash
# pywin32 설정 다시 실행 (관리자 권한)
python -m pip install -U --force-reinstall pywin32
python -m pywin32_postinstall -install
```

---

## 🟠 Mitsubishi (삼중 PLC)

### 개요

삼중 MELSEC 시리즈 PLC와의 직접 통신입니다.

**프로토콜:**
- `E-series`: Ethernet IP
- `iQ-R series`: 동일 프로토콜

**장점:**
- ✅ 직접 연결 가능 (OPC 불필요)
- ✅ 빠른 응답
- ✅ 간단한 설정

**단점:**
- ❌ Mitsubishi PLC만 지원
- ❌ 일부 고급 기능 미지원

### 설정

```json
{
  "MITSUBISHI": {
    "USEYN": "Y",
    "NAME": "MITSU_PLC_1",
    "IP": "192.168.2.210",
    "PORT": 3000,
    "TAGS": ["D100", "D101", "D102", "M10", "Y5"],
    "SUBSCRIPTION": {
      "MODE": "auto",
      "ACTIVE_POLL_MS": 100,
      "IDLE_POLL_MS": 1000,
      "BURST_CYCLES": 10
    }
  }
}
```

### 메모리 주소 형식

```
데이터 메모리:     D0, D1, D100
비트 메모리:       B0, B10
마스터 컨트롤:     M0, M10
래치 메모리:       L0, L10
특수 릴레이:       S0, S10
타이머:            T0, T100
카운터:            C0, C100
입력:              X0, X10
출력:              Y0, Y10
링크 설정:         R0, R10

형식:
- 단일 값: "D100"
- 범위: "D100:D110" (D100부터 D110까지)
- 배열식: "D100, D101, D102"
```

### Mitsubishi PLC IP 설정

#### FX5U-Ethernet

1. PLC 접속 (씨매스 스튜디오)
2. 시스템 설정 → Ethernet
3. IP 주소 설정 (예: 192.168.2.210)
4. Port: 3000 또는 5006

### 사용 예시

#### 단일 데이터 읽기

```python
response = requests.post(
    'http://localhost:5000/api/plc/read-tag',
    json={
        'plc_name': 'MITSU_PLC_1',
        'tag': 'D100'
    }
)
value = response.json()['data']['value']
print(f"D100 = {value}")
```

#### 쓰기

```python
response = requests.post(
    'http://localhost:5000/api/plc/write-tag',
    json={
        'plc_name': 'MITSU_PLC_1',
        'tag': 'D100',
        'value': 12345
    }
)
```

### 성능 최적화

```json
{
  "MITSUBISHI": {
    "USEYN": "Y",
    "NAME": "MITSU_PLC_1",
    "IP": "192.168.2.210",
    "PORT": 3000,
    "TAGS": ["D100", "D101"],
    "SUBSCRIPTION": {
      "MODE": "auto",
      "ACTIVE_POLL_MS": 50,      // 빠른 응답
      "IDLE_POLL_MS": 500,
      "BURST_CYCLES": 20
    }
  }
}
```

---

## 🔵 Siemens (S7 PLC)

### 개요

Siemens SIMATIC S5/S7 시리즈와의 통신입니다.

**지원 모델:**
- S7-200, S7-300, S7-400
- S7-1200, S7-1500

**프로토콜:** ISO-over-TCP (S7 프로토콜)

**장점:**
- ✅ 직접 연결
- ✅ Siemens 시스템 표준

**단점:**
- ❌ Siemens PLC만 지원
- ❌ Rack/Slot 번호 필요

### 설정

```json
{
  "SIEMENS": {
    "USEYN": "Y",
    "NAME": "S7_PLC_1",
    "IP": "192.168.2.211",
    "PORT": 102,
    "RACK": 0,
    "SLOT": 1,
    "TAGS": [
      "DB1.DBW0",
      "DB1.DBD4",
      "DB2.DBB8"
    ],
    "SUBSCRIPTION": {
      "MODE": "auto",
      "ACTIVE_POLL_MS": 100,
      "IDLE_POLL_MS": 1000,
      "BURST_CYCLES": 10
    }
  }
}
```

### S7 주소 형식

```
데이터 블록:
  DB<번호>.DBW<오프셋>    (Word 크기)
  DB<번호>.DBD<오프셋>    (Double Word)
  DB<번호>.DBB<오프셋>    (Byte)
  DB<번호>.DBX<오프셋>    (Bit)

입출력:
  I<번호>.<비트>          (입력)
  Q<번호>.<비트>          (출력)
  %I<번호>.<비트>         (입력)
  %Q<번호>.<비트>         (출력)

메모리:
  M<번호>.<비트>          (메모리)
  %M<번호>                (메모리)

예시:
- DB1.DBW0      (Data Block 1, Word 0)
- DB1.DBD10     (Data Block 1, Double Word 10)
- I0.0          (입력 비트)
- Q1.0          (출력 비트)
- M0.0          (메모리 비트)
```

### Rack/Slot 번호 찾기

#### S7-300/400

```
S7-300:
- RACK = 0
- SLOT = 매개변수(보통 2)

S7-400:
- RACK = 0
- SLOT = 매개변수(보통 3)
```

#### S7-1200/1500

```
- RACK = 0
- SLOT = 0 (고정)
```

### 사용 예시

```python
response = requests.post(
    'http://localhost:5000/api/plc/read-tag',
    json={
        'plc_name': 'S7_PLC_1',
        'tag': 'DB1.DBW0'
    }
)
print(response.json()['data']['value'])
```

---

## 🟢 Rockwell (Allen-Bradley)

### 개요

Rockwell CompactLogix/ControlLogix 시리즈와의 통신입니다.

**프로토콜:** Ethernet/IP (EIPS)

**지원 모델:**
- CompactLogix 5370
- ControlLogix 5570
- GuardLogix

**장점:**
- ✅ 태그명 기반 읽기 (간단)
- ✅ 구조체/배열 지원

### 설정

```json
{
  "ROCKWELL": {
    "USEYN": "Y",
    "NAME": "ROCKWELL_PLC_1",
    "IP": "192.168.2.212",
    "PORT": 44818,
    "SLOT": 0,
    "TAGS": [
      "Program:MainProgram.Motor_Speed",
      "Program:MainProgram.Pump_Enable",
      "Global_Counter"
    ]
  }
}
```

### 태그명 형식

```
프로그램 태그:
  Program:<프로그램명>.<태그명>
  예: Program:MainProgram.Motor_Speed

컨트롤러 태그:
  <태그명>
  예: Global_Speed

배열:
  <태그명>[인덱스]
  예: DataArray[0]

구조체:
  <태그명>.<멤버>
  예: Status.Ready

중괄호:
  <태그명>.<멤버>[인덱스]
  예: Registry[0].Enable
```

### Rockwell PLC IP 설정

1. Studio 5000 접속
2. CPU 설정 → Ethernet
3. IP 주소 설정
4. 스캔 시간: 기본 50ms

### 사용 예시

```python
response = requests.post(
    'http://localhost:5000/api/plc/read-tag',
    json={
        'plc_name': 'ROCKWELL_PLC_1',
        'tag': 'Program:MainProgram.Motor_Speed'
    }
)
```

---

## 📊 드라이버 비교

| 기능 | OPC UA | OPC DA | Mitsubishi | Siemens | Rockwell |
|------|--------|--------|------------|---------|----------|
| 플랫폼 | 크로스 | Windows | 크로스 | 크로스 | 크로스 |
| 보안 | 높음 | 낮음 | 중간 | 중간 | 중간 |
| 응답 속도 | 중간 | 느림 | 빠름 | 빠름 | 빠름 |
| 설정 난이도 | 높음 | 높음 | 낮음 | 중간 | 낮음 |
| 호환성 | 광범위 | 제한됨 | Mitsubishi만 | Siemens만 | Rockwell만 |
| 비용 | 무료 | 무료 | 무료 | 무료 | 무료 |

---

## 🔧 드라이버 문제 해결

### 연결 불가

```
CheckList:
1. IP 주소 확인: ping <IP>
2. 방화벽 확인: inbound 규칙 확인
3. PLC 전원 확인
4. 포트 확인: netstat -ano | findstr :<PORT>
5. 로그 확인: PLC Manager 시작 실패 메시지
```

### 태그 읽기 실패

```
CheckList:
1. 태그명 형식 확인
2. 태그 주소 범위 확인
3. PLC 프로그램 상태 확인 (RUN/STOP)
4. 권한 확인 (쓰기 보호)
```

### 성능 저하

```
해결 방안:
1. 폴링 간격 증가
2. 태그 수 감소
3. 네트워크 최적화
4. CPU 부하 확인
```

---

## 📞 지원

드라이버별 문제는 [TROUBLESHOOTING.md](TROUBLESHOOTING.md) 참고
