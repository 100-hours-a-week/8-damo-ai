#!/bin/bash
set -e
export PYTHONUNBUFFERED=1

MODEL="${LOCAL_MODEL:-HugJerry99/SKT-AX-4.0-Light-AWQ}"
MODEL_CACHE_DIR="${HF_HOME:-/workspace}/hub/models--$(echo "$MODEL" | tr '/' '--')"

if [ -d "$MODEL_CACHE_DIR" ]; then
  echo "Model cache found at $MODEL_CACHE_DIR, skipping download"
else
  echo "Model cache not found, downloading $MODEL from HuggingFace..."
fi

echo "Starting vLLM server: $MODEL"
python3 -m vllm.entrypoints.openai.api_server \
  --model "$MODEL" \
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
