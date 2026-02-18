from fastapi import FastAPI

# 로깅 설정
app = FastAPI(
    title="Iterative Discussion Service",
    description="Iterative Discussion Service for Damo AI Features",
    version="0.1.0",
)


# 엔드포인트 설정
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "iterative_discussion_service"}
