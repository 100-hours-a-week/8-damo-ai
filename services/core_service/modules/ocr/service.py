from typing import Dict, Any
from google.cloud import vision
import json
import logging
from shared.utils.config import get_settings

logger = logging.getLogger("faststream") 

class GoogleVisionService:
    def __init__(self):
        # 환경 변수에서 인증 정보 직접 읽기
        settings = get_settings()
        credentials_json = settings.GOOGLE_CREDENTIALS_JSON
        credentials_info = json.loads(credentials_json)
        self.client = vision.ImageAnnotatorClient.from_service_account_info(credentials_info)
    
    async def check_client(self):
        return self.client

    async def extract_text(self, image_content: bytes) -> Dict[str, Any]:
        import time
        start_time = time.time()
        
        try:
            image = vision.Image(content=image_content)
            response = self.client.text_detection(image=image)
            
            texts = response.text_annotations
            full_text = texts[0].description if texts else ""
            
            end_time = time.time()
            process_time = round((end_time - start_time) * 1000, 2)  # ms 단위
            
            return {
                "provider": "google_vision",
                "success": True,
                "full_text": full_text,
                "process_time": process_time,
                "error": None
            }
            
        except Exception as e:
            end_time = time.time()
            process_time = round((end_time - start_time) * 1000, 2)
            
            return {
                "provider": "google_vision",
                "success": False,
                "full_text": "",
                "process_time": process_time,
                "error": str(e)
            }