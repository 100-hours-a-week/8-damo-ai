import httpx
from shared.logging.logger import get_correlation_id, setup_logger

logger = setup_logger("shared.utils")

class ServiceClient:
    def __init__(self, base_url: str, timeout: float = 180.0):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout

    async def _request(self, method: str, path: str, **kwargs):
        url = f"{self.base_url}/{path.lstrip('/')}"
        headers = kwargs.pop("headers", {})
        headers["X-Request-ID"] = get_correlation_id()
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.request(method, url, headers=headers, **kwargs)
                response.raise_for_status()
                return response.json()
            except Exception as e:
                logger.error(f"Error calling {url}: {str(e)}")
                raise

    async def get(self, path: str, **kwargs):
        return await self._request("GET", path, **kwargs)

    async def post(self, path: str, **kwargs):
        return await self._request("POST", path, **kwargs)
