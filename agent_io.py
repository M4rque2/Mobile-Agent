"""Action parsing and execution for Mobile-Agent.

This module converts model text output into predefined actions and executes
those actions via ADB tools.
"""

import json
import math
import os
import re
import shutil
import subprocess
import tempfile
import time
import unicodedata
from typing import Any

from PIL import Image, ImageDraw

from app_name_to_package import resolve_package_ids


# ---------------------------------------------------------------------------
# ADB Tools
# ---------------------------------------------------------------------------


class AdbTools:
    """Wrapper around ADB commands for device interaction."""

    def __init__(self, device=None):
        resolved_adb_path = shutil.which("adb")
        if not resolved_adb_path:
            raise SystemExit("Missing adb executable in system PATH.")
        if not os.path.exists(resolved_adb_path):
            raise SystemExit(f"Resolved adb path does not exist: {resolved_adb_path}")

        self.adb_path = resolved_adb_path
        self.device = device
        self._device_flag = f" -s {device} " if device is not None else " "
        self.image_info = None

    def _run(self, args):
        """Run an ADB command string."""
        cmd = self.adb_path + self._device_flag + args
        return subprocess.run(cmd, capture_output=True, text=True, shell=True)

    def _run_args(self, args):
        """Run an ADB command with argv args to avoid shell quoting issues."""
        cmd = [self.adb_path]
        if self.device:
            cmd.extend(["-s", self.device])
        cmd.extend(args)
        return subprocess.run(cmd, capture_output=True, text=True, check=False)

    def _load_image_info(self, path):
        """Cache the width and height of the screenshot."""
        width, height = Image.open(path).size
        self.image_info = (width, height)

    def get_screenshot(self, image_path, retry_times=3):
        """Capture screenshot and save to image_path."""
        self._run("shell input keyevent KEYCODE_WAKEUP")
        time.sleep(0.3)

        cmd = [self.adb_path]
        if self.device:
            cmd.extend(["-s", self.device])
        cmd.extend(["exec-out", "screencap", "-p"])

        for _ in range(retry_times):
            res = subprocess.run(cmd, capture_output=True, check=False)
            if res.returncode == 0 and res.stdout:
                with open(image_path, "wb") as f:
                    f.write(res.stdout)
            if os.path.exists(image_path) and os.path.getsize(image_path) > 0:
                self._load_image_info(image_path)
                return True
            time.sleep(0.1)
        return False

    def dump_ui_hierarchy(
        self,
        output_path,
        retry_times=3,
        retry_delay_seconds=1,
        compressed=False,
    ):
        output_path = os.fspath(output_path)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        remote_name = f"window_dump_{int(time.time() * 1000)}.xml"
        remote_path = f"/sdcard/{remote_name}"
        dump_args = ["shell", "uiautomator", "dump"]
        if compressed:
            dump_args.append("--compressed")
        dump_args.append(remote_path)

        dump_succeeded = False
        for attempt in range(1, retry_times + 1):
            self._run_args(["shell", "input", "keyevent", "KEYCODE_WAKEUP"])
            time.sleep(0.3)
            dump_result = self._run_args(dump_args)
            dump_output = f"{dump_result.stdout}\n{dump_result.stderr}".strip()
            if dump_output:
                print(f"[UI XML] dump attempt {attempt}/{retry_times}: {dump_output}")
            ls_result = self._run_args(["shell", "ls", remote_path])
            remote_exists = ls_result.returncode == 0 and "No such file or directory" not in (
                f"{ls_result.stdout}\n{ls_result.stderr}"
            )
            if dump_result.returncode == 0 and remote_exists:
                dump_succeeded = True
                break
            if attempt < retry_times:
                time.sleep(retry_delay_seconds)

        if not dump_succeeded:
            print(f"[WARN] uiautomator dump failed after {retry_times} attempts: {remote_path}")
            return False

        temp_dir = tempfile.mkdtemp(prefix="ui_dump_")
        try:
            pull_result = self._run_args(["pull", remote_path, temp_dir])
            if pull_result.returncode != 0:
                print(f"[WARN] adb pull failed: {pull_result.stderr.strip()}")
                return False
            pulled_path = os.path.join(temp_dir, remote_name)
            if not os.path.exists(pulled_path):
                print(f"[WARN] Pulled XML file missing: {pulled_path}")
                return False
            shutil.move(pulled_path, output_path)
            return True
        finally:
            self._run_args(["shell", "rm", remote_path])
            shutil.rmtree(temp_dir, ignore_errors=True)

    def click(self, x, y):
        self._run(f"shell input tap {x} {y}")

    def long_press(self, x, y, duration=800):
        self._run(f"shell input swipe {x} {y} {x} {y} {duration}")

    def slide(self, x1, y1, x2, y2, slide_time=800):
        self._run(f"shell input swipe {x1} {y1} {x2} {y2} {slide_time}")

    def back(self):
        self._run("shell input keyevent 4")

    def home(self):
        self._run(
            "shell am start -a android.intent.action.MAIN "
            "-c android.intent.category.HOME"
        )

    def type(self, text):
        if self._type_with_adb_keyboard(text):
            return

        print("[WARN] ADB Keyboard input failed; falling back to clipboard paste.")
        if self._type_with_clipboard(text):
            return

        print("[WARN] Clipboard paste failed; falling back to adb shell input text.")
        safe_text = self._adb_input_text_safe(text)
        self._run_args(["shell", "input", "text", safe_text])

    def _adb_input_text_safe(self, text):
        ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
        if ascii_text:
            return ascii_text.replace(" ", "%s")
        return text.replace(" ", "%s")

    def _type_with_adb_keyboard(self, text):
        adb_ime = "com.android.adbkeyboard/.AdbIME"
        ime_list = self._run_args(["shell", "ime", "list", "-a"])
        if adb_ime not in ime_list.stdout:
            return False

        current_ime = self._run_args(["shell", "settings", "get", "secure", "default_input_method"]).stdout.strip()

        self._run_args(["shell", "ime", "enable", adb_ime])
        set_result = self._run_args(["shell", "ime", "set", adb_ime])
        if set_result.returncode != 0:
            print(f"[WARN] Failed to switch to ADB Keyboard: {set_result.stderr.strip()}")
            return False

        time.sleep(0.5)
        self._run_args(["shell", "am", "broadcast", "-a", "ADB_CLEAR_TEXT"])
        time.sleep(0.2)
        broadcast = self._run_args(
            ["shell", "am", "broadcast", "-a", "ADB_INPUT_TEXT", "--es", "msg", text]
        )
        time.sleep(0.8)

        if current_ime and current_ime != adb_ime:
            self._run_args(["shell", "ime", "set", current_ime])

        if broadcast.returncode != 0:
            print(f"[WARN] ADB Keyboard broadcast failed: {broadcast.stderr.strip()}")
            return False
        return True

    def _type_with_clipboard(self, text):
        set_clipboard = self._run_args(["shell", "cmd", "clipboard", "set", "text", text])
        clipboard_output = f"{set_clipboard.stdout}\n{set_clipboard.stderr}".strip()
        if set_clipboard.returncode != 0 or "No shell command implementation" in clipboard_output:
            print(f"[WARN] Clipboard set failed: {clipboard_output}")
            return False
        time.sleep(0.2)
        paste = self._run_args(["shell", "input", "keyevent", "KEYCODE_PASTE"])
        time.sleep(0.5)
        return paste.returncode == 0

    def get_package_name(self, all_packages=False):
        try:
            flag = "" if all_packages else " -3"
            cmd = f"{self.adb_path}{self._device_flag}shell pm list packages{flag}"
            res = subprocess.run(cmd, capture_output=True, text=True, shell=True)
            pkgs = []
            for line in res.stdout.splitlines():
                s = line.strip()
                if not s:
                    continue
                if s.startswith("package:"):
                    s = s[len("package:"):]
                if "=" in s:
                    _, s = s.split("=", 1)
                if s:
                    pkgs.append(s)
            return sorted(set(pkgs))
        except Exception as e:
            print(f"[ERROR] Failed to list packages: {e}")
            return []

    def open_app(self, package_name):
        self._run(
            f"shell monkey -p {package_name} "
            "-c android.intent.category.LAUNCHER 1"
        )

    def get_display_size(self) -> tuple[int, int]:
        result = self._run_args(["shell", "wm", "size"])
        output = f"{result.stdout}\n{result.stderr}"
        match = re.search(r"(?:Physical size|Override size):\s*(\d+)x(\d+)", output)
        if not match:
            return 1080, 2400
        return int(match.group(1)), int(match.group(2))

    def get_device_state(self) -> dict[str, bool]:
        power_result = self._run_args(["shell", "dumpsys", "power"])
        power_output = f"{power_result.stdout}\n{power_result.stderr}"
        power_output_lower = power_output.lower()

        window_result = self._run_args(["shell", "dumpsys", "window"])
        window_output = f"{window_result.stdout}\n{window_result.stderr}"
        window_output_lower = window_output.lower()

        policy_result = self._run_args(["shell", "dumpsys", "window", "policy"])
        policy_output = f"{policy_result.stdout}\n{policy_result.stderr}"
        policy_output_lower = policy_output.lower()

        screen_on = (
            "mwakefulness=awake" in power_output_lower
            or "display power: state=on" in power_output_lower
            or "display power state=on" in power_output_lower
        )

        lock_markers = [
            "mdreaminglockscreen=true",
            "isstatusbarkeyguard=true",
            "mshowinglockscreen=true",
            "mkeyguardshowing=true",
            "keyguardshowing=true",
        ]
        locked = any(marker in window_output_lower for marker in lock_markers) or any(
            marker in policy_output_lower for marker in lock_markers
        )

        return {
            "screen_on": screen_on,
            "locked": locked,
        }

    def wake_if_needed(self) -> None:
        state = self.get_device_state()
        if state["screen_on"]:
            return
        self._run_args(["shell", "input", "keyevent", "KEYCODE_WAKEUP"])
        time.sleep(0.6)

    def unlock_if_needed(self, max_attempts: int = 3) -> bool:
        width, height = self.get_display_size()
        x = width // 2
        start_y = int(height * 0.86)
        end_y = int(height * 0.25)

        for _ in range(max_attempts):
            state = self.get_device_state()
            if not state["locked"]:
                return True
            self._run_args(
                [
                    "shell",
                    "input",
                    "swipe",
                    str(x),
                    str(start_y),
                    str(x),
                    str(end_y),
                    "450",
                ]
            )
            time.sleep(0.8)

        return not self.get_device_state()["locked"]

    def go_home_default_page(self) -> None:
        self.home()
        time.sleep(0.4)
        self.home()
        time.sleep(0.6)


def annotate_screenshot(image_path, action_parameter, save_path="screenshot_anno.png"):
    image = Image.open(image_path)
    draw = ImageDraw.Draw(image)

    action_type = action_parameter.get("action", "")

    if action_type == "click":
        radius = 15
        cx, cy = action_parameter["coordinate"]
        draw.ellipse(
            (cx - radius, cy - radius, cx + radius, cy + radius),
            fill="red",
            outline="red",
        )
    elif action_type in ("scroll", "swipe"):
        x1, y1 = action_parameter["coordinate"]
        x2, y2 = action_parameter["coordinate2"]
        color = "red"
        arrow_size = 10

        draw.line((x1, y1, x2, y2), fill=color, width=2)

        angle = math.atan2(y2 - y1, x2 - x1)
        ax1 = x2 - arrow_size * math.cos(angle - math.pi / 6)
        ay1 = y2 - arrow_size * math.sin(angle - math.pi / 6)
        ax2 = x2 - arrow_size * math.cos(angle + math.pi / 6)
        ay2 = y2 - arrow_size * math.sin(angle + math.pi / 6)
        draw.polygon([(x2, y2), (ax1, ay1), (ax2, ay2)], fill=color)
    else:
        return None

    image.save(save_path)
    return save_path


def smart_resize(height, width, factor=16, min_pixels=None, max_pixels=None):
    IMAGE_MIN_TOKEN_NUM = 4
    IMAGE_MAX_TOKEN_NUM = 16384
    MAX_RATIO = 200

    max_pixels = max_pixels if max_pixels is not None else (IMAGE_MAX_TOKEN_NUM * factor ** 2)
    min_pixels = min_pixels if min_pixels is not None else (IMAGE_MIN_TOKEN_NUM * factor ** 2)
    assert max_pixels >= min_pixels, "max_pixels must be >= min_pixels."

    if max(height, width) / min(height, width) > MAX_RATIO:
        raise ValueError(
            f"Aspect ratio must be < {MAX_RATIO}, "
            f"got {max(height, width) / min(height, width)}"
        )

    def _round(n):
        return round(n / factor) * factor

    def _floor(n):
        return math.floor(n / factor) * factor

    def _ceil(n):
        return math.ceil(n / factor) * factor

    h_bar = max(factor, _round(height))
    w_bar = max(factor, _round(width))

    if h_bar * w_bar > max_pixels:
        beta = math.sqrt((height * width) / max_pixels)
        h_bar = _floor(height / beta)
        w_bar = _floor(width / beta)
    elif h_bar * w_bar < min_pixels:
        beta = math.sqrt(min_pixels / (height * width))
        h_bar = _ceil(height * beta)
        w_bar = _ceil(width * beta)

    return h_bar, w_bar


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
    """Best-effort extraction for structured model answers."""
    parsed = try_parse_json(text)
    if parsed is not None:
        return parsed

    if not text:
        return None

    starts = [idx for idx in (text.find("{"), text.find("[")) if idx != -1]
    if not starts:
        return None

    decoder = json.JSONDecoder()
    for start in sorted(starts):
        candidate = text[start:].strip()
        while candidate:
            try:
                parsed, _ = decoder.raw_decode(candidate)
                return parsed
            except Exception:
                candidate = candidate[:-1].rstrip()
    return None


def parse_action(tool_call: dict[str, Any]) -> dict[str, Any]:
    if tool_call.get("name") != "mobile_use":
        raise ValueError(f"Unexpected tool name: {tool_call}")
    if "arguments" not in tool_call:
        raise ValueError(f"tool_call has no arguments: {tool_call}")
    return tool_call


def parse_turn_response(output_text: str) -> dict[str, Any]:
    payload = extract_json_payload(output_text)
    if not isinstance(payload, dict):
        raise ValueError(f"No top-level JSON object found in model output: {output_text}")

    choice = payload.get("choice")
    if choice not in {"navigate", "extract", "quit"}:
        raise ValueError(f"Unsupported choice in model output: {payload}")

    if choice == "navigate":
        tool_call = payload.get("tool_call")
        if not isinstance(tool_call, dict):
            raise ValueError(f"Navigate choice missing tool_call: {payload}")
        payload["tool_call"] = parse_action(tool_call)
    elif choice == "extract":
        if not isinstance(payload.get("data"), dict):
            raise ValueError(f"Extract choice missing data object: {payload}")
    elif choice == "quit":
        if payload.get("status") not in {"success", "failure"}:
            raise ValueError(f"Quit choice missing valid status: {payload}")

    return payload


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
    action_parameter: dict[str, Any],
    adb_tools: AdbTools,
):
    app_name = action_parameter.get("text", "")
    package_candidates = resolve_package_ids(app_name)
    if not package_candidates:
        print(f"[WARN] No package mapping found for app: {app_name}")
        return False

    installed_packages = adb_tools.get_package_name()

    for pkg in package_candidates:
        if pkg in installed_packages:
            adb_tools.open_app(pkg)
            return True

    print(f"[WARN] App mapped but not installed on device: {app_name} -> {package_candidates}")
    return False


def execute_action(
    action_parameter: dict[str, Any],
    instruction: str,
    adb_tools: AdbTools,
    api_key: str,
    endpoint_url: str,
    model_name: str,
    trace_logger=None,
) -> bool:
    """Execute one action.

    Returns True when execution indicates the run should terminate.
    """
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
        status = action_parameter.get("status", "unknown")
        print(f"[TERMINATED] Status: {status}")
        return True
    elif action_type == "open":
        opened = handle_open_action(
            action_parameter,
            adb_tools,
        )
        if not opened:
            print("[WARN] Open action was not executed successfully.")
    else:
        print(f"[WARN] Unsupported action type: {action_type}")

    return False
