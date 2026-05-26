"""GUI-agent message construction and prompt definitions."""

import json
import os
import time
from datetime import datetime
from typing import Any

from PIL import Image

from agent_io import annotate_screenshot, execute_action, parse_turn_response, rescale_coordinates


SYSTEM_PROMPT = '''# Tools

You may call one or more functions to assist with the user query.

You are provided with function signatures within <tools></tools> XML tags:
<tools>
{"type": "function", "function": {"name_for_human": "mobile_use", "name": "mobile_use", "description": "Use a touchscreen to interact with a mobile device, and take screenshots.
* This is an interface to a mobile device with touchscreen. You can perform actions like clicking, typing, swiping, etc.
* Some applications may take time to start or process actions, so you may need to wait and take successive screenshots to see the results of your actions.
* The screen's resolution is 1000x1000.
* Make sure to click any buttons, links, icons, etc with the cursor tip in the center of the element. Don't click boxes on their edges unless asked.", "parameters": {"properties": {"action": {"description": "The action to perform. The available actions are:
* `key`: Perform a key event on the mobile device.
    - This supports adb's `keyevent` syntax.
    - Examples: \\"volume_up\\", \\"volume_down\\", \\"power\\", \\"camera\\", \\"clear\\".
* `click`: Click the point on the screen with coordinate (x, y).
* `long_press`: Press the point on the screen with coordinate (x, y) for specified seconds.
* `swipe`: Swipe from the starting point with coordinate (x, y) to the end point with coordinates2 (x2, y2).
* `type`: Input the specified text into the activated input box.
* `system_button`: Press the system button.
* `open`: Open an app on the device.
* `wait`: Wait specified seconds for the change to happen.
* `interact`: Resolve the blocking window by interacting with the user.", "enum": ["key", "click", "long_press", "swipe", "type", "system_button", "open", "wait", "interact"], "type": "string"}, "coordinate": {"description": "(x, y): The x (pixels from the left edge) and y (pixels from the top edge) coordinates to move the mouse to. Required only by `action=click`, `action=long_press`, and `action=swipe`.", "type": "array"}, "coordinate2": {"description": "(x, y): The x (pixels from the left edge) and y (pixels from the top edge) coordinates to move the mouse to. Required only by `action=swipe`.", "type": "array"}, "text": {"description": "Required only by `action=key`, `action=type`, `action=open`, and `action=interact`.", "type": "string"}, "time": {"description": "The seconds to wait. Required only by `action=long_press` and `action=wait`.", "type": "number"}, "button": {"description": "Back means returning to the previous interface, Home means returning to the desktop, Menu means opening the application background menu, and Enter means pressing the enter. Required only by `action=system_button`", "enum": ["Back", "Home", "Menu", "Enter"], "type": "string"}}, "required": ["action"], "type": "object"}, "args_format": "Format the arguments as a JSON object."}}
</tools>

# Required response protocol

Every response must be exactly one JSON object and nothing else.
Choose exactly one of these 3 modes:
1. `navigate`: the phone is still navigating toward the target page, so return the next mobile action.
2. `extract`: the current screenshot is already the target informational page, so return structured JSON data extracted from the current page and do not return a phone action.
3. `quit`: the mission is complete or the mission is stuck and cannot be overcome.

JSON schemas:

Navigate:
{
  "choice": "navigate",
  "summary": "short reason for the next action",
  "tool_call": {"name": "mobile_use", "arguments": { ...mobile action json... }}
}

Extract:
{
  "choice": "extract",
  "summary": "short reason why this is the target page",
  "data": { ...structured page json... }
}

Quit:
{
  "choice": "quit",
  "status": "success" | "failure",
    "summary": "short summary of the final task result",
  "data": { ...optional final json... }
}

Rules:
- Return valid JSON only. Do not use markdown fences.
- Never include a tool call unless `choice` is `navigate`.
- Never mix `extract` data with a tool call.
- Use `extract` only when the current screenshot already shows the target informational page whose data should be crawled now.
- Use `quit` when the mission is done or the UI is blocked/stuck in a way you cannot overcome safely.
- `quit.summary` must summarize the final task result.
- Keep `summary` brief.'''

def _try_parse_json(text):
    if not text:
        return None
    try:
        cleaned = text.strip()
        if "```json" in cleaned:
            cleaned = cleaned.split("```json", 1)[1].split("```", 1)[0].strip()
        elif "```" in cleaned:
            cleaned = cleaned.split("```", 1)[1].split("```", 1)[0].strip()
        return json.loads(cleaned)
    except Exception:
        return None

def _summarize_history_output(text):
    payload = _try_parse_json(text)
    if isinstance(payload, dict):
        choice = payload.get("choice")
        if choice == "navigate":
            return payload.get("summary") or json.dumps(payload.get("tool_call", {}), ensure_ascii=False)
        if choice == "extract":
            return payload.get("summary") or "Extracted target page data"
        if choice == "quit":
            status = payload.get("status", "unknown")
            summary = payload.get("summary") or "Quit"
            return f"Quit ({status}): {summary}"
    if "<tool_call>" in text:
        return text.split("<tool_call>")[0].strip()
    return text.strip()

def build_messages(
    image_path,
    instruction,
    history_output,
    model_name,
    history_n=4,
    reference_image_path=None,
    reference_text=None,
):
    """Construct multi-turn messages for the VLM."""
    current_step = len(history_output)
    history_start_idx = max(0, current_step - history_n)

    previous_actions = []
    for i in range(history_start_idx):
        if i < len(history_output):
            text = _summarize_history_output(history_output[i]["output"])
            previous_actions.append(f"Step {i + 1}: {text}")

    previous_actions_str = "\n".join(previous_actions) if previous_actions else "None"

    today = datetime.today()
    weekday_names = [
        "Monday", "Tuesday", "Wednesday", "Thursday",
        "Friday", "Saturday", "Sunday",
    ]
    formatted_date = today.strftime("%Y-%m-%d") + " " + weekday_names[today.weekday()]
    date_info = f"Today's date is: {formatted_date}."

    instruction_prompt = (
        f"Please generate the next move according to the UI screenshot, "
        f"instruction and previous actions.\n\n"
        f"Instruction: {date_info}{instruction}\n\n"
        f"Previous actions:\n{previous_actions_str}"
    )
    if reference_image_path:
        reference_prompt = reference_text or "Use the reference image to recognize the target UI region on the current screenshot."
        instruction_prompt = (
            f"{instruction_prompt}\n\n"
            f"Reference image guidance: {reference_prompt}\n"
            f"The first image is the reference image. The last image is the current screenshot."
        )

    messages = [
        {
            "role": "system",
            "content": [{"text": SYSTEM_PROMPT}],
        }
    ]

    history_len = min(history_n, len(history_output))
    if history_len > 0:
        for idx, item in enumerate(history_output[-history_n:]):
            if idx == 0:
                first_turn_content = [{"text": instruction_prompt}]
                if reference_image_path:
                    first_turn_content.append({"image": "file://" + reference_image_path})
                first_turn_content.append({"image": "file://" + item["image"]})
                messages.append({
                    "role": "user",
                    "content": first_turn_content,
                })
            else:
                messages.append({
                    "role": "user",
                    "content": [{"image": "file://" + item["image"]}],
                })
            messages.append({
                "role": "assistant",
                "content": [{"text": item["output"]}],
            })
        messages.append({
            "role": "user",
            "content": [{"image": "file://" + image_path}],
        })
    else:
        first_turn_content = [{"text": instruction_prompt}]
        if reference_image_path:
            first_turn_content.append({"image": "file://" + reference_image_path})
        first_turn_content.append({"image": "file://" + image_path})
        messages.append({
            "role": "user",
            "content": first_turn_content,
        })

    return messages


def prepare_device_for_task(adb_tools: Any) -> None:
    print("[PREFLIGHT] Checking device state...")
    initial_state = adb_tools.get_device_state()
    print(
        "[PREFLIGHT] Initial state: "
        f"screen_on={initial_state['screen_on']}, locked={initial_state['locked']}"
    )

    adb_tools.wake_if_needed()
    unlocked = adb_tools.unlock_if_needed(max_attempts=3)
    if not unlocked:
        print("[WARN] Device may still be locked after swipe attempts.")

    adb_tools.go_home_default_page()

    final_state = adb_tools.get_device_state()
    print(
        "[PREFLIGHT] Final state: "
        f"screen_on={final_state['screen_on']}, locked={final_state['locked']}"
    )


def run_agent_loop(
    *,
    max_steps: int,
    task_root: str,
    screenshot_dir: str,
    anno_dir: str,
    instruction: str,
    history_n: int,
    adb_tools: Any,
    vlm: Any,
) -> None:
    prepare_device_for_task(adb_tools)

    history = []

    for step_id in range(max_steps):
        print(f"\n{'=' * 50}\nSTEP {step_id}\n{'=' * 50}")
        screenshot_path = os.path.join(screenshot_dir, f"screenshot_{step_id}.png")
        if not adb_tools.get_screenshot(screenshot_path):
            print("[ERROR] Failed to capture screenshot. Retrying...")
            time.sleep(1)
            continue

        messages = build_messages(
            screenshot_path,
            instruction,
            history,
            vlm.model_name,
            history_n=history_n,
        )
        try:
            output_text, _, _ = vlm.invoke(messages)
        except Exception as exc:
            print(f"[ERROR] LLM invoke failed: {exc}")
            break
        print(f"[MODEL OUTPUT]\n{output_text}")

        try:
            turn = parse_turn_response(output_text)
        except Exception as exc:
            print(f"[ERROR] Failed to parse model response: {exc}")
            history.append({"output": output_text or "Malformed model response.", "image": screenshot_path})
            continue

        choice = turn["choice"]
        if choice == "extract":
            summary = turn.get("summary") or "Extracted target page data"
            print(f"[EXTRACT] {summary}")
            history.append({"output": json.dumps(turn, ensure_ascii=False), "image": screenshot_path})
            continue

        if choice == "quit":
            summary = turn.get("summary") or (
                "任务已完成" if turn.get("status") == "success" else "任务未完成，已退出"
            )
            status = turn["status"]
            print(f"[QUIT] {status}: {summary}")
            history.append({"output": json.dumps(turn, ensure_ascii=False), "image": screenshot_path})
            break

        action_parameter = turn["tool_call"]["arguments"]
        with Image.open(screenshot_path) as image:
            action_parameter = rescale_coordinates(action_parameter, image.width, image.height)
        print(f"[ACTION] {json.dumps(action_parameter, ensure_ascii=False)}")

        should_terminate = execute_action(
            action_parameter,
            instruction,
            adb_tools,
            vlm.api_key,
            vlm.endpoint_url,
            vlm.model_name,
            trace_logger=vlm.trace_logger,
        )
        if should_terminate:
            break

        history.append({"output": json.dumps(turn, ensure_ascii=False), "image": screenshot_path})
        annotate_screenshot(
            screenshot_path,
            action_parameter,
            os.path.join(anno_dir, f"screenshot_anno_{step_id}.png"),
        )
        time.sleep(2)
