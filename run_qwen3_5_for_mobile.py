"""
Mobile-Agent-v3.5 runner for the Qwen3.5-397B-A17B multimodal endpoint.

This is a sibling of run_gui_owl_1_5_for_mobile.py for environments where
GUI-Owl-1.5 is unavailable but Qwen3.5-397B-A17B can process images through an
OpenAI-compatible chat-completions endpoint.

By default, the script reads the URL, model name, and bearer token from the
repo-level test_script.py without executing it. CLI args or environment
variables override those defaults.

Example:
    cd mobile_use
    python run_qwen3_5_for_mobile.py --adb_path /path/to/adb

Sample default task:
    Open 小红书, browse the feed, save/favorite 10 posts, then terminate.
"""

import argparse
import ast
import base64
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from io import BytesIO
from pathlib import Path
from typing import Any

import requests
from PIL import Image

from packages import PACKAGES_NAME_DICT, NAME_PACKAGE_DICT, normalize_package_name
from utils import (
    AdbTools,
    annotate_screenshot,
    build_messages,
    smart_resize,
)


DEFAULT_URL = (
    "https://lpai-llm.lixiang.com/inference/qwen/"
    "qwen3.5-397b-a17b/v1/chat/completions"
)
DEFAULT_MODEL = "Qwen__Qwen3_5-397B-A17B"
DEFAULT_INSTRUCTION = (
    "Open 小红书 app, browse the home feed, save or favorite 10 interesting "
    "posts, and stop after 10 posts are saved."
)
ERROR_CALLING_LLM = "Error calling Qwen3.5 endpoint"


def load_test_script_defaults() -> dict[str, str]:
    """Read endpoint defaults from ../test_script.py without importing it."""
    defaults: dict[str, str] = {}
    test_script = Path(__file__).resolve().parents[1] / "test_script.py"
    if not test_script.exists():
        return defaults

    try:
        tree = ast.parse(test_script.read_text(encoding="utf-8"))
    except Exception:
        return defaults

    values: dict[str, Any] = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Name):
            continue
        if target.id not in {"url", "payload", "headers"}:
            continue
        try:
            values[target.id] = ast.literal_eval(node.value)
        except Exception:
            continue

    if isinstance(values.get("url"), str):
        defaults["url"] = values["url"]
    if isinstance(values.get("payload"), dict):
        model = values["payload"].get("model")
        if isinstance(model, str):
            defaults["model"] = model
    if isinstance(values.get("headers"), dict):
        authorization = values["headers"].get("Authorization")
        if isinstance(authorization, str) and authorization.startswith("Bearer "):
            defaults["api_key"] = authorization.removeprefix("Bearer ").strip()
    return defaults


def parse_args():
    test_defaults = load_test_script_defaults()
    parser = argparse.ArgumentParser(
        description="Mobile-Agent-v3.5 with Qwen3.5 multimodal inference."
    )
    parser.add_argument("--adb_path", type=str, required=True, help="Path to adb.")
    parser.add_argument("--device", type=str, default=None, help="ADB device serial.")
    parser.add_argument(
        "--url",
        type=str,
        default=(
            os.getenv("QWEN3_5_API_URL")
            or os.getenv("QWEN_API_URL")
            or test_defaults.get("url")
            or DEFAULT_URL
        ),
        help="Full chat-completions endpoint URL.",
    )
    parser.add_argument(
        "--api_key",
        type=str,
        default=(
            os.getenv("QWEN3_5_API_KEY")
            or os.getenv("QWEN_API_KEY")
            or test_defaults.get("api_key")
        ),
        help="Bearer token for the endpoint.",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=(
            os.getenv("QWEN3_5_MODEL")
            or os.getenv("QWEN_MODEL")
            or test_defaults.get("model")
            or DEFAULT_MODEL
        ),
        help="Model name for the endpoint.",
    )
    parser.add_argument(
        "--instruction",
        type=str,
        default=DEFAULT_INSTRUCTION,
        help="Task instruction for the agent.",
    )
    parser.add_argument(
        "--add_info",
        type=str,
        default="",
        help="Supplementary knowledge appended to the instruction.",
    )
    parser.add_argument("--max_steps", type=int, default=80)
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--top_p", type=float, default=0.7)
    parser.add_argument("--max_tokens", type=int, default=1024)
    parser.add_argument("--frequency_penalty", type=float, default=0)
    parser.add_argument("--presence_penalty", type=float, default=0)
    parser.add_argument(
        "--no_stream",
        action="store_true",
        help="Disable streaming. test_script.py uses streaming by default.",
    )
    parser.add_argument(
        "--transport",
        choices=("requests", "curl"),
        default=os.getenv("QWEN3_5_TRANSPORT", "curl"),
        help="HTTP transport for model calls. Use curl when Python TLS fails.",
    )
    parser.add_argument(
        "--history_n",
        type=int,
        default=4,
        help="Number of previous screenshot turns to include.",
    )
    parser.add_argument(
        "--app_resolver_api_key",
        type=str,
        default=None,
        help="Optional app resolver API key; defaults to --api_key.",
    )
    parser.add_argument(
        "--app_resolver_url",
        type=str,
        default=None,
        help="Optional full app resolver chat-completions URL; defaults to --url.",
    )
    parser.add_argument(
        "--app_resolver_model",
        type=str,
        default=None,
        help="Optional app resolver model; defaults to --model.",
    )
    parser.add_argument(
        "--answer_output_path",
        type=str,
        default=None,
        help="Optional local JSON path for the final answer action payload.",
    )
    parser.add_argument(
        "--trace_dir",
        type=str,
        default=None,
        help="Optional directory for screenshots and trace artifacts.",
    )
    return parser.parse_args()


def pil_to_base64_png(image: Image.Image) -> str:
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def image_to_data_url(image_path: str) -> str:
    if image_path.startswith("file://"):
        image_path = image_path[len("file://"):]
    image = Image.open(image_path)
    resized_height, resized_width = smart_resize(
        image.height,
        image.width,
        factor=28,
        min_pixels=3136,
        max_pixels=1003520,
    )
    image = image.resize((resized_width, resized_height))
    return f"data:image/png;base64,{pil_to_base64_png(image)}"


def convert_messages_to_openai_image_url(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert Mobile-Agent message parts to OpenAI-compatible multimodal parts."""
    converted = []
    for message in messages:
        content = []
        for item in message["content"]:
            if "text" in item:
                content.append({"type": "text", "text": item["text"]})
            elif "image" in item:
                content.append(
                    {
                        "type": "image_url",
                        "image_url": {"url": image_to_data_url(item["image"])},
                    }
                )
        converted.append({"role": message["role"], "content": content})
    return converted


def parse_streaming_response(response: requests.Response) -> str:
    chunks = []
    for raw_line in response.iter_lines(decode_unicode=True):
        if not raw_line:
            continue
        line = raw_line.strip()
        if line.startswith("data:"):
            line = line[len("data:"):].strip()
        if line == "[DONE]":
            break
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        choice = event.get("choices", [{}])[0]
        delta = choice.get("delta") or {}
        message = choice.get("message") or {}
        if delta.get("content"):
            chunks.append(delta["content"])
        if message.get("content"):
            chunks.append(message["content"])
    return "".join(chunks)


class Qwen35MultimodalWrapper:
    def __init__(
        self,
        url: str,
        api_key: str,
        model: str,
        temperature: float = 0.2,
        top_p: float = 0.7,
        max_tokens: int = 1024,
        frequency_penalty: float = 0,
        presence_penalty: float = 0,
        stream: bool = True,
        transport: str = "curl",
        max_retry: int = 3,
    ):
        self.url = url
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.top_p = top_p
        self.max_tokens = max_tokens
        self.frequency_penalty = frequency_penalty
        self.presence_penalty = presence_penalty
        self.stream = stream
        self.transport = transport
        self.max_retry = max_retry

    def predict_mm(self, messages: list[dict[str, Any]]) -> tuple[str, Any, Any]:
        payload_messages = convert_messages_to_openai_image_url(messages)
        payload = {
            "model": self.model,
            "messages": payload_messages,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "frequency_penalty": self.frequency_penalty,
            "presence_penalty": self.presence_penalty,
            "max_tokens": self.max_tokens,
            "stream": self.stream,
        }
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        if self.transport == "curl":
            for attempt in range(1, self.max_retry + 1):
                curl_result = self._predict_mm_with_curl(payload, headers)
                if curl_result is not None:
                    return curl_result[0], payload_messages, curl_result[1]
                if attempt < self.max_retry:
                    time.sleep(wait_seconds)
            return ERROR_CALLING_LLM, payload_messages, None

        wait_seconds = 5
        for attempt in range(1, self.max_retry + 1):
            try:
                response = requests.post(
                    self.url,
                    json=payload,
                    headers=headers,
                    stream=self.stream,
                    timeout=300,
                )
                response.raise_for_status()
                if self.stream:
                    return parse_streaming_response(response), payload_messages, response
                body = response.json()
                message = body["choices"][0]["message"]
                content = message.get("content")
                if content is None:
                    tool_calls = message.get("tool_calls") or []
                    if tool_calls:
                        content = "\n".join(json.dumps(call, ensure_ascii=False) for call in tool_calls)
                    else:
                        content = message.get("reasoning") or ""
                return content, payload_messages, body
            except Exception as exc:
                print(f"[WARN] Qwen3.5 call failed on attempt {attempt}: {exc}")
                curl_result = self._predict_mm_with_curl(payload, headers)
                if curl_result is not None:
                    return curl_result[0], payload_messages, curl_result[1]
                if attempt < self.max_retry:
                    time.sleep(wait_seconds)
        return ERROR_CALLING_LLM, payload_messages, None

    def _predict_mm_with_curl(
        self,
        payload: dict[str, Any],
        headers: dict[str, str],
    ) -> tuple[str, Any] | None:
        """Fallback for environments where Python SSL fails but curl succeeds."""
        curl_payload = dict(payload)
        curl_payload["stream"] = False

        temp_path = None
        try:
            with tempfile.NamedTemporaryFile("w", delete=False, suffix=".json", encoding="utf-8") as temp_file:
                json.dump(curl_payload, temp_file, ensure_ascii=False)
                temp_path = temp_file.name

            curl_binary = "curl.exe" if os.name == "nt" else "curl"
            result = subprocess.run(
                [
                    curl_binary,
                    "-sS",
                    "-X",
                    "POST",
                    self.url,
                    "-H",
                    "accept: application/json",
                    "-H",
                    "content-type: application/json",
                    "-H",
                    f"Authorization: {headers['Authorization']}",
                    "--data-binary",
                    f"@{temp_path}",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=300,
                check=False,
            )
            if result.returncode != 0:
                print(f"[WARN] curl fallback failed: {result.stderr.strip()}")
                return None

            try:
                body = json.loads(result.stdout, strict=False)
            except json.JSONDecodeError as exc:
                snippet = result.stdout[:500].replace(self.api_key, "<redacted>")
                print(f"[WARN] curl fallback returned non-JSON response: {exc}; body starts: {snippet}")
                content = self._extract_content_from_malformed_response(result.stdout)
                if content is not None:
                    print("[INFO] Used curl fallback with malformed-response content extraction.")
                    return content, {"raw_response": result.stdout}
                return None
            if "error" in body:
                print(f"[WARN] curl fallback returned error: {body['error']}")
                return None

            message = body["choices"][0]["message"]
            content = message.get("content")
            if content is None:
                tool_calls = message.get("tool_calls") or []
                if tool_calls:
                    content = "\n".join(json.dumps(call, ensure_ascii=False) for call in tool_calls)
                else:
                    content = message.get("reasoning") or ""
            print("[INFO] Used curl fallback for Qwen3.5 call.")
            return content, body
        except Exception as exc:
            print(f"[WARN] curl fallback failed: {exc}")
            return None
        finally:
            if temp_path and os.path.exists(temp_path):
                os.unlink(temp_path)

    @staticmethod
    def _extract_content_from_malformed_response(response_text: str) -> str | None:
        marker = '"content":"'
        start = response_text.find(marker)
        if start == -1:
            return None
        start += len(marker)
        end = response_text.find('","refusal"', start)
        if end == -1:
            return None
        raw_content = response_text[start:end]
        try:
            return json.loads(f'"{raw_content}"', strict=False)
        except Exception:
            return raw_content.replace('\\"', '"').replace("\\n", "\n")


def parse_action(output_text: str) -> dict[str, Any]:
    match = re.search(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", output_text, re.S)
    if not match:
        raise ValueError(f"No <tool_call> JSON found in model output: {output_text}")
    tool_call = json.loads(match.group(1))
    if "arguments" not in tool_call:
        raise ValueError(f"tool_call has no arguments: {tool_call}")
    return tool_call


def rescale_coordinates(action_parameter: dict[str, Any], width: int, height: int):
    if action_parameter.get("action") == "left_click":
        action_parameter["action"] = "click"
    for key in ("coordinate", "coordinate1", "coordinate2"):
        if key in action_parameter:
            x = max(0, min(1000, int(action_parameter[key][0])))
            y = max(0, min(1000, int(action_parameter[key][1])))
            action_parameter[key][0] = int(x / 1000 * width)
            action_parameter[key][1] = int(y / 1000 * height)
    return action_parameter


def handle_open_action(
    action_parameter,
    instruction,
    adb_tools,
    resolver_api_key,
    resolver_url,
    resolver_model,
):
    app_name = action_parameter.get("text", "")
    package_candidates = NAME_PACKAGE_DICT.get(normalize_package_name(app_name), [])
    installed_packages = adb_tools.get_package_name()
    display_name = app_name

    for pkg in package_candidates:
        if pkg in installed_packages:
            adb_tools.open_app(pkg)
            return True

    installed_app_names = []
    for pkg in installed_packages:
        if pkg in PACKAGES_NAME_DICT:
            installed_app_names.append(PACKAGES_NAME_DICT[pkg][0])

    resolved_name = resolve_app_name_with_full_url(
        instruction,
        ", ".join(installed_app_names),
        api_key=resolver_api_key,
        url=resolver_url,
        model=resolver_model,
    )
    if resolved_name:
        display_name = resolved_name

    for pkg in NAME_PACKAGE_DICT.get(normalize_package_name(resolved_name), []):
        if pkg in installed_packages:
            adb_tools.open_app(pkg)
            return True

    input(f"[ACTION REQUIRED] Please install or open the app manually: {display_name}")
    return False


def resolve_app_name_with_full_url(
    instruction: str,
    app_name_list_str: str,
    api_key: str,
    url: str,
    model: str,
) -> str:
    """Resolver equivalent for full chat-completions URLs from test_script.py."""
    prompt = f"""Given a task and installed app names, choose the app to open.

Task: {instruction}
Installed apps: {app_name_list_str}

Return only JSON:
{{"reason":"brief reason","app":"installed app name or empty string"}}"""
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You resolve Android app names."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0,
        "top_p": 0.7,
        "max_tokens": 256,
        "stream": False,
    }
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=120)
        response.raise_for_status()
        text = response.json()["choices"][0]["message"]["content"]
        parsed = try_parse_json(text)
        if parsed and "app" in parsed:
            return parsed["app"]
    except Exception as exc:
        print(f"[WARN] App resolver failed: {exc}")
    return ""


def try_parse_json(text: str):
    if not text:
        return None
    cleaned = text.strip()
    if "```json" in cleaned:
        cleaned = cleaned.split("```json", 1)[1].split("```", 1)[0].strip()
    elif "```" in cleaned:
        cleaned = cleaned.split("```", 1)[1].split("```", 1)[0].strip()
    try:
        return json.loads(cleaned)
    except Exception:
        return None


def extract_json_payload(text: str):
    """Best-effort extraction for final structured answers."""
    parsed = try_parse_json(text)
    if parsed is not None:
        return parsed

    if not text:
        return None

    starts = [idx for idx in (text.find("{"), text.find("[")) if idx != -1]
    if not starts:
        return None

    decoder = json.JSONDecoder()
    try:
        parsed, _ = decoder.raw_decode(text[min(starts):])
        return parsed
    except Exception:
        return None


def write_answer_output(answer_text: str, output_path: str | None):
    """Persist a final answer as JSON, preserving raw text on parse failure."""
    if not output_path:
        return

    payload = extract_json_payload(answer_text)
    if payload is None:
        payload = {"raw_answer": answer_text}

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[ANSWER SAVED] {path}")


def make_trace_dirs(instruction: str, trace_dir: str | None) -> tuple[str, str]:
    if trace_dir:
        task_dir = trace_dir
    else:
        task_dir = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "_", instruction.replace(" ", "_"))
        task_dir = task_dir.strip(" ._")[:80] or "mobile_agent_task"

    anno_dir = f"{task_dir}_anno"
    for directory in (task_dir, anno_dir):
        if os.path.exists(directory):
            shutil.rmtree(directory)
        os.makedirs(directory)
    return task_dir, anno_dir


def execute_action(
    action_parameter: dict[str, Any],
    output_text: str,
    instruction: str,
    adb_tools: AdbTools,
    resolver_api_key: str,
    resolver_url: str,
    resolver_model: str,
    answer_output_path: str | None = None,
) -> bool:
    action_type = action_parameter["action"]

    if action_type == "click":
        adb_tools.click(*action_parameter["coordinate"])
    elif action_type == "long_press":
        duration = int(float(action_parameter.get("time", 1)) * 1000)
        adb_tools.long_press(*action_parameter["coordinate"], duration=duration)
    elif action_type == "type":
        adb_tools.type(action_parameter["text"])
        if action_parameter["text"]:
            time.sleep(0.5)
            adb_tools._run("shell input keyevent 66")
    elif action_type in ("scroll", "swipe"):
        adb_tools.slide(
            action_parameter["coordinate"][0],
            action_parameter["coordinate"][1],
            action_parameter["coordinate2"][0],
            action_parameter["coordinate2"][1],
        )
    elif action_type == "system_button":
        button = action_parameter["button"]
        if button == "Back":
            adb_tools.back()
        elif button == "Home":
            adb_tools.home()
        elif button == "Enter":
            adb_tools._run("shell input keyevent 66")
        elif button == "Menu":
            adb_tools._run("shell input keyevent KEYCODE_APP_SWITCH")
    elif action_type == "key":
        adb_tools._run(f"shell input keyevent {action_parameter['text']}")
    elif action_type == "wait":
        time.sleep(float(action_parameter.get("time", 2)))
    elif action_type == "terminate":
        print(f"[TERMINATED] Status: {action_parameter.get('status', 'unknown')}")
        return True
    elif action_type == "open":
        opened = handle_open_action(
            action_parameter,
            instruction,
            adb_tools,
            resolver_api_key,
            resolver_url,
            resolver_model,
        )
        if not opened:
            return False
    elif action_type == "answer":
        conclusion = action_parameter.get("text") or output_text.split("<tool_call>")[0].strip()
        print(f"[ANSWER] {conclusion}")
        write_answer_output(conclusion, answer_output_path)
        return True
    elif action_type in ("call_user", "calluser", "interact"):
        user_prompt = action_parameter.get("text", "the required action")
        input(f"[ACTION REQUIRED] Please complete: {user_prompt}")
        print("[INFO] User action completed. Resuming...")
    else:
        print(f"[WARN] Unsupported action type: {action_type}")
    return False


def main():
    args = parse_args()
    if not args.api_key:
        raise SystemExit(
            "Missing API key. Pass --api_key, set QWEN3_5_API_KEY/QWEN_API_KEY, "
            "or keep a bearer token in repo-level test_script.py."
        )

    adb_tools = AdbTools(adb_path=args.adb_path, device=args.device)
    instruction = args.instruction
    if args.add_info:
        instruction = f"{instruction} ({args.add_info})"

    task_dir, anno_dir = make_trace_dirs(instruction, args.trace_dir)

    resolver_api_key = args.app_resolver_api_key or args.api_key
    resolver_url = args.app_resolver_url or args.url
    resolver_model = args.app_resolver_model or args.model
    history = []

    vllm = Qwen35MultimodalWrapper(
        url=args.url,
        api_key=args.api_key,
        model=args.model,
        temperature=args.temperature,
        top_p=args.top_p,
        max_tokens=args.max_tokens,
        frequency_penalty=args.frequency_penalty,
        presence_penalty=args.presence_penalty,
        stream=not args.no_stream,
        transport=args.transport,
    )

    for step_id in range(args.max_steps):
        print(f"\n{'=' * 50}\nSTEP {step_id}\n{'=' * 50}")
        screenshot_path = os.path.join(task_dir, f"screenshot_{step_id}.png")
        if not adb_tools.get_screenshot(screenshot_path):
            print("[ERROR] Failed to capture screenshot. Retrying...")
            time.sleep(1)
            continue

        messages = build_messages(
            screenshot_path,
            instruction,
            history,
            args.model,
            history_n=args.history_n,
        )
        output_text, _, _ = vllm.predict_mm(messages)
        print(f"[MODEL OUTPUT]\n{output_text}")
        if output_text == ERROR_CALLING_LLM:
            break

        try:
            action = parse_action(output_text)
            action_parameter = action["arguments"]
        except Exception as exc:
            print(f"[ERROR] Failed to parse action: {exc}")
            history.append({"output": output_text or "No parseable model output.", "image": screenshot_path})
            continue

        image = Image.open(screenshot_path)
        action_parameter = rescale_coordinates(action_parameter, image.width, image.height)
        print(f"[ACTION] {json.dumps(action_parameter, ensure_ascii=False)}")

        done = execute_action(
            action_parameter,
            output_text,
            instruction,
            adb_tools,
            resolver_api_key,
            resolver_url,
            resolver_model,
            args.answer_output_path,
        )

        history.append({"output": output_text, "image": screenshot_path})
        annotate_screenshot(
            screenshot_path,
            action_parameter,
            os.path.join(anno_dir, f"screenshot_anno_{step_id}.png"),
        )
        if done:
            break
        time.sleep(2)

    print("\n[DONE] Agent execution finished.")


if __name__ == "__main__":
    main()
