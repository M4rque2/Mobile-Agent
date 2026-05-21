# Framework Improvement Notes

Implemented for this task:
- Added `com.teslamotors.tesla` to `packages.py` so `open 特斯拉` can resolve directly instead of relying on manual app opening.
- Added `--answer_output_path` to `run_qwen3_5_for_mobile.py`. When the model finishes with action `answer`, the runner extracts the JSON payload and writes it to local disk.
- Added `--trace_dir` to avoid invalid or awkward trace folder names when a task uses a long markdown prompt.

Recommended next improvements:
- Add a first-class `record_json` or `save_data` action so long extraction tasks can checkpoint station data during the run, not only at the final answer.
- Save per-step model outputs and parsed actions as trace JSONL alongside screenshots. This will make failures easier to replay and debug.
- Add optional Android UI hierarchy capture through `adb shell uiautomator dump` so station names, addresses, and availability text can be extracted more reliably than screenshot-only perception.
- Add duplicate-detection memory in the runner for collection tasks, or expose a small structured memory file to the agent.
- Add safety policies as code-level guards for sensitive actions such as payment, account changes, vehicle control, reservation, and charging start/stop.
