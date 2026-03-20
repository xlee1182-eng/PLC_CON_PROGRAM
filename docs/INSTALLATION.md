# 설치 가이드

PLC_CON_PROGRAM을 설치하고 실행하는 방법을 단계별로 설명합니다.

## 📋 사전요구사항

### 시스템 요구사항

- **OS**: Windows, Linux, macOS
- **Python**: 3.8 이상
- **RAM**: 최소 256MB 이상 권장
- **Disk**: 최소 100MB 이상

### 필수 소프트웨어

1. **Python 3.8+**
   - [python.org](https://www.python.org/) 에서 다운로드
   - 설치 시 "Add Python to PATH" 체크

2. **Git** (저장소 클론용)
   - [git-scm.com](https://git-scm.com/) 에서 다운로드

3. **PLC 드라이버**
   - Siemens: Snap7 (선택사항)
   - Mitsubishi: pymcprotocol (자동 설치)
   - OPC DA: pywin32 (자동 설치)

---

## 🔧 설치 단계

### 1단계: 저장소 클론

```bash
# 저장소 복제
git clone <repository-url>

# 프로젝트 디렉토리로 이동
cd PLC_CON_PROGRAM
```

### 2단계: 가상환경 생성 (권장)

#### Windows

```powershell
# 가상환경 생성
python -m venv venv

# 가상환경 활성화
venv\Scripts\activate
```

#### Linux / macOS

```bash
# 가상환경 생성
python3 -m venv venv

# 가상환경 활성화
source venv/bin/activate
```

### 3단계: 의존성 설치

```bash
# pip 업그레이드
pip install --upgrade pip

# 의존성 설치
pip install -r requirements.txt
```

**설치 확인:**
```bash
pip list
```

예상 출력:
```
asyncua              1.1.8
fastapi              0.135.1
humps                0.2.2
loguru               0.7.3
pymcprotocol         0.3.0
pywin32              308
uvicorn              0.42.0
```

### 4단계: 필수 설정

#### pywin32 추가 설정 (OPC DA 사용 시)

Windows에서 OPC DA를 사용할 경우:

```bash
# pywin32 설정 스크립트 실행
python Scripts/pyinstaller.py -w
```

또는 PowerShell (관리자 권한)에서:

```powershell
python -m pip install pywin32

# post-install 스크립트 실행
python -m pip install -U --force-reinstall pywin32

# COM 등록
python -m pywin32_postinstall -install
```

### 5단계: Config.json 설정

프로젝트 루트의 `Config.json` 파일을 편집:

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
      "USEYN": "N",
      "NAME": "MITSU_PLC_1",
      "IP": "192.168.2.210",
      "PORT": 3000,
      "TAGS": ["D100", "D101"]
    }
  }
}
```

---

## ▶️ 서버 실행

### 기본 실행

```bash
# 가상환경이 활성화된 상태에서
python server.py
```

예상 출력:
```
INFO:     Uvicorn running on http://0.0.0.0:5000 (Press CTRL+C to quit)
INFO:     ================================================================
INFO:     LAST UPDATED DATE: 2026-03-17
INFO:     PLC_TYPE: OPCUA
INFO:     PLC_NAME: OPCUA_PLC_1
INFO:     PLC_IP  : 127.0.0.1
INFO:     PLC_PORT: 49320
INFO:     ================================================================
```

### 포트 변경 (선택사항)

`server.py` 파일에서:

```python
if __name__ == '__main__':
  uvicorn.run('app.main:app', 
              host = '0.0.0.0', 
              port = 8000,  # ← 포트 변경
              use_colors = True, 
              log_config = None)
```

### 호스트 변경 (선택사항)

특정 IP에서만 리스닝:

```python
if __name__ == '__main__':
  uvicorn.run('app.main:app', 
              host = '192.168.1.100',  # ← 특정 IP
              port = 5000,
              use_colors = True, 
              log_config = None)
```

---

## 🧪 설치 검증

### 1. 서버 시작 확인

```bash
python server.py
```

포트 5000에서 정상 시작되는지 확인

### 2. 웹 접속

브라우저에서 `http://localhost:5000` 접속

시스템 상태 JSON 응답 확인:
```json
{
  "status": "OK",
  "msg": "The PLC_CON_Program is running now.",
  "data": null
}
```

### 3. 웹 대시보드 접속

`http://localhost:5000/web` 에서 대시보드 UI 확인

### 4. PLC 연결 테스트

```bash
# 목록 조회
curl http://localhost:5000/plc_list

# 읽기 테스트
curl "http://localhost:5000/plc_read?plc_name=OPCUA_PLC_1&tag=ns=2;s=Channel2.Device2.B0"
```

---

## 🐛 설치 문제 해결

### 문제: Python이 설치되지 않음

```bash
# Python 버전 확인
python --version

# 설치 안 되면 python.org에서 다운로드 후 재설치
```

### 문제: pip 모듈을 찾을 수 없음

```bash
# pip 업그레이드
python -m pip install --upgrade pip

# 또는 Python 재설치
```

### 문제: 의존성 설치 실패

```bash
# 캐시 삭제 후 재설치
pip install --no-cache-dir -r requirements.txt

# 또는 개별 설치
pip install fastapi==0.135.1
pip install uvicorn==0.42.0
```

### 문제: 포트 5000이 이미 사용 중

```bash
# Windows에서 포트 확인
netstat -ano | findstr :5000

# Linux/macOS
lsof -i :5000
```

프로세스 종료 후 재시작하거나 다른 포트 사용

### 문제: 가상환경 활성화 안 됨

```bash
# Windows PowerShell 권한 정책 확인
Get-ExecutionPolicy

# 권한 변경 필요시
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

---

## 📦 의존성 상세

### 필수 패키지

| 패키지 | 버전 | 용도 |
|--------|------|------|
| asyncua | 1.1.8 | OPC UA 통신 |
| fastapi | 0.135.1 | 웹 프레임워크 |
| uvicorn | 0.42.0 | ASGI 서버 |
| pymcprotocol | 0.3.0 | Mitsubishi 통신 |
| pywin32 | 308 | Windows COM (OPC DA) |
| loguru | 0.7.3 | 로깅 |
| humps | 0.2.2 | JSON 변수명 변환 |

### 선택 패키지 (PLC 드라이버별)

**Siemens S7 추가 설정:**
```bash
pip install snap7
```

**PostgreSQL 데이터베이스:**
```bash
pip install psycopg2-binary
```

---

## 🚀 다음 단계

설치 완료 후:

1. [CONFIG_GUIDE.md](CONFIG_GUIDE.md) - PLC 설정 방법
2. [API_GUIDE.md](API_GUIDE.md) - API 사용 방법
3. [ARCHITECTURE.md](ARCHITECTURE.md) - 시스템 구조 이해

---

## 💾 언인스톨

```bash
# 가상환경 비활성화
deactivate

# 가상환경 삭제
rm -rf venv  # Linux/macOS
rmdir /s venv  # Windows
```

---

## 📞 지원

문제 발생 시:
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) 확인
- 로그 파일 검토
- GitHub Issues 등록
