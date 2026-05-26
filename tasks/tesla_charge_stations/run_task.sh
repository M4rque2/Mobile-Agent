#!/usr/bin/env bash
set -euo pipefail

TASK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${TASK_DIR}/../.." && pwd)"
PROMPT="$(cat "${TASK_DIR}/task_prompt.md")"

cd "${REPO_DIR}"

if [ -f .env.local ]; then
    set -a
    . ./.env.local
    set +a
fi

ADB_BIN="${ADB_PATH:-adb}"
"${ADB_BIN}" shell input keyevent KEYCODE_WAKEUP 

"${ADB_BIN}" shell monkey -p com.teslamotors.tesla -c android.intent.category.LAUNCHER 1 
sleep 3

python run_agent.py \
    --model-config "model_config.json" \
    --instruction "${PROMPT}" \
    --answer-output-path "${TASK_DIR}/tesla_charge_stations.json" \
    --trace-dir "${TASK_DIR}/traces/latest" \
    --max-steps 120 \
    --history-length 6
