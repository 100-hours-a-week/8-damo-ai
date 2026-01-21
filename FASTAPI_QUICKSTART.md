# FastAPI 헬스체크 서버 - 빠른 시작 가이드

AWS EC2에서 FastAPI 헬스체크 서버를 실행하기 위한 최소 구성입니다.

## 📁 파일 구성

- `main.py` - FastAPI 애플리케이션 (루트 및 헬스체크 엔드포인트)
- `requirements.txt` - 필요한 패키지 목록

## 🚀 설치 및 실행

### 1. 의존성 설치

```bash
pip install -r requirements.txt
```

### 2. 서버 실행

#### 개발 모드 (포그라운드)
```bash
python main.py
```

또는

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

#### 프로덕션 모드 (백그라운드)
```bash
nohup uvicorn main:app --host 0.0.0.0 --port 8000 > server.log 2>&1 &
```

백그라운드 프로세스 확인:
```bash
ps aux | grep uvicorn
```

백그라운드 프로세스 종료:
```bash
pkill -f uvicorn
```

## 🧪 테스트

### 로컬에서 테스트
```bash
# 루트 엔드포인트
curl http://localhost:8000/

# 헬스체크 엔드포인트
curl http://localhost:8000/health
```

### 외부에서 테스트 (EC2 퍼블릭 IP 사용)
```bash
# 루트 엔드포인트
curl http://<EC2_PUBLIC_IP>:8000/

# 헬스체크 엔드포인트
curl http://<EC2_PUBLIC_IP>:8000/health
```

### Swagger UI 접속
브라우저에서 다음 URL로 접속하여 API 문서 확인:
```
http://<EC2_PUBLIC_IP>:8000/docs
```

## 🔧 AWS EC2 보안 그룹 설정

외부에서 접속하려면 EC2 보안 그룹에서 8000 포트를 열어야 합니다:

1. EC2 콘솔 → 인스턴스 선택
2. 보안 그룹 클릭
3. 인바운드 규칙 편집
4. 규칙 추가:
   - 유형: 사용자 지정 TCP
   - 포트 범위: 8000
   - 소스: 0.0.0.0/0 (모든 IP) 또는 특정 IP

## 📊 로그 확인

백그라운드 실행 시 로그 확인:
```bash
tail -f server.log
```

## 🛑 서버 중지

```bash
# uvicorn 프로세스 찾기
ps aux | grep uvicorn

# 프로세스 종료
kill <PID>

# 또는 한번에
pkill -f uvicorn
```

## 📝 엔드포인트

- `GET /` - 루트 엔드포인트 (환영 메시지)
- `GET /health` - 헬스체크 엔드포인트
- `GET /docs` - Swagger UI (자동 생성)
- `GET /redoc` - ReDoc (자동 생성)
