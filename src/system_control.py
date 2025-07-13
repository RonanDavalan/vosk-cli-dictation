# src/system_control.py

import subprocess
import pyperclip
import time
import shutil

from config.config import config
from src.i18n import get_translation

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

def type_text(text: str) -> bool:
    """
    Simulates typing text by pasting from the clipboard.
    """
    _ = get_translation()
    if not text: return False

    window_id = get_active_window_id()
    if not window_id:
        # UPDATE: Use theme colors from config
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
        # UPDATE: Use theme colors from config
        print(f"\n{config.color_error}{_('An error occurred with xdotool paste method:')} {e}{config.RESET}")
        return False

def press_key(key_name: str, count: int = 1) -> bool:
    """Simulates pressing a key (e.g., 'BackSpace') using xdotool."""
    _ = get_translation()
    window_id = get_active_window_id()
    if not window_id:
        # UPDATE: Use theme colors from config
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
        # UPDATE: Use theme colors from config
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
