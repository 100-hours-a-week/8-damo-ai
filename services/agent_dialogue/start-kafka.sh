#!/bin/bash
set -e
export PYTHONUNBUFFERED=1

echo "Starting vLLM server: ${LOCAL_MODEL:-HugJerry99/SKT-AX-4.0-Light-AWQ}"
python3 -m vllm.entrypoints.openai.api_server \
  --model "${LOCAL_MODEL:-HugJerry99/SKT-AX-4.0-Light-AWQ}" \
  --host 0.0.0.0 --port 8000 \
  --quantization awq --dtype auto \
  --max-model-len "${VLLM_MAX_MODEL_LEN:-4096}" \
  --gpu-memory-utilization "${VLLM_GPU_MEMORY_UTIL:-0.85}" &

VLLM_PID=$!
echo "Waiting for vLLM..."
until curl -s http://localhost:8000/health > /dev/null 2>&1; do sleep 2; done
echo "vLLM ready!"

faststream run services.agent_dialogue.app.main:app &
FASTSTREAM_PID=$!

wait -n $VLLM_PID $FASTSTREAM_PID
echo "One process exited, shutting down..."
kill $VLLM_PID $FASTSTREAM_PID 2>/dev/null
wait
