from fastapi import APIRouter

router = APIRouter()

@router.post("/validate_receipt", description="영수증을 검증하는 API(외부 API 사용)")
async def validate_receipt():
    return [{"api": "validate_receipt", "version": "v2"}]