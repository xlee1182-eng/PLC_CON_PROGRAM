# 설정 가이드

Config.json 파일을 상세히 설정하는 방법을 설명합니다.

## 📄 Config.json 구조

```json
{
  "PLC_INFO": {
    "OPCUA": { /* OPC UA 설정 */ },
    "OPCDA": { /* OPC DA 설정 */ },
    "MITSUBISHI": { /* Mitsubishi 설정 */ },
    "SIEMENS": { /* Siemens 설정 */ },
    "ROCKWELL": { /* Rockwell 설정 */ }
  }
}
```

---

## 🔧 공통 설정 항목

모든 PLC 타입에서 공통적으로 사용되는 항목:

### USEYN (필수)

PLC 사용 여부

```json
"USEYN": "Y"   // Y (사용) or N (미사용)
```

**설명:**
- `"Y"`: 서버 시작 시 이 PLC 초기화
- `"N"`: 이 PLC 무시

### NAME (필수)

PLC의 고유 이름

```json
"NAME": "MITSU_PLC_1"
```

**설명:**
- API 호출 시 사용 (`plc_name` 파라미터)
- 동일한 타입의 여러 PLC 구분용
- 알파벳, 숫자, 언더스코어만 사용

**예시:**
```json
{
  "MITSUBISHI": {
    "USEYN": "Y",
    "NAME": "MITSUBISHI_1",
    ...
  },
  "MITSUBISHI_2": {
    "USEYN": "Y",
    "NAME": "MITSUBISHI_2",
    ...
  }
}
// ✓ 불가능 (동일 타입, 다른 인스턴스 필요)
```

### IP (필수)

PLC의 IP 주소

```json
"IP": "192.168.2.210"
```

**예시:**
- 로컬호스트: `"127.0.0.1"` 또는 `"localhost"`
- 네트워크: `"192.168.1.100"`
- DHCP: IP 고정 권장

### PORT (필수)

통신 포트

```json
"PORT": 3000
```

**기본값 (타입별):**

| 타입 | 기본 포트 | 설정 가능 범위 |
|------|---------|------|
| OPCUA | 4840 | 1000-65535 |
| MITSUBISHI | 5006/3000 | 1000-65535 |
| SIEMENS | 102 | 1000-65535 |
| ROCKWELL | 44818 | 1000-65535 |
| OPCDA | 0 | - |

### TAGS (필수)

모니터링할 태그 목록

```json
"TAGS": ["D100", "D101", "D102"]
```

타입별 형식:

| 타입 | 형식 | 예시 |
|------|------|------|
| OPCUA | OPC UA 노드 ID | `"ns=2;s=Channel2.Device2.B0"` |
| Mitsubishi | 메모리 주소 | `"D100"`, `"M10"`, `"Y5"` |
| Siemens | S7 주소 | `"DB1.DBW10"`, `"%M1.0"` |
| Rockwell | 태그명 | `"Pump_Speed"`, `"Valve_State"` |
| OPCDA | OPC 경로 | `"Channel1.Device1.D1001"` |

---

## 📡 타입별 상세 설정

### 1. OPC UA (최신 표준)

```json
{
  "OPCUA": {
    "USEYN": "Y",
    "NAME": "OPCUA_PLC_1",
    "IP": "127.0.0.1",
    "PORT": 4840,
    "TAGS": [
      "ns=2;s=Channel2.Device2.B0",
      "ns=2;s=Channel2.Device2.D1001"
    ]
  }
}
```

**설정 항목:**

| 항목 | 필수 | 설명 |
|------|------|------|
| USEYN | O | 사용 여부 |
| NAME | O | PLC 이름 |
| IP | O | OPC UA 서버 IP |
| PORT | O | 포트 (기본 4840) |
| TAGS | O | 노드 ID 목록 |
| USERNAME | X | 인증 사용자명 |
| PASSWORD | X | 인증 비밀번호 |

**OPC UA 노드 ID 형식:**

```
ns=<네임스페이스>;<타입>=<식별자>

예시:
- ns=2;s=Channel2.Device2.B0
- ns=4;i=12345
- ns=3;g=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx

타입:
  s = String (문자열)
  i = Integer (정수)
  g = GUID (UUID)
  b = Opaque (불투명)
```

**보안 설정 (선택):**

```json
{
  "OPCUA": {
    "USEYN": "Y",
    "NAME": "OPCUA_SECURE",
    "IP": "192.168.1.100",
    "PORT": 4840,
    "TAGS": [...],
    "USERNAME": "user",
    "PASSWORD": "password"
  }
}
```

---

### 2. OPC DA (레거시)

```json
{
  "OPCDA": {
    "USEYN": "N",
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

**설정 항목:**

| 항목 | 필수 | 설명 |
|------|------|------|
| USEYN | O | 사용 여부 |
| NAME | O | PLC 이름 |
| IP | O | OPC 서버 IP (보통 localhost) |
| PORT | O | 0 (사용 안 함) |
| PROG_ID | O | OPC 서버 프로그램 ID |
| TAGS | O | 항목 경로 |

**일반적인 PROG_ID:**

```
삼중: Takebishi.Melsec.1
SIMATIC S7: Siemens.SimaticNET.1
아산기전: AsconOpcServer.WinCC.1
```

**포트 설정:**

⚠️ OPC DA는 Windows COM/DCOM 사용하므로 네트워크 포트 없음
- PORT는 0으로 설정
- DCOM 설정으로 원격 접속 가능 (복잡함)

---

### 3. Mitsubishi (삼중 PLC)

```json
{
  "MITSUBISHI": {
    "USEYN": "Y",
    "NAME": "MITSU_PLC_1",
    "IP": "192.168.2.210",
    "PORT": 3000,
    "TAGS": ["D100", "D5", "D1001", "D1002", "D1003"],
    "SUBSCRIPTION": {
      "MODE": "auto",
      "ACTIVE_POLL_MS": 100,
      "IDLE_POLL_MS": 1000,
      "BURST_CYCLES": 10
    }
  }
}
```

**설정 항목:**

| 항목 | 필수 | 기본값 | 설명 |
|------|------|--------|------|
| USEYN | O | - | 사용 여부 |
| NAME | O | - | PLC 이름 |
| IP | O | - | PLC IP |
| PORT | O | 3000 또는 5006 | 포트 |
| TAGS | O | - | 메모리 주소 |
| SUBSCRIPTION.MODE | X | "auto" | 폴링 모드 |
| SUBSCRIPTION.ACTIVE_POLL_MS | X | 100 | 활동 중 폴링 간격 (ms) |
| SUBSCRIPTION.IDLE_POLL_MS | X | 1000 | 유휴 상태 폴링 간격 (ms) |
| SUBSCRIPTION.BURST_CYCLES | X | 10 | 버스트 사이클 수 |

**Mitsubishi 메모리 주소:**

```
데이터 메모리:        D0, D100, D1001
보조 메모리:          B0, B100
타이머:              T0, T100
카운터:              C0, C100
입력:                X0, X10
출력:                Y0, Y10
```

**폴링 전략:**

```
MODE: "auto" (추천)
│
├─ 활동 상태 (최근 읽기 있음)
│  └─ ACTIVE_POLL_MS (기본 100ms) 간격으로 폴링
│
├─ 유휴 상태 (읽기 없음)
│  └─ IDLE_POLL_MS (기본 1000ms) 간격으로 폴링
│
└─ 버스트 상태
   └─ BURST_CYCLES (기본 10) 주기 동안 빠른 폴링
```

**권장 설정:**

```json
// 빠른 응답 필요 (기계 제어)
"SUBSCRIPTION": {
  "MODE": "auto",
  "ACTIVE_POLL_MS": 50,
  "IDLE_POLL_MS": 500,
  "BURST_CYCLES": 20
}

// 느린 모니터링 (에너지 절약)
"SUBSCRIPTION": {
  "MODE": "auto",
  "ACTIVE_POLL_MS": 500,
  "IDLE_POLL_MS": 5000,
  "BURST_CYCLES": 5
}
```

---

### 4. Siemens (S7 PLC)

```json
{
  "SIEMENS": {
    "USEYN": "N",
    "NAME": "S7_PLC_1",
    "IP": "192.168.2.211",
    "PORT": 102,
    "RACK": 0,
    "SLOT": 1,
    "TAGS": ["DB1.DBW0", "DB1.DBW2"],
    "SUBSCRIPTION": {
      "MODE": "auto",
      "ACTIVE_POLL_MS": 100,
      "IDLE_POLL_MS": 1000,
      "BURST_CYCLES": 10
    }
  }
}
```

**설정 항목:**

| 항목 | 필수 | 설명 |
|------|------|------|
| USEYN | O | 사용 여부 |
| NAME | O | PLC 이름 |
| IP | O | PLC IP |
| PORT | O | 포트 (보통 102) |
| RACK | O | 랙 번호 (보통 0) |
| SLOT | O | 슬롯 번호 (보통 1) |
| TAGS | O | S7 주소 |
| SUBSCRIPTION | X | 폴링 설정 |

**Siemens 주소 형식:**

```
데이터 블록:         DB<블록번호>.<오프셋>
입력:               %I 또는 I<위치>
출력:               %Q 또는 Q<위치>
메모리:             %M 또는 M<위치>
타이머:             T<번호>
카운터:             C<번호>

예시:
- DB1.DBW0         (Data Block 1, Word 0)
- DB1.DBD4         (Data Block 1, Double Word 4)
- DB1.DBB8         (Data Block 1, Byte 8)
- %M0.0            (메모리 비트)
- I0.0             (입력 비트)
- Q1.0             (출력 비트)
```

---

### 5. Rockwell (Allen-Bradley)

```json
{
  "ROCKWELL": {
    "USEYN": "N",
    "NAME": "ROCKWELL_PLC_1",
    "IP": "192.168.2.212",
    "PORT": 44818,
    "SLOT": 0,
    "PATH": [1, 0],
    "TAGS": ["Program:MainProgram.Global_Var1"],
    "SUBSCRIPTION": {
      "MODE": "auto",
      "ACTIVE_POLL_MS": 100,
      "IDLE_POLL_MS": 1000,
      "BURST_CYCLES": 10
    }
  }
}
```

**설정 항목:**

| 항목 | 필수 | 설명 |
|------|------|------|
| USEYN | O | 사용 여부 |
| NAME | O | PLC 이름 |
| IP | O | PLC IP |
| PORT | O | 포트 (기본 44818) |
| SLOT | O | CPU 슬롯 (보통 0) |
| PATH | X | 통신 경로 |
| TAGS | O | 태그 이름 |
| SUBSCRIPTION | X | 폴링 설정 |

**Rockwell 태그 형식:**

```
프로그램 태그:   Program:MainProgram.TagName
컨트롤러 태그:   ControllerName.TagName
배열 요소:       ArrayName[0]
구조체 멤버:     StructName.MemberName

예시:
- MainProgram.Motor_Speed
- MainProgram.Sensor_State
- MainProgram.Counter[0]
- MainProgram.Status.Ready
```

---

## 🔀 다중 PLC 설정

동일 네트워크에 여러 PLC가 있는 경우:

```json
{
  "PLC_INFO": {
    "MITSUBISHI": {
      "USEYN": "Y",
      "NAME": "MITSU_FACTORY_A",
      "IP": "192.168.1.100",
      "PORT": 3000,
      "TAGS": ["D0", "D100"]
    },
    "MITSUBISHI_2": {
      "USEYN": "Y",
      "NAME": "MITSU_FACTORY_B",
      "IP": "192.168.1.101",
      "PORT": 3000,
      "TAGS": ["D0", "D100"]
    },
    "SIEMENS": {
      "USEYN": "Y",
      "NAME": "SIEMENS_1",
      "IP": "192.168.1.200",
      "PORT": 102,
      "RACK": 0,
      "SLOT": 1,
      "TAGS": ["DB1.DBW0"]
    }
  }
}
```

⚠️ 주의: 타입이 다르면 자동으로 다중 인스턴스 생성 (설정 파일 확장 필요)

---

## 🌐 네트워크 설정

### 로컬 PLC 접속

```json
"IP": "127.0.0.1"
또는
"IP": "localhost"
```

### 원격 PLC 접속

```json
"IP": "192.168.1.100"
```

**방화벽 설정:**

```
인바운드 규칙:
- 포트 3000: Mitsubishi
- 포트 102: Siemens
- 포트 4840: OPC UA
- 포트 44818: Rockwell
```

### VPN을 통한 접속

```json
"IP": "vpn-gateway.example.com"
```

---

## ⚙️ 고급 설정

### 타임아웃 설정

환경 변수로 설정:

```bash
set PLC_OPERATION_TIMEOUT_SEC=5.0
python server.py
```

또는 `.env` 파일:

```
PLC_OPERATION_TIMEOUT_SEC=5.0
```

기본값: 3.0초

### 로깅 레벨

```bash
set LOGURU_LEVEL=DEBUG
python server.py
```

레벨: DEBUG, INFO, WARNING, ERROR, CRITICAL

---

## ✅ 설정 검증

### Config.json 문법 확인

```python
import json

with open('Config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)
    print("✓ 유효한 JSON")
```

### Python에서 실행 확인

```bash
python -m json.tool Config.json
```

### 서버 로그 확인

```bash
python server.py
# INFO 로그에서 설정된 PLC 확인
```

---

## 🐛 일반적인 설정 오류

### 1. 포트 충돌

❌ 오류:
```
OSError: [Errno 48] Address already in use
```

✓ 해결:
```json
"PORT": 5007  // 다른 포트로 변경
```

### 2. IP 주소 오류

❌ 오류:
```
ConnectionRefused: [Errno 111]
```

✓ 확인:
```bash
ping 192.168.2.210  // IP 접근 가능 확인
```

### 3. 태그 형식 오류

❌ 잘못된 형식:
```json
"TAGS": ["D 100"]   // 공백 포함
```

✓ 올바른 형식:
```json
"TAGS": ["D100"]    // 공백 없음
```

### 4. 인코딩 오류

❌ 오류:
```
UnicodeDecodeError
```

✓ Config.json 저장 시 UTF-8 인코딩 사용

---

## 📋 체크리스트

설정 완료 전:

- [ ] Config.json이 유효한 JSON 형식
- [ ] USEYN이 "Y" 또는 "N"
- [ ] NAME이 고유함
- [ ] IP 주소가 정확함
- [ ] PORT가 사용 가능함
- [ ] TAGS 형식이 정확함
- [ ] 방화벽에서 포트 허용함
- [ ] PLC가 켜져 있고 응답함

---

## 📞 지원

설정 문제는 [TROUBLESHOOTING.md](TROUBLESHOOTING.md) 참고
