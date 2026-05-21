#!/usr/bin/env bash
set -euo pipefail

TASK_DIR="tasks/tesla_charge_stations"

if [ -f .env.local ]; then
    set -a
    . ./.env.local
    set +a
fi

INSTRUCTION="$(cat "$TASK_DIR/task_prompt.md")"
ADB_BIN="${ADB_PATH:-adb}"

"$ADB_BIN" shell input keyevent KEYCODE_WAKEUP >/dev/null
for _ in 1 2 3; do
    "$ADB_BIN" shell input swipe 720 2600 720 600 500 >/dev/null
    sleep 1
    if ! "$ADB_BIN" shell dumpsys window | grep -q "mDreamingLockscreen=true"; then
        break
    fi
done
"$ADB_BIN" shell monkey -p com.teslamotors.tesla -c android.intent.category.LAUNCHER 1 >/dev/null
sleep 3

python run_qwen3_5_for_mobile.py \
    --adb_path "$ADB_BIN" \
    --url "${QWEN3_5_API_URL:?Set QWEN3_5_API_URL in .env.local or the environment}" \
    --api_key "${QWEN3_5_API_KEY:?Set QWEN3_5_API_KEY in .env.local or the environment}" \
    --model "${QWEN3_5_MODEL:?Set QWEN3_5_MODEL in .env.local or the environment}" \
    --instruction "$INSTRUCTION" \
    --answer_output_path "$TASK_DIR/tesla_charge_stations.json" \
    --trace_dir "$TASK_DIR/traces/latest" \
    --max_steps 120 \
    --history_n 6 \
    --transport curl \
    --no_stream
