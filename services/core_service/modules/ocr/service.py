import asyncio
import base64
import json
import logging
import time
from typing import Any, Dict

import aiohttp
from google.cloud import vision

from shared.utils.config import get_settings

logger = logging.getLogger("faststream")


class GoogleVisionService:
    def __init__(self):
        settings = get_settings()
        credentials_json = settings.GOOGLE_CREDENTIALS_JSON
        credentials_info = json.loads(credentials_json)
        self.client = vision.ImageAnnotatorClient.from_service_account_info(credentials_info)

    async def check_client(self):
        return self.client

    async def extract_text(self, image_content: bytes) -> Dict[str, Any]:
        start_time = time.time()
        try:
            loop = asyncio.get_event_loop()
            image = vision.Image(content=image_content)
            response = await loop.run_in_executor(
                None, lambda: self.client.text_detection(image=image)
            )
            texts = response.text_annotations
            full_text = texts[0].description if texts else ""
            process_time = round((time.time() - start_time) * 1000, 2)
            return {
                "provider": "google_vision",
                "success": True,
                "full_text": full_text,
                "process_time": process_time,
                "error": None,
            }
        except Exception as e:
            process_time = round((time.time() - start_time) * 1000, 2)
            return {
                "provider": "google_vision",
                "success": False,
                "full_text": "",
                "process_time": process_time,
                "error": str(e),
            }

    async def extract_text_from_url(self, url: str) -> Dict[str, Any]:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                image_content = await resp.read()
        return await self.extract_text(image_content)

    async def extract_text_from_base64(self, b64: str) -> Dict[str, Any]:
        image_content = base64.b64decode(b64)
        return await self.extract_text(image_content)
