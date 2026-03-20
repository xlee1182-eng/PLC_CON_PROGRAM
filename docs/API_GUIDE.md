# API 가이드

PLC_CON_PROGRAM의 모든 HTTP API 엔드포인트를 상세히 설명합니다.

## 📡 기본 정보

### 서버 주소

```
http://localhost:5000
```

### 응답 형식

모든 API는 다음 형식으로 응답합니다:

```json
{
  "status": "OK" | "ERROR",
  "msg": "메시지",
  "data": { /* 데이터 */ }
}
```

### 에러 응답

```json
{
  "status": "ERROR",
  "msg": "에러 메시지",
  "data": null
}
```

---

## ✅ API 엔드포인트

### 1. 서버 상태 확인

#### GET `/`

서버 상태를 확인합니다.

**요청:**
```bash
curl http://localhost:5000
```

**응답:**
```json
{
  "status": "OK",
  "msg": "The PLC_CON_Program is running now.",
  "data": null
}
```

**상태 코드:** 200 OK

---

### 2. 웹 대시보드

#### GET `/web`

대시보드 HTML 페이지를 반환합니다.

**요청:**
```bash
curl http://localhost:5000/web
```

**응답:** HTML 문서

**상태 코드:** 200 OK

---

### 3. PLC 읽기 (Query 방식)

#### GET `/plc_read`

쿼리 파라미터를 사용한 PLC 태그 읽기

**요청:**
```bash
curl "http://localhost:5000/plc_read?plc_name=MITSU_PLC_1&tag=D100"
```

**파라미터:**

| 파라미터 | 타입 | 필수 | 설명 |
|---------|------|------|------|
| `plc_name` | string | O | PLC 이름 (Config.json의 NAME) |
| `tag` | string | O | 태그명 (Config.json의 TAGS 중 하나) |

**응답:**
```json
{
  "status": "OK",
  "msg": "Read command success",
  "data": {
    "plcName": "MITSU_PLC_1",
    "tag": "D100",
    "value": 123
  }
}
```

**에러 응답:**
```json
{
  "status": "ERROR",
  "msg": "PLC 'UNKNOWN_PLC' not found",
  "data": null
}
```

**상태 코드:**
- 200 OK: 성공
- 503 Service Unavailable: PLC Manager 준비 안 됨
- 500 Internal Server Error: 기타 오류

**예시:**
```bash
# Mitsubishi D100 읽기
curl "http://localhost:5000/plc_read?plc_name=MITSU_PLC_1&tag=D100"

# OPC UA 태그 읽기
curl "http://localhost:5000/plc_read?plc_name=OPCUA_PLC_1&tag=ns%3D2%3Bs%3DChannel2.Device2.B0"
```

---

### 4. PLC 쓰기 (Query 방식)

#### GET `/plc_write`

쿼리 파라미터를 사용한 PLC 태그 쓰기

**요청:**
```bash
curl "http://localhost:5000/plc_write?plc_name=MITSU_PLC_1&tag=D100&value=123"
```

**파라미터:**

| 파라미터 | 타입 | 필수 | 설명 |
|---------|------|------|------|
| `plc_name` | string | O | PLC 이름 |
| `tag` | string | O | 태그명 |
| `value` | string | O | 쓸 값 |

**응답:**
```json
{
  "status": "OK",
  "msg": "Write command sent to PLC.",
  "data": null
}
```

**상태 코드:**
- 200 OK: 성공
- 503 Service Unavailable: PLC Manager 준비 안 됨
- 500 Internal Server Error: 기타 오류

**예시:**
```bash
# 정수 쓰기
curl "http://localhost:5000/plc_write?plc_name=MITSU_PLC_1&tag=D100&value=123"

# 실수 쓰기
curl "http://localhost:5000/plc_write?plc_name=MITSU_PLC_1&tag=D101&value=45.67"

# 문자열 쓰기
curl "http://localhost:5000/plc_write?plc_name=MITSU_PLC_1&tag=TAG&value=TEST"
```

---

### 5. PLC 읽기 (JSON 방식)

#### POST `/api/plc/read-tag`

JSON 바디를 사용한 PLC 태그 읽기

**요청:**
```bash
curl -X POST http://localhost:5000/api/plc/read-tag \
  -H "Content-Type: application/json" \
  -d '{
    "plc_name": "MITSU_PLC_1",
    "tag": "D100"
  }'
```

**요청 바디:**
```json
{
  "plc_name": "string",  // 필수
  "tag": "string"        // 필수
}
```

**응답:**
```json
{
  "status": "OK",
  "msg": "Read command success",
  "data": {
    "plcName": "MITSU_PLC_1",
    "tag": "D100",
    "value": 123
  }
}
```

**예시:**

Python:
```python
import requests

response = requests.post(
    'http://localhost:5000/api/plc/read-tag',
    json={
        'plc_name': 'MITSU_PLC_1',
        'tag': 'D100'
    }
)
print(response.json())
```

JavaScript:
```javascript
fetch('http://localhost:5000/api/plc/read-tag', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    plc_name: 'MITSU_PLC_1',
    tag: 'D100'
  })
})
.then(r => r.json())
.then(data => console.log(data));
```

---

### 6. PLC 쓰기 (JSON 방식)

#### POST `/api/plc/write-tag`

JSON 바디를 사용한 PLC 태그 쓰기

**요청:**
```bash
curl -X POST http://localhost:5000/api/plc/write-tag \
  -H "Content-Type: application/json" \
  -d '{
    "plc_name": "MITSU_PLC_1",
    "tag": "D100",
    "value": 123
  }'
```

**요청 바디:**
```json
{
  "plc_name": "string",  // 필수
  "tag": "string",       // 필수
  "value": "any"         // 필수 (숫자, 문자열 등 가능)
}
```

**응답:**
```json
{
  "status": "OK",
  "msg": "Write command sent to PLC.",
  "data": {
    "plcName": "MITSU_PLC_1",
    "tag": "D100",
    "value": 123
  }
}
```

**예시:**

Python:
```python
import requests

response = requests.post(
    'http://localhost:5000/api/plc/write-tag',
    json={
        'plc_name': 'MITSU_PLC_1',
        'tag': 'D100',
        'value': 123
    }
)
print(response.json())
```

JavaScript:
```javascript
fetch('http://localhost:5000/api/plc/write-tag', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    plc_name: 'MITSU_PLC_1',
    tag: 'D100',
    value: 123
  })
})
.then(r => r.json())
.then(data => console.log(data));
```

---

### 7. PLC 목록 확인

#### GET `/plc_list`

모든 연결된 PLC 정보를 조회합니다.

**요청:**
```bash
curl http://localhost:5000/plc_list
```

**응답:**
```json
{
  "status": "OK",
  "msg": "List of PLC devices",
  "data": [
    {
      "name": "MITSU_PLC_1",
      "driver_type": "MITSUBISHI",
      "ip": "192.168.2.210",
      "port": 3000,
      "connected": true,
      "tags": ["D100", "D101"],
      "supports_subscription": true,
      "supports_read_tag": true
    },
    {
      "name": "OPCUA_PLC_1",
      "driver_type": "OPCUA",
      "ip": "127.0.0.1",
      "port": 49320,
      "connected": true,
      "tags": ["ns=2;s=Channel2.Device2.B0"],
      "supports_subscription": true,
      "supports_read_tag": true
    }
  ]
}
```

**상태 코드:** 200 OK

---

### 8. 시스템 상태

#### GET `/manager_status`

PLC Manager의 상태 및 통계를 조회합니다.

**요청:**
```bash
curl http://localhost:5000/manager_status
```

**응답:**
```json
{
  "status": "OK",
  "msg": "Manager status",
  "data": {
    "running": true,
    "plc_count": 2,
    "active_poll_tasks": 2,
    "plcs": [
      {
        "name": "MITSU_PLC_1",
        "driver_type": "MITSUBISHI",
        "ip": "192.168.2.210",
        "port": 3000,
        "connected": true,
        "tags": ["D100", "D101"],
        "supports_subscription": true,
        "supports_read_tag": true
      }
    ]
  }
}
```

**상태 코드:** 200 OK

---

## 🔑 인증

현재 버전에서는 인증이 없습니다.

프로덕션 환경에서는 다음을 권장합니다:
- API Key 기반 인증
- JWT Bearer Token
- OAuth2

---

## 🔄 CORS (크로스 오리진)

모든 오리진 (`*`)에서 요청 가능하도록 설정되어 있습니다.

프로덕션 환경에서는 `main.py`의 `origins` 설정을 변경하세요:

```python
origins = [
    "http://localhost:3000",
    "http://example.com",
]
```

---

## 📊 사용 예시

### Python Client

```python
import requests
import json

BASE_URL = 'http://localhost:5000'

# 1. 서버 상태 확인
response = requests.get(f'{BASE_URL}/')
print(response.json())

# 2. PLC 목록 조회
response = requests.get(f'{BASE_URL}/plc_list')
plcs = response.json()['data']
print(f"연결된 PLC: {len(plcs)}")

# 3. PLC 읽기
response = requests.post(
    f'{BASE_URL}/api/plc/read-tag',
    json={'plc_name': 'MITSU_PLC_1', 'tag': 'D100'}
)
value = response.json()['data']['value']
print(f"D100 값: {value}")

# 4. PLC 쓰기
response = requests.post(
    f'{BASE_URL}/api/plc/write-tag',
    json={
        'plc_name': 'MITSU_PLC_1',
        'tag': 'D100',
        'value': 456
    }
)
print("쓰기 완료")
```

### cURL 예시

```bash
# 1. 서버 상태
curl http://localhost:5000

# 2. PLC 목록
curl http://localhost:5000/plc_list

# 3. PLC 읽기 (Query)
curl "http://localhost:5000/plc_read?plc_name=MITSU_PLC_1&tag=D100"

# 4. PLC 쓰기 (Query)
curl "http://localhost:5000/plc_write?plc_name=MITSU_PLC_1&tag=D100&value=456"

# 5. PLC 읽기 (JSON)
curl -X POST http://localhost:5000/api/plc/read-tag \
  -H "Content-Type: application/json" \
  -d '{"plc_name":"MITSU_PLC_1","tag":"D100"}'

# 6. PLC 쓰기 (JSON)
curl -X POST http://localhost:5000/api/plc/write-tag \
  -H "Content-Type: application/json" \
  -d '{"plc_name":"MITSU_PLC_1","tag":"D100","value":456}'
```

---

## ⚠️ 에러 처리

### 일반 에러 코드

| 상태 코드 | 설명 |
|----------|------|
| 200 | 성공 |
| 400 | 잘못된 요청 |
| 404 | 리소스 없음 |
| 500 | 서버 내부 오류 |
| 503 | 서비스 사용 불가 (PLC Manager 준비 안 됨) |

### 재시도 전략

```python
import requests
import time

def api_call_with_retry(method, url, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = requests.request(method, url)
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 503:
                # PLC Manager 준비 중
                time.sleep(2)
                continue
            else:
                print(f"오류: {response.status_code}")
                break
        except requests.exceptions.RequestException as e:
            print(f"연결 오류: {e}")
            time.sleep(1)
    return None
```

---

## 🧪 테스트

### Postman 사용

1. Postman 설치
2. 새 Collection 생성
3. 요청 추가:
   - **GET** `http://localhost:5000/`
   - **POST** `http://localhost:5000/api/plc/read-tag` (JSON 바디)
   - **POST** `http://localhost:5000/api/plc/write-tag` (JSON 바디)
4. 테스트 실행

### 스크립트 테스트

```bash
# test_api.sh
#!/bin/bash

echo "=== API 테스트 시작 ==="

echo "1. 서버 상태"
curl http://localhost:5000
echo ""

echo "2. PLC 목록"
curl http://localhost:5000/plc_list
echo ""

echo "3. PLC 읽기"
curl -X POST http://localhost:5000/api/plc/read-tag \
  -H "Content-Type: application/json" \
  -d '{"plc_name":"MITSU_PLC_1","tag":"D100"}'
echo ""

echo "=== 테스트 완료 ==="
```

---

## 📞 지원

문제 발생 시 [TROUBLESHOOTING.md](TROUBLESHOOTING.md) 참고
