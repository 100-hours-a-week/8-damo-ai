from fastapi import FastAPI
import uvicorn
from src.router.router import api_router

app = FastAPI(title="Damo AI Pipeline API", version="0.0.1")


@app.get("/ai/api")
async def root():
    """루트 엔드포인트 - 간단한 환영 메시지"""
    return {"message": "Welcome to Damo AI Pipeline API", "status": "running"}


@app.get("/ai/api/health")
async def health_check():
    """헬스체크 엔드포인트"""
    return {"status": "ok", "message": "Server is healthy"}


app.include_router(router, prefix="/ai/api")


if __name__ == "__main__":
    # 개발용 서버 실행
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
