# Tesla Charge Station Task

Goal: open the 特斯拉 app, navigate to the 充电 page, and save all reachable charging station information as local JSON.

Files:
- `task_prompt.md`: the instruction to pass to the mobile agent.
- `run_task.sh`: task-specific runner using the model endpoint from the repo's Qwen runner defaults.
- `tesla_charge_stations.json`: expected output file created by the runner after the final `answer` action.

Run:

```bash
cd /path/to/Mobile-Agent
bash tasks/tesla_charge_stations/run_task.sh
```

If ADB is not at `adb`, edit `ADB_PATH` in `run_task.sh` or run with:

```bash
ADB_PATH=/path/to/adb bash tasks/tesla_charge_stations/run_task.sh
```

Notes:
- The app is mapped as `com.teslamotors.tesla` / `特斯拉` for direct launch.
- The scripts wake/unlock the device with repeated swipes until the lockscreen clears, then pre-launch `com.teslamotors.tesla` with ADB so the model starts inside Tesla instead of searching the launcher.
- The runner writes the final `answer` payload to `tasks/tesla_charge_stations/tesla_charge_stations.json`.
- The task intentionally forbids charging, payment, reservation, account, and vehicle-setting actions.
