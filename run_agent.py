"""
Mobile-Agent runner for a multimodal chat-completions endpoint.

Example:
    python run_agent.py --model-config model_config.json
"""

import argparse
import shutil
from pathlib import Path

from agent_io import AdbTools
from agent import run_agent_loop
from logs import make_task_log_dirs, enable_dual_logging
from llm_client import DEFAULT_MODEL_CONFIG_PATH, create_llm_client


def parse_args():
    parser = argparse.ArgumentParser(
        description="Mobile-Agent runner for a multimodal chat-completions endpoint."
    )
    parser.add_argument("--model-config", dest="model_config", type=str, default=DEFAULT_MODEL_CONFIG_PATH, help="Path to model config JSON.")
    parser.add_argument(
        "--instruction",
        type=str,
        default="",
        help="Task instruction for the agent.",
    )
    parser.add_argument(
        "--max-steps",
        dest="max_steps",
        type=int,
        default=80)
    parser.add_argument(
        "--history-length",
        dest="history_n",
        type=int,
        default=4,
        help="Number of previous screenshot turns to include.",
    )
    parser.add_argument(
        "--trace-dir",
        dest="trace_dir",
        type=str,
        default=None,
        help="Optional task root directory override.",
    )
    parser.add_argument(
        "--llm-trace-dir",
        dest="llm_trace_dir",
        type=str,
        default=None,
        help="Optional directory for LLM request/response trace logs.",
    )
    return parser.parse_args()

def run_agent():
    args = parse_args()
    log_dirs = make_task_log_dirs(args.trace_dir)
    log_file_path = enable_dual_logging(log_dirs["task_root"])
    print(f"[TASK ROOT] {log_dirs['task_root']}")
    print(f"[LOG FILE] {log_file_path}")

    llm_trace_dir = args.llm_trace_dir or log_dirs["llm_tracer_dir"]
    vlm = create_llm_client(
        config_path=args.model_config,
        llm_trace_dir=llm_trace_dir,
    )

    adb_path = vlm.adb_path or shutil.which("adb")
    if not adb_path:
        raise SystemExit("Missing adb path. Set 'adb_path' in model_config.json or make adb available in system PATH.")
    if vlm.adb_path and not Path(adb_path).exists():
        raise SystemExit(f"Configured adb_path does not exist: {adb_path}")

    adb_tools = AdbTools(adb_path=adb_path)

    run_agent_loop(
        max_steps=args.max_steps,
        task_root=log_dirs["task_root"],
        screenshot_dir=log_dirs["screenshot_dir"],
        anno_dir=log_dirs["screenshot_anno_dir"],
        instruction=args.instruction,
        history_n=args.history_n,
        adb_tools=adb_tools,
        vlm=vlm,
    )

    print("\n[DONE] Agent execution finished.")


if __name__ == "__main__":
    run_agent()
