# src/ui.py

import queue
import pyperclip

from config.config import config
from src.system_control import type_text, press_key, play_sound
from src.i18n import get_translation, set_ui_language
from src.text_processing import TextProcessor

def ui_thread(text_queue: queue.Queue, control_queue: queue.Queue, stop_event, processor: TextProcessor, display_partials_event):
    recording = False
    full_text_log = ""
    xdotool_failed_once = False

    def start_recording():
        nonlocal recording, full_text_log, xdotool_failed_once
        _ = get_translation()
        recording = True
        display_partials_event.set()
        full_text_log = ""
        xdotool_failed_once = False
        processor.reset_state()
        # UPDATE: Use theme colors from config
        print(f"\n{config.color_success}{_('Recording started.')}{config.RESET}")
        play_sound()

    def stop_recording():
        nonlocal recording
        _ = get_translation()
        recording = False
        display_partials_event.clear()
        # UPDATE: Use theme colors from config
        print(f"\n{config.color_error}{_('Recording paused.')}{config.RESET}")
        play_sound()

    def finalize_session():
        nonlocal recording, full_text_log
        _ = get_translation()

        if not recording and not full_text_log.strip():
            return

        recording = False
        display_partials_event.clear()
        text_to_copy = full_text_log.strip()
        if text_to_copy:
            pyperclip.copy(text_to_copy)
        msg = _('Recording finished. Text copied.')
        # UPDATE: Use theme colors from config
        print(f"\n{config.color_error}{msg}{config.RESET}")
        full_text_log = ""
        processor.reset_state()
        play_sound()

    def execute_manual_command(command: str):
        nonlocal full_text_log, recording
        _ = get_translation()

        command = command.strip()
        if not command.startswith('/'): return
        cmd_parts = command[1:].split()
        if not cmd_parts: return
        cmd_name = cmd_parts[0].lower()

        # UPDATE: Use theme colors from config
        if cmd_name == 'cancel':
            if recording: stop_recording()
            full_text_log = ""
            processor.reset_state()
            print(f"{config.color_warning}{_('Session canceled.')}{config.RESET}")
        elif cmd_name == 'delete-word':
            if full_text_log.strip():
                log_parts = full_text_log.rstrip().split(' ')
                if log_parts:
                    word_to_remove = log_parts.pop()
                    full_text_log = ' '.join(log_parts) + (' ' if log_parts else '')
                    for _ in range(len(word_to_remove) + 1): press_key('BackSpace')
                    print(f"{config.color_warning}{_('Last word deleted (simulation).')}{config.RESET}")
            else:
                print(f"{config.color_warning}{_('No text to modify.')}{config.RESET}")
        elif cmd_name == 'nl':
            to_add = '\n\n' if config.current_lang == 'fr' else '\n'
            if recording:
                process_and_type(to_add)
                print(f"{config.color_warning}{_('New paragraph inserted.')}{config.RESET}")
            else:
                full_text_log += to_add
                processor.capitalize_next_word = True
                print(f"{config.color_warning}{_('New paragraph added to buffer.')}{config.RESET}")
        else:
            print(f"{config.color_error}{_('Unknown command:')} {command}{config.RESET}")

    def process_and_type(raw_text: str):
        nonlocal full_text_log, xdotool_failed_once
        _ = get_translation()

        processed_text = processor.process(raw_text)
        if not processed_text: return

        string_to_type = ""
        if full_text_log and not full_text_log.endswith((' ', '\n', '\u202f', '« ')):
            if not processed_text.startswith(('\u202f', ',', '.', ')', ']')):
                 string_to_type = " "
        string_to_type += processed_text

        # UPDATE: Use theme colors from config
        if not xdotool_failed_once and not type_text(string_to_type):
            xdotool_failed_once = True
            msg = _('Warning: xdotool failed. Switching to log-only mode.')
            print(f"\n{config.color_warning}{msg}{config.RESET}")

        full_text_log += string_to_type
        display_repr = repr(string_to_type.strip())
        if not xdotool_failed_once:
            msg = _('Typed:')
            print(f"\r{config.color_success}{msg} {display_repr}{config.RESET}{' ' * 20}")
        else:
            msg = _('[Degraded Mode] Added:')
            print(f"\r{config.color_success}{msg} {display_repr}{config.RESET}{' ' * 20}")

    try:
        while not stop_event.is_set():
            _ = get_translation()
            try:
                command = control_queue.get_nowait()
                if command == 'TOGGLE_RECORDING':
                    if recording: stop_recording()
                    else: start_recording()
                elif command == 'FINALIZE_SESSION':
                    finalize_session()
                elif command.startswith('/'):
                    execute_manual_command(command)
            except queue.Empty: pass
            try:
                raw_text = text_queue.get_nowait()
                raw_text_lower = raw_text.strip().lower()
                if config.STOP_WORD in raw_text_lower:
                    text_before_stop = raw_text.split(config.STOP_WORD, 1)[0].strip()
                    if text_before_stop and recording:
                        process_and_type(text_before_stop)
                    finalize_session()
                    continue
                if not recording:
                    if config.START_WORD in raw_text_lower:
                        start_recording()
                    continue
                if raw_text:
                    process_and_type(raw_text)
            except queue.Empty: continue
    except KeyboardInterrupt: pass
    finally:
        if not stop_event.is_set(): stop_event.set()
        # UPDATE: Use theme colors from config
        msg = _("Stopping user interface...")
        print(f"\n{config.color_info}{msg}{config.RESET}")
