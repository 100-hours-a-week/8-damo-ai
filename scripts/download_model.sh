#!/bin/bash
# RunPod Network Volume 첫 세팅 시 모델을 사전 다운로드하는 스크립트
# 사용법: bash scripts/download_model.sh
# RunPod 템플릿에서 /workspace에 Network Volume을 마운트한 상태로 실행

set -e

MODEL="${LOCAL_MODEL:-HugJerry99/SKT-AX-4.0-Light-AWQ}"
HF_HOME="${HF_HOME:-/workspace}"

echo "Downloading model: $MODEL"
echo "Cache directory: $HF_HOME"

HF_HOME="$HF_HOME" python3 - <<EOF
from huggingface_hub import snapshot_download
import os

model = "$MODEL"
print(f"Downloading {model}...")
path = snapshot_download(repo_id=model)
print(f"Download complete: {path}")
EOF

echo "Done. Model cached at $HF_HOME/hub/"
