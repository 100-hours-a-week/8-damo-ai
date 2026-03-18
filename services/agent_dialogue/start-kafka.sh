#!/bin/bash
set -e
export PYTHONUNBUFFERED=1

VLLM_MODEL="${VLLM_MODEL:-HugJerry99/SKT-AX-4.0-Light-AWQ}"

# vLLM HTTP API 서버 — 내부 포트 8001 (외부 미노출)
echo "Starting vLLM server: $VLLM_MODEL"
python3 -m vllm.entrypoints.openai.api_server \
  --model "$VLLM_MODEL" \
  --host 127.0.0.1 --port 8001 \
  --quantization awq --dtype auto \
  --max-model-len "${VLLM_MAX_MODEL_LEN:-4096}" \
  --gpu-memory-utilization "${VLLM_GPU_MEMORY_UTIL:-0.85}" &

VLLM_PID=$!

# vLLM 준비 대기 (최대 5분)
echo "Waiting for vLLM (port 8001)..."
MAX_WAIT=300
ELAPSED=0
until curl -s http://127.0.0.1:8001/health > /dev/null 2>&1; do
  sleep 2
  ELAPSED=$((ELAPSED + 2))
  if [ "$ELAPSED" -ge "$MAX_WAIT" ]; then
    echo "ERROR: vLLM failed to start within ${MAX_WAIT}s"
    kill "$VLLM_PID" 2>/dev/null
    exit 1
  fi
done
echo "vLLM ready!"

# LiteLLM config 동적 생성 — 모델 이름이 env var에서 직접 치환되어 신뢰성 보장
LITELLM_CONFIG=/tmp/litellm_config.yaml
cat > "$LITELLM_CONFIG" << EOF
model_list:
  - model_name: local-model
    litellm_params:
      model: openai/$VLLM_MODEL
      api_base: http://127.0.0.1:8001/v1
      api_key: local

litellm_settings:
  request_timeout: 120
  drop_params: true
EOF

# LiteLLM 프록시 — 외부 포트 8000
# 모델 교체 시 VLLM_MODEL 환경변수만 변경하면 됨 (클라이언트 코드 변경 불필요)
echo "Starting LiteLLM proxy (port 8000) -> vLLM (port 8001, model=$VLLM_MODEL)"
litellm --config "$LITELLM_CONFIG" \
  --host 0.0.0.0 --port 8000 &

LITELLM_PID=$!

wait -n $VLLM_PID $LITELLM_PID
echo "One process exited, shutting down..."
kill $VLLM_PID $LITELLM_PID 2>/dev/null
wait
