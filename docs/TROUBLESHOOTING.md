# 문제 해결 가이드

자주 발생하는 문제와 해결 방법을 정리합니다.

## 🔴 설치 및 환경

### 문제: Python이 설치되지 않음

**증상:**
```
'python' is not recognized as an internal or external command
```

**해결:**
1. [python.org](https://www.python.org/) 에서 Python 3.8+ 다운로드
2. 설치 시 **"Add Python to PATH"** 체크
3. 터미널 재시작 후 확인:
   ```bash
   python --version
   ```

---

### 문제: 가상환경 활성화 실패

**증상:**
```
PowerShell 실행 정책 오류 또는 명령어 인식 안 됨
```

**해결 (Windows PowerShell):**
```powershell
# 현재 권한 정책 확인
Get-ExecutionPolicy

# 권한 정책 변경 (관리자 권한 필요)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# 가상환경 재시도
venv\Scripts\activate
```

**해결 (Windows CMD):**
```cmd
venv\Scripts\activate.bat
```

---

### 문제: 의존성 설치 실패

**증상:**
```
ERROR: Could not find a version that satisfies the requirement
```

**해결:**
```bash
# 1. pip 업그레이드
python -m pip install --upgrade pip

# 2. 캐시 삭제 후 재설치
pip install --no-cache-dir -r requirements.txt

# 3. 개별 설치 시도
pip install fastapi==0.135.1
pip install uvicorn==0.42.0
# ... 나머지 패키지

# 4. 네트워크 문제시 타임아웃 증가
pip install --default-timeout=1000 -r requirements.txt
```

---

### 문제: pywin32 설정 오류 (OPC DA용)

**증상:**
```
ModuleNotFoundError: No module named 'win32com'
```

**해결 (Windows 관리자 권한):**
```cmd
pip install pywin32
python -m pip install -U --force-reinstall pywin32
python -m pywin32_postinstall -install
```

---

## 🟡 서버 실행

### 문제: 포트 5000이 이미 사용 중

**증상:**
```
OSError: [Errno 48] Address already in use
또는
Errno 10048 - 정상 작동 상태에서 소켓 작업을 할 수 없습니다
```

**진단:**
```powershell
# Windows: 포트 사용 프로세스 확인
netstat -ano | findstr :5000

# 또는
Get-Process | Where-Object {$_.Id -eq <PID>}
```

**해결 방법 1: 기존 프로세스 종료**
```powershell
# 프로세스 PID 확인 후
taskkill /PID <PID> /F

# 예시
taskkill /PID 1234 /F
```

**해결 방법 2: 다른 포트 사용**

`server.py` 수정:
```python
if __name__ == '__main__':
  uvicorn.run('app.main:app', 
              host = '0.0.0.0', 
              port = 8000,  # ← 변경
              use_colors = True, 
              log_config = None)
```

**해결 방법 3: 포트 대기 설정**
```bash
# Unix/Linux: 포트 강제 재사용
sudo lsof -ti:5000 | xargs kill -9
python server.py
```

---

### 문제: Config.json 로드 오류

**증상:**
```
FileNotFoundError: [Errno 2] No such file or directory: 'Config.json'
또는
json.decoder.JSONDecodeError: Expecting value
```

**진단:**
```bash
# Config.json 존재 확인
ls -la Config.json  # Linux/macOS
dir Config.json     # Windows

# JSON 문법 확인
python -m json.tool Config.json
```

**해결:**
1. Config.json 파일이 프로젝트 루트에 있는지 확인
2. JSON 형식 검증 (쉼표, 따옴표 확인)
3. UTF-8 인코딩으로 저장되어 있는지 확인
4. 경로 문제시 절대 경로 사용

---

### 문제: 서버 시작 후 즉시 모든 PLC 연결 실패

**증상:**
```
PLC build error (MITSUBISHI): Connection refused
```

**확인 사항:**
1. PLC가 켜져 있는가?
2. 네트워크 연결이 되어 있는가?
3. IP 주소가 정확한가?
4. 방화벽이 포트를 차단하지 않는가?

**진단:**
```bash
# IP 접근 가능 확인
ping 192.168.2.210

# 포트 접근 가능 확인 (Windows)
netstat -ano | findstr :3000

# 포트 접근 가능 확인 (Linux)
telnet 192.168.2.210 3000
```

**해결:**
```json
// Config.json에서 USEYN을 "N"으로 설정하여 비활성화
{
  "MITSUBISHI": {
    "USEYN": "N",  // ← 나중에 다시 시도
    ...
  }
}
```

---

## 🔵 PLC 연결

### 문제: PLC에 연결되지 않음

**증상:**
```
HTTP 503: PLC manager is not ready
또는
PLC '<name>' not found
```

**확인:**
1. PLC 전원 확인
2. 네트워크 연결 확인
3. IP/PORT 확인

**수정:**

```bash
# 로그 확인
python server.py  # 로그 메시지 읽기

# 테스트 연결
ping <PLC_IP>
```

---

### 문제: 특정 PLC만 연결 불가

**증상:**
```
PLC build error (SIEMENS): Connection timeout
```

**해결 단계:**

1. **부팅 전 대기**
   ```python
   # server.py에 대기 추가
   import time
   time.sleep(10)  # 10초 대기
   uvicorn.run(...)
   ```

2. **재시도 설정 확인**
   - PLC Manager의 자동 재연결 확인

3. **타임아웃 증가**
   ```bash
   set PLC_OPERATION_TIMEOUT_SEC=10.0
   python server.py
   ```

---

## 🟢 API 호출

### 문제: API 응답 없음 (타임아웃)

**증상:**
```
requests.exceptions.Timeout: HTTPConnectionPool timeout
또는
TimeoutError: <context> timeout after 3.0s
```

**원인:**
- PLC 응답 느림
- 네트워크 지연
- 너무 짧은 타임아웃 설정

**해결:**

```python
# Python 클라이언트
import requests

response = requests.post(
    'http://localhost:5000/api/plc/read-tag',
    json={'plc_name': 'MITSU_PLC_1', 'tag': 'D100'},
    timeout=10  # ← 타임아웃 증가
)
```

또는 환경 변수:
```bash
set PLC_OPERATION_TIMEOUT_SEC=10.0
python server.py
```

---

### 문제: 태그를 읽을 수 없음

**증상:**
```json
{
  "status": "ERROR",
  "msg": "PLC 'MITSU_PLC_1' not found",
  "data": null
}
```

**확인:**
1. PLC 이름이 정확한가? (Config.json의 NAME)
2. PLC가 USEYN: "Y"로 활성화되었는가?
3. 태그명 형식이 정확한가?

**예시 (Mitsubishi):**
```bash
# ❌ 잘못된 형식
curl "http://localhost:5000/plc_read?plc_name=MITSU_PLC_1&tag=D 100"

# ✅ 올바른 형식
curl "http://localhost:5000/plc_read?plc_name=MITSU_PLC_1&tag=D100"
```

---

### 문제: 태그 읽기는 되지만 쓰기 실패

**증상:**
```json
{
  "status": "ERROR",
  "msg": "Tag is read-only",
  "data": null
}
```

**해결:**
1. PLC에서 쓰기 권한 확인
2. 태그 보호 해제
3. 관리자 권한으로 실행

---

## 🔴 PLC 드라이버별 문제

### OPC UA

**문제: 노드를 찾을 수 없음**

```
Node not found: ns=2;s=Channel2.Device2.B0
```

**해결:**
1. UaExpert로 정확한 노드 ID 확인
2. 노드 ID 형식 확인:
   ```
   ✓ ns=2;s=Channel2.Device2.B0
   ✓ ns=4;i=12345
   ✗ Channel2.Device2 (형식 오류)
   ```

---

### OPC DA

**문제: COM 초기화 실패**

```
CoInitializeEx failed
```

**해결:**
```bash
# pywin32 재설치 (관리자 권한)
python -m pip install -U --force-reinstall pywin32
python -m pywin32_postinstall -install
```

**문제: PROG_ID를 찾을 수 없음**

**해결:**
```python
# Registry에서 PROG_ID 찾기
import winreg

key = winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, "ProgID")
for i in range(100):
    try:
        name = winreg.EnumKey(key, i)
        if 'opc' in name.lower():
            print(name)
    except:
        break
```

---

### Mitsubishi

**문제: EthernetIP 포트 오류**

```
Connection refused on port 3000
```

**확인:**
1. PLC 웹 인터페이스 접속 → 네트워크 설정 확인
2. PORT 값: 3000 또는 5006
3. 방화벽: 인바운드 포트 3000, 5006 허용

**문제: D 메모리의 경계 초과**

```
Offset out of range: D10000
```

**PLC별 한계:**
- FX5U: D0-D32767
- iQ-R: D0-D8388607

---

### Siemens

**문제: S7 연결 실패**

```
ISO-over-TCP connection failed
```

**확인:**
1. Rack/Slot 번호 정확성
   - S7-300: RACK=0, SLOT=2 또는 3
   - S7-1200/1500: RACK=0, SLOT=0
2. 방화벽: 포트 102 허용

**문제: DB 블록이 없음**

```
DB1 not found
```

**해결:**
1. PLC에서 해당 DB가 생성되었는지 확인
2. DB 번호와 크기 확인

---

### Rockwell

**문제: 태그명을 찾을 수 없음**

```
Tag 'Motor_Speed' not found
```

**해결:**
1. Studio 5000에서 정확한 태그명 확인
2. 프로그램 태그: `Program:MainProgram.Motor_Speed`
3. 컨트롤러 태그: `Motor_Speed` (프로그램명 제외)

---

## 📊 로그 분석

### 로그 활성화

```bash
set LOGURU_LEVEL=DEBUG
python server.py
```

### 중요한 로그 메시지

```
INFO: PLC manager initialized: 2 PLC(s)
    ✓ 모든 PLC 초기화 완료

ERROR: PLC build error (MITSUBISHI): ...
    ✗ Mitsubishi PLC 초기화 실패

ERROR: API route fatal error: ...
    ✗ API 처리 중 오류
```

### 로그 파일 저장

```python
from loguru import logger

logger.add("app.log", rotation="500 MB")
```

---

## 🧪 진단 도구

### 1. 네트워크 진단

```bash
# IP 접근 가능 확인
ping 192.168.2.210

# 포트 확인
netstat -ano | findstr :3000

# 원격 포트 접근 확인
telnet 192.168.2.210 3000
```

### 2. PLC 정보 확인 API

```bash
# PLC 목록 확인
curl http://localhost:5000/plc_list

# 시스템 상태 확인
curl http://localhost:5000/manager_status
```

### 3. Python 진단 스크립트

```python
# diagnose.py
import json
import requests
from pathlib import Path

def diagnose():
    # 1. Config.json 확인
    try:
        with open('Config.json') as f:
            config = json.load(f)
        print("✓ Config.json 유효")
    except Exception as e:
        print(f"✗ Config.json 오류: {e}")
        return
    
    # 2. 서버 연결 확인
    try:
        response = requests.get('http://localhost:5000', timeout=5)
        print(f"✓ 서버 응답: {response.status_code}")
    except Exception as e:
        print(f"✗ 서버 미응답: {e}")
        return
    
    # 3. PLC 연결 상태 확인
    try:
        response = requests.get('http://localhost:5000/plc_list')
        plcs = response.json()['data']
        for plc in plcs:
            status = "✓" if plc['connected'] else "✗"
            print(f"{status} {plc['name']}: {plc['ip']}:{plc['port']}")
    except Exception as e:
        print(f"✗ PLC 확인 오류: {e}")

if __name__ == '__main__':
    diagnose()
```

실행:
```bash
python diagnose.py
```

---

## 🔄 성능 최적화

### 높은 CPU 사용률

**원인:**
- 폴링 간격이 너무 짧음
- 태그 수가 너무 많음

**해결:**
```json
{
  "MITSUBISHI": {
    "SUBSCRIPTION": {
      "ACTIVE_POLL_MS": 200,  // 100에서 200으로 증가
      "IDLE_POLL_MS": 2000    // 1000에서 2000으로 증가
    }
  }
}
```

### 느린 읽기 성능

**원인:**
- 네트워크 지연
- 태그를 하나씩 읽음

**해결:**
```python
# 배치 읽기로 변경
tags = ['D100', 'D101', 'D102']
results = await asyncio.gather(*[
    plc_manager.read_by_name('MITSU_PLC_1', tag)
    for tag in tags
])
```

---

## 📞 고급 지원

### 상세 로깅으로 디버깅

```python
# 개발용 설정
logger.add("debug.log", level="DEBUG", format="{time} {level} {message}")
logger.enable("asyncua")  # OPC UA 라이브러리 로깅 활성화
```

### 성능 프로파일링

```bash
# cProfile로 성능 분석
python -m cProfile -s cumulative server.py
```

---

## 📋 체크리스트

문제 발생시 확인:

- [ ] Python 버전 3.8+ 확인
- [ ] 가상환경 활성화 확인
- [ ] 의존성 업데이트: `pip install --upgrade -r requirements.txt`
- [ ] Config.json 유효성 확인
- [ ] 네트워크 연결 확인
- [ ] 방화벽 설정 확인
- [ ] PLC 전원 확인
- [ ] 로그 파일 확인

---

## 🆘 여전히 해결 안 되는 경우

1. [TROUBLESHOOTING.md](TROUBLESHOOTING.md) 재검토
2. 로그 파일 전체 검토
3. GitHub Issues에 로그와 함께 보고
4. 커뮤니티 포럼 검색

**보고 시 포함할 정보:**
- Python 버전
- OS 정보
- Config.json (IP/Password 제외)
- 전체 에러 로그
- 시도한 해결책
