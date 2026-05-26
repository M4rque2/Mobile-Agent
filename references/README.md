# Agent Framework References

Third-party repositories are cloned under `references/agent-frameworks/` for local study only. That folder is ignored by Git so reference code, models, benchmark assets, and nested Git histories are not pushed with this repository.

## Initial Reference Set

| Repository | Local Folder | Shallow HEAD on 2026-05-21 | Purpose |
| --- | --- | --- | --- |
| X-PLUG/MobileAgent | `agent-frameworks/MobileAgent` | `0e5065e9e7ac` | Mobile-Agent family prompts, mobile action loop, ADB/device patterns, GUI-Owl integration. |
| MadeAgents/mobile-use | `agent-frameworks/mobile-use` | `1c01bef9ce3b` | Android GUI-agent architecture, reflection, task execution, AndroidWorld/AndroidLab integration. |
| OpenBMB/AgentCPM-GUI | `agent-frameworks/AgentCPM-GUI` | `2168ae21b1be` | Android screenshot-to-action modeling, compact action schema, Chinese-app operation patterns. |
| ZJU-REAL/ClawGUI | `agent-frameworks/ClawGUI` | `ab8a670527a8` | Broader GUI-agent build/evaluate/deploy framework with real-device Android support. |
| google-research/android_world | `agent-frameworks/android_world` | `d9c569f764b3` | AndroidWorld benchmark tasks, environment setup, evaluation interfaces, and reproducible mobile-task design. |

## Review Checklist

For each reference, inspect:

- action schema and grounding format;
- system/task prompts and recovery instructions;
- screenshot, accessibility, and UI-tree handling;
- ADB/device control abstractions;
- trace and replay artifacts;
- memory/checkpointing for extraction tasks;
- safety guards for account, payment, and irreversible actions;
- model adapter and inference transport design;
- task/evaluation harness shape.

Record lessons for this project in our own docs rather than copying code blindly.
