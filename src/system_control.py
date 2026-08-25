# src/system_control.py

import subprocess
import pyperclip
import time
import shutil

from config.config import config
from src.i18n import get_translation

KEYCODE = {'ctrl': 29, 'v': 47, 'BackSpace': 14}

_YDOTOOL_OK = None

def check_command_exists(command: str) -> bool:
    """Checks if an external command is available in the system's PATH."""
    return shutil.which(command) is not None

def get_active_window_id():
    """Retrieves the ID of the currently active window using xdotool."""
    try:
        result = subprocess.run(
            ['xdotool', 'getactivewindow'],
            check=True,
            capture_output=True,
            text=True
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None

def _ydotool_disponible() -> bool:
    """Checks if ydotool is available and working, caching the result."""
    global _YDOTOOL_OK
    if _YDOTOOL_OK is not None:
        return _YDOTOOL_OK
    if not check_command_exists("ydotool"):
        _YDOTOOL_OK = False
        return False
    try:
        subprocess.run(['ydotool', 'key', '0:0'], check=True, capture_output=True, text=True)
        _YDOTOOL_OK = True
    except (subprocess.CalledProcessError, FileNotFoundError):
        _YDOTOOL_OK = False
    return _YDOTOOL_OK

def ydotool_disponible() -> bool:
    """Returns whether ydotool is available, computing it on first call."""
    return _ydotool_disponible()

def _type_text_ydotool(text: str) -> bool:
    """Simulates typing text via ydotool by pasting from the clipboard."""
    _ = get_translation()
    try:
        original_clipboard = pyperclip.paste()
        pyperclip.copy(text)
        time.sleep(0.1)
        ctrl = str(KEYCODE['ctrl'])
        v = str(KEYCODE['v'])
        subprocess.run(['ydotool', 'key', f'{ctrl}:1', f'{v}:1', f'{v}:0', f'{ctrl}:0'], check=True)
        time.sleep(0.1)
        pyperclip.copy(original_clipboard)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"\n{config.color_error}{_('An error occurred with ydotool paste method:')} {e}{config.RESET}")
        return False

def _press_key_ydotool(key_name: str, count: int = 1) -> bool:
    """Simulates pressing a key via ydotool."""
    _ = get_translation()
    if key_name not in KEYCODE:
        raise ValueError(f"Key '{key_name}' is not supported by ydotool")
    code = str(KEYCODE[key_name])
    events = []
    for _i in range(count):
        events.append(f'{code}:1')
        events.append(f'{code}:0')
    try:
        subprocess.run(['ydotool', 'key'] + events, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"\n{config.color_error}{_('An error occurred with ydotool key press:')} {e}{config.RESET}")
        return False

def type_text(text: str) -> bool:
    """Simulates typing text by pasting from the clipboard."""
    if not text: return False
    if ydotool_disponible():
        return _type_text_ydotool(text)

    _ = get_translation()
    window_id = get_active_window_id()
    if not window_id:
        print(f"\n{config.color_error}{_('Error: Could not find an active window to type into.')}{config.RESET}")
        return False

    try:
        original_clipboard = pyperclip.paste()
        pyperclip.copy(text)
        time.sleep(0.1)
        subprocess.run(['xdotool', 'key', '--window', window_id, 'ctrl+v'], check=True)
        time.sleep(0.1)
        pyperclip.copy(original_clipboard)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"\n{config.color_error}{_('An error occurred with xdotool paste method:')} {e}{config.RESET}")
        return False

def press_key(key_name: str, count: int = 1) -> bool:
    """Simulates pressing a key (e.g., 'BackSpace') using xdotool."""
    if ydotool_disponible():
        return _press_key_ydotool(key_name, count)

    _ = get_translation()
    window_id = get_active_window_id()
    if not window_id:
        print(f"\n{config.color_error}{_('Error: Could not find an active window to press a key.')}{config.RESET}")
        return False

    try:
        command = ['xdotool', 'key', '--window', window_id]
        if count > 1:
            command.extend(['--repeat', str(count), '--delay', '0'])
        command.append(key_name)
        subprocess.run(command, check=True, stderr=subprocess.DEVNULL)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"\n{config.color_error}{_('An error occurred with xdotool key press:')} {e}{config.RESET}")
        return False

def play_sound():
    """Plays a system notification sound using paplay if available."""
    if not check_command_exists("paplay") or not config.sound_file:
        return

    try:
        subprocess.run(
            ["paplay", config.sound_file],
            check=True, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
