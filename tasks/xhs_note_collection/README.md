# XHS Note Crawler Task

Goal: open the 小红书 app, browse the feed, enter 10 individual note detail pages, extract visible metadata from each, and save everything to a local JSON file.

Files:
- `task_prompt.md`: the instruction to pass to the mobile agent.
- `run_task.sh`: task-specific runner using the model endpoint from the repo's Qwen runner defaults.
- `xhs_notes.json`: expected output file created by the runner after the final `answer` action.

Run:

```bash
cd /path/to/Mobile-Agent
bash tasks/xhs_note_crawler/run_task.sh
```

If ADB is not at `adb`, edit `ADB_PATH` in `run_task.sh` or run with:

```bash
ADB_PATH=/path/to/adb bash tasks/xhs_note_crawler/run_task.sh
```

Notes:
- The app is mapped as `com.xingin.xhs` / `小红书` for direct launch.
- The scripts wake/unlock the device with repeated swipes until the lockscreen clears, then pre-launch `com.xingin.xhs` with ADB so the model starts inside 小红书 instead of searching the launcher.
- The runner writes the final `answer` payload to `tasks/xhs_note_crawler/xhs_notes.json`.
- The task intentionally forbids posting, commenting, liking, following, DM, payment, account-setting, and any other irreversible actions.