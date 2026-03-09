#!/bin/bash
set -e

export PYTHONUNBUFFERED=1
export HF_HOME=/workspace

KAFKA_HOME=/opt/kafka

# 1. Kafka 시작 (KRaft mode)
echo "Starting Kafka (KRaft mode)..."
$KAFKA_HOME/bin/kafka-server-start.sh -daemon $KAFKA_HOME/config/kraft/server.properties

echo "Waiting for Kafka to be ready..."
until $KAFKA_HOME/bin/kafka-broker-api-versions.sh --bootstrap-server localhost:9092 > /dev/null 2>&1; do
  sleep 2
done
echo "Kafka is ready!"

# 2. vLLM 서버 백그라운드 실행
echo "Starting vLLM server with model: ${LOCAL_MODEL:-skt/A.X-4.0-Light}"
python -m vllm.entrypoints.openai.api_server \
  --model "${LOCAL_MODEL:-skt/A.X-4.0-Light}" \
  --host 0.0.0.0 \
  --port 8000 \
  --max-model-len "${VLLM_MAX_MODEL_LEN:-4096}" \
  --gpu-memory-utilization "${VLLM_GPU_MEMORY_UTIL:-0.85}" &

VLLM_PID=$!

echo "Waiting for vLLM server to be ready..."
until curl -s http://localhost:8000/health > /dev/null 2>&1; do
  sleep 2
done
echo "vLLM server is ready!"

# 3. FastStream 실행
echo "Starting faststream consumer..."
faststream run services.agent_dialogue.app.main:app &
FASTSTREAM_PID=$!

# 어느 하나라도 종료되면 전체 종료
wait -n $VLLM_PID $FASTSTREAM_PID
echo "One process exited, shutting down..."
kill $VLLM_PID $FASTSTREAM_PID 2>/dev/null
$KAFKA_HOME/bin/kafka-server-stop.sh 2>/dev/null
wait
