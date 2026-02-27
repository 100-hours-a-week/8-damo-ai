FROM python:3.12-slim

# 작업 디렉토리 설정
WORKDIR /app

# 파이썬 종속성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONPATH=/app

CMD ["python", "gateway/main.py"]
