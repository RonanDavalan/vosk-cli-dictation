# src/ui.py

import queue
import time
import pyperclip

from config.config import config
from src.system_control import type_text, press_key, play_sound
from src.i18n import get_translation, set_ui_language
from src.text_processing import TextProcessor
from src.runtime_state import (
    runtime_state, STATE_DICTATING, STATE_LISTENING, STATE_SLEEPING,
)
from src.voice_commands import (
    normalize_tokens, phrase_tokens, find_phrase, is_doubled,
    strip_one_repetition, remove_phrase_and_after, mean_confidence,
)

def ui_thread(text_queue: queue.Queue, control_queue: queue.Queue, stop_event, processor: TextProcessor, display_partials_event, sleep_event, wake_event):
    recording = False
    full_text_log = ""
    xdotool_failed_once = False

    # Détection tokenisée de la phrase d'arrêt (chantier 7 volet E). Le réveil
    # (phrase de réveil en ÉCOUTE) est piloté par le thread de reconnaissance,
    # qui a accès aux résultats partiels et à la grammaire restreinte.
    stop_tokens = phrase_tokens(config.STOP_PHRASE)
    conf_threshold = config.data.get('recognition', {}).get('confidence_threshold', 0.85)

    def start_recording():
        nonlocal recording, full_text_log, xdotool_failed_once
        _ = get_translation()
        recording = True
        runtime_state.set_state(STATE_DICTATING)
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
        runtime_state.set_state(STATE_LISTENING)
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
        runtime_state.set_state(STATE_LISTENING)
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

    def toggle_sleep():
        nonlocal recording
        _ = get_translation()
        if sleep_event.is_set():
            sleep_event.clear()
            wake_event.set()
            runtime_state.set_state(STATE_LISTENING)
            print(f"\n{config.color_success}{_('Sleep mode disabled — listening resumed.')}{config.RESET}")
        else:
            if recording:
                stop_recording()
            sleep_event.set()
            wake_event.clear()
            runtime_state.set_state(STATE_SLEEPING)
            print(f"\n{config.color_warning}{_('Sleep mode enabled — the microphone is released.')}{config.RESET}")
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
                elif command == 'DICTATION_ON':
                    if not recording and not sleep_event.is_set(): start_recording()
                elif command == 'DICTATION_OFF':
                    if recording: stop_recording()
                elif command == 'FINALIZE_SESSION':
                    finalize_session()
                elif command == 'TOGGLE_SLEEP':
                    toggle_sleep()
                elif command == 'SLEEP_ON':
                    if not sleep_event.is_set(): toggle_sleep()
                elif command == 'SLEEP_OFF':
                    if sleep_event.is_set(): toggle_sleep()
                elif command.startswith('/'):
                    execute_manual_command(command)
            except queue.Empty: pass
            try:
                item = text_queue.get_nowait()
                raw_text, words = item if isinstance(item, tuple) else (item, [])
                if not recording:
                    # En ÉCOUTE, le réveil est traité par le thread de
                    # reconnaissance ; tout texte parvenant ici est ignoré.
                    continue

                tokens = normalize_tokens(raw_text)

                # Échappatoire littérale : phrase d'arrêt dite deux fois de
                # suite -> on la tape une fois, on ne finalise pas.
                if is_doubled(tokens, stop_tokens):
                    literal = strip_one_repetition(raw_text, stop_tokens)
                    if literal:
                        process_and_type(literal)
                    continue

                idx = find_phrase(tokens, stop_tokens)
                if idx != -1 and not runtime_state.in_debounce():
                    conf = mean_confidence(words, idx, len(stop_tokens))
                    if conf >= conf_threshold:
                        before = remove_phrase_and_after(raw_text, stop_tokens)
                        if before:
                            process_and_type(before)
                        finalize_session()
                        continue
                    # Confiance insuffisante : on laisse passer comme du texte.

                if raw_text:
                    process_and_type(raw_text)
            except queue.Empty:
                time.sleep(0.01)
                continue
    except KeyboardInterrupt: pass
    finally:
        if not stop_event.is_set(): stop_event.set()
        # UPDATE: Use theme colors from config
        msg = _("Stopping user interface...")
        print(f"\n{config.color_info}{msg}{config.RESET}")
