# src/main.py

import sys
import os
import threading
import queue
import atexit
import argparse
import select

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from config.config import config
from src.i18n import set_ui_language, get_translation
from src.system_control import check_command_exists
from src.audio_capture import initialize_audio, audio_capture_thread
from src.recognition import load_model, recognition_thread
from src.ui import ui_thread
from src.keyboard_listener import keyboard_listener_thread
from src.text_processing import TextProcessor

def print_status(message, color):
    """Print status message with color."""
    print(f"{color}{message}")

def print_help_message():
    """
    Print a structured and logically grouped help message.
    """
    _ = get_translation()
    separator = f"{config.color_help_text}------------------------------------------------------------------{config.RESET}"
    title_style = f"{config.BRIGHT}{config.color_help_title}"

    print(separator)

    start_word = config.START_WORD
    stop_word = config.STOP_WORD
    toggle_hotkey = config.hotkeys['toggle_recording']['display_name']
    finalize_hotkey = config.hotkeys['finalize_session']['display_name']

    print_status(_("  - Say '{start_word}' or press {hotkey} to start/stop.").format(start_word=start_word, hotkey=toggle_hotkey), config.color_help_text)
    print_status(_("  - Say '{stop_word}' or press {hotkey} to stop and copy.").format(stop_word=stop_word, hotkey=finalize_hotkey), config.color_help_text)

    print_status(_("\n{style}  Manual commands:{reset}").format(style=title_style, reset=config.RESET), config.color_help_text)
    print_status(_("  - '/cancel', '/delete-word', '/nl'"), config.color_help_text)

    lang_settings = config.language_settings.get(config.current_lang, {})
    punctuation_sections = lang_settings.get('punctuation', {})
    if punctuation_sections:
        print_status(_("\n{style}  Punctuation commands:{reset}").format(style=title_style, reset=config.RESET), config.color_help_text)

        all_punctuation_cmds = {}
        for section in punctuation_sections.values():
            all_punctuation_cmds.update(section)

        # AFFICHE DYNAMIQUEMENT TOUTES les commandes de ponctuation de la config, triées
        # par ordre alphabétique et sur deux colonnes pour la lisibilité.
        display_commands = sorted(all_punctuation_cmds.keys())
        col_width = 35
        for i in range(0, len(display_commands), 2):
            line_str = "  "
            # Colonne 1
            cmd1 = display_commands[i]
            symbol1 = all_punctuation_cmds[cmd1]
            display_entry1 = f"{cmd1} ({repr(symbol1).strip('/')})"
            line_str += display_entry1.ljust(col_width)

            # Colonne 2 (si elle existe)
            if i + 1 < len(display_commands):
                cmd2 = display_commands[i + 1]
                symbol2 = all_punctuation_cmds[cmd2]
                display_entry2 = f"{cmd2} ({repr(symbol2).strip('/')})"
                line_str += display_entry2

            print_status(line_str, config.color_help_text)

    print(separator)
    print_status(_("Press Ctrl+C to exit the program."), config.color_help_text)


def exit_cleanup():
    """Clean exit function"""
    _ = get_translation()
    try:
        msg = _("\nProgram stopped cleanly.")
        print_status(msg, config.color_info)
    except (TypeError, NameError):
        print_status("\nProgram stopped cleanly.", config.color_info)

def main():
    """Main function"""
    set_ui_language(config.default_model)
    _ = get_translation()

    parser = argparse.ArgumentParser(description=_("A Vosk-based command-line dictation tool."))
    parser.add_argument('-l', '--lang', type=str, default=None, help=_("Force the interface and model language."))
    args = parser.parse_args()

    ui_lang = args.lang if args.lang else config.default_model

    if ui_lang != config.current_lang:
        set_ui_language(lang=ui_lang)
        _ = get_translation()

    config.set_language(ui_lang)
    atexit.register(exit_cleanup)

    print_status(_("Checking external dependencies..."), config.color_info)
    if not check_command_exists("xdotool"):
        print_status(_("'xdotool' is a critical dependency and is not installed."), config.color_error)
        print_status(_("Please install it (e.g., 'sudo apt-get install xdotool')."), config.color_error)
        return
    if not check_command_exists("paplay"):
        print_status(_("'paplay' not found. Sound notifications will be disabled."), config.color_warning)
    print_status(_("Dependencies checked."), config.color_info)

    print_status(_("Attempting to load model for language: {lang}").format(lang=ui_lang), config.color_info)
    recognizer, loaded_model_name = load_model(ui_lang)

    if not recognizer:
        default_model_name = config.default_model_name
        if ui_lang != default_model_name:
            print_status(_("Failed. Attempting to load default model: {model_name}").format(model_name=default_model_name), config.color_info)
            recognizer, loaded_model_name = load_model(default_model_name)

    if not recognizer:
        print_status(_("FATAL: No speech recognition model could be loaded."), config.color_error)
        print_status(_("Please check the model paths and integrity in your config.yaml file."), config.color_error)
        return

    lang_of_loaded_model = config.get_lang_from_model_name(loaded_model_name)
    if lang_of_loaded_model and lang_of_loaded_model != config.current_lang:
        config.set_language(lang_of_loaded_model)
        set_ui_language(lang_of_loaded_model)
        _ = get_translation()

    p, stream = initialize_audio()
    if not p or not stream: return

    audio_queue = queue.Queue()
    text_queue = queue.Queue()
    control_queue = queue.Queue()
    stop_event = threading.Event()
    display_partials_event = threading.Event()

    processor = TextProcessor(config.current_lang)

    threads = [
        threading.Thread(target=recognition_thread, args=(recognizer, audio_queue, text_queue, stop_event, display_partials_event)),
        threading.Thread(target=audio_capture_thread, args=(stream, audio_queue, stop_event)),
        threading.Thread(target=keyboard_listener_thread, args=(control_queue, stop_event)),
        threading.Thread(target=ui_thread, args=(text_queue, control_queue, stop_event, processor, display_partials_event))
    ]

    for t in threads:
        if t is not threading.current_thread():
            t.daemon = True

    ready_message = _("The script is ready. Current model: {model_name}").format(model_name=loaded_model_name.upper())
    print_status(ready_message, config.color_ready_message)
    print_help_message()

    try:
        for t in threads: t.start()

        while not stop_event.is_set():
            if sys.stdin.isatty() and select.select([sys.stdin], [], [], 0.1)[0]:
                line = sys.stdin.readline().strip()
                if line.startswith('/'):
                    control_queue.put(line)
            else:
                stop_event.wait(0.1)

    except KeyboardInterrupt:
        print_status(_("\nStop request received. Shutting down..."), config.color_info)
    finally:
        if not stop_event.is_set():
            stop_event.set()

        if stream and stream.is_active():
            stream.stop_stream()
            stream.close()

        if p:
            p.terminate()

if __name__ == "__main__":
    main()
