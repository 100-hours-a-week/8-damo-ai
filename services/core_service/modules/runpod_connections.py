import httpx
import logging
import asyncio
from shared.utils.config import get_settings

logger = logging.getLogger("faststream")


class RunPodClient:
    def __init__(self):
        self.settings = get_settings()
        self.base_url = self.settings.RUNPOD_API_URL
        self.api_key = self.settings.RUNPOD_API_KEY
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        # 클라이언트를 세션처럼 유지합니다. (커넥션 풀 활용)
        self.client = httpx.AsyncClient(
            base_url=self.base_url, headers=self.headers, timeout=30.0
        )

    async def close(self):
        """클라이언트 세션을 종료합니다."""
        await self.client.aclose()

    async def health_check(self) -> bool:
        """RunPod 엔드포인트의 헬스체크를 수행합니다."""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # base_url이 설정되어 있으므로 상대 경로만 사용합니다.
                response = await self.client.get("/health")

                if response.status_code == 200:
                    logger.info(
                        f"✅ RunPod Health Check Success: {response.status_code}"
                    )
                    return True

                logger.warning(
                    f"⚠️ RunPod Health Check status {response.status_code}. Attempt {attempt + 1}/{max_retries}"
                )

            except httpx.RequestError as e:
                logger.error(
                    f"❌ RunPod Health Check attempt {attempt + 1} failed: {e}"
                )

            if attempt < max_retries - 1:
                await asyncio.sleep(1)

        logger.error("🚨 RunPod health check failed after all attempts")
        return False

    async def run_sync_task(self, payload: dict):
        """동기식 작업을 요청합니다 (RunPod /run)"""
        try:
            response = await self.client.post("/run", json={"input": payload})
            response.raise_for_status()
            result = response.json()
            logger.info(f"🚀 RunPod Task Submitted: {result.get('id')}")
            return result
        except httpx.HTTPStatusError as e:
            logger.error(
                f"❌ RunPod HTTP Error: {e.response.status_code} - {e.response.text}"
            )
            raise
        except Exception as e:
            logger.error(f"❌ RunPod Task Error: {e}")
            raise

    async def run_async_task(self, payload: dict):
        """비동기 작업 요청 (RunPod /run, job_id만 반환하고 결과를 기다리지 않음)"""
        try:
            response = await self.client.post("/run", json={"input": payload})
            response.raise_for_status()
            result = response.json()
            logger.info(f"RunPod Async Task Submitted: job_id={result.get('id')}")
            return result
        except httpx.HTTPStatusError as e:
            logger.error(
                f"RunPod HTTP Error: {e.response.status_code} - {e.response.text}"
            )
            raise
        except Exception as e:
            logger.error(f"RunPod Async Task Error: {e}")
            raise
