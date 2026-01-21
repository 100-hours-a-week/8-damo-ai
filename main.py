from fastapi import FastAPI
import uvicorn

app = FastAPI(title="Health Check API", version="1.0.0")


@app.get("/")
async def root():
    """루트 엔드포인트 - 간단한 환영 메시지"""
    return {
        "message": "Welcome to FastAPI Health Check Server",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """헬스체크 엔드포인트"""
    return {
        "status": "ok",
        "message": "Server is healthy"
    }


if __name__ == "__main__":
    # 개발용 서버 실행
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
