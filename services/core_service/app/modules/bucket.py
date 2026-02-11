import boto3
import os
from dotenv import load_dotenv

load_dotenv()

class BucketManager:
    def __init__(self):
        # Railway Buckets의 환경 변수를 기반으로 세팅
        self.endpoint_url = os.getenv('AWS_ENDPOINT_URL')
        self.access_key = os.getenv('AWS_ACCESS_KEY_ID')
        self.secret_key = os.getenv('AWS_SECRET')
        self.region = os.getenv('AWS_REGION')
        self.bucket_name = os.getenv('AWS_BUCKET_NAME')

        self.s3 = boto3.client(
            's3',
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name=self.region
        )

    def list_objects(self, prefix='prompts/'):
        """특정 경로내의 파일 목록 조회"""
        try:
            response = self.s3.list_objects_v2(Bucket=self.bucket_name, Prefix=prefix)
            return response.get('Contents', [])
        except Exception as e:
            print(f"Error listing objects: {e}")
            return []

    def upload_file(self, local_path, target_key):
        """파일 업로드"""
        try:
            self.s3.upload_file(local_path, self.bucket_name, target_key)
            return True
        except Exception as e:
            print(f"Error uploading file: {e}")
            return False

    def download_file(self, target_key, local_path):
        """파일 다운로드"""
        try:
            self.s3.download_file(self.bucket_name, target_key, local_path)
            return True
        except Exception as e:
            print(f"Error downloading file: {e}")
            return False

    def get_object_body(self, key):
        """파일의 내용을 직접 읽어서 반환 (작은 마크다운 파일용)"""
        try:
            response = self.s3.get_object(Bucket=self.bucket_name, Key=key)
            return response['Body'].read().decode('utf-8')
        except Exception as e:
            print(f"Error reading object: {e}")
            return None

# 싱글톤 패턴으로 인스턴스 제공
bucket_manager = BucketManager()