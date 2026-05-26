#!/usr/bin/env bash
set -euo pipefail

TASK_DIR="tasks/tesla_charge_stations"

INSTRUCTION="$(cat "$TASK_DIR/task_prompt.md")"

python run_agent.py \
    --model-config "model_config.json" \
    --instruction "$INSTRUCTION" \
    --answer-output-path "$TASK_DIR/tesla_charge_stations.json" \
    --trace-dir "$TASK_DIR/traces/latest" \
    --max-steps 120 \
    --history-length 6
