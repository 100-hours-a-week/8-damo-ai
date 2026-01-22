from fastapi import APIRouter

router = APIRouter()

@router.post("/analyze_refresh", description="사용자가 재추천을 원할 경우 호출하는 API")
async def analyze_refresh():
    return [{"api": "analyze_refresh", "version": "v2"}]

@router.post("/make_persona", description="사용자 데이터로 Persona를 생성하는 API(회원가입시, 리뷰 작성시 호출)")
async def make_persona():
    return [{"api": "make_persona", "version": "v2"}]

@router.post("/recommendations", description="추천시 호출하는 API(외부 API 사용)")
async def recommendations():
    return [{"api": "recommendations", "version": "v2"}]