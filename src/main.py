# src/main.py

import sys
import os
import threading
import queue
import atexit
import argparse
import select
import signal
import vosk

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from config.config import config
from src.i18n import set_ui_language, get_translation
from src.system_control import check_command_exists, injection_backend_available
from src.audio_capture import initialize_audio, audio_capture_thread
from src.recognition import load_model, recognition_thread
from src.ui import ui_thread
from src.keyboard_listener import keyboard_listener_thread
from src.text_processing import TextProcessor
from src.control_socket import (
    start_control_server, send_control_command, instance_running, socket_path,
)

# Sous-commandes de contrôle (chantier 7 volet A) : drapeau -> jeton socket.
CONTROL_FLAGS = [
    ("toggle", "toggle"), ("dictation_on", "dictation-on"),
    ("dictation_off", "dictation-off"), ("finalize", "finalize"),
    ("cancel", "cancel"), ("sleep", "sleep"), ("wake", "wake"),
    ("sleep_toggle", "sleep-toggle"), ("status", "status"), ("stop", "quit"),
]

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

    wake_phrase = config.WAKE_PHRASE
    stop_phrase = config.STOP_PHRASE
    toggle_hotkey = config.hotkeys['toggle_recording']['display_name']
    finalize_hotkey = config.hotkeys['finalize_session']['display_name']

    print_status(_("  - Say '{wake_phrase}' or press {hotkey} to start/stop.").format(wake_phrase=wake_phrase, hotkey=toggle_hotkey), config.color_help_text)
    print_status(_("  - Say '{stop_phrase}', press {hotkey}, or run 'vosk-cli-dictation --finalize' to stop and copy.").format(stop_phrase=stop_phrase, hotkey=finalize_hotkey), config.color_help_text)
    print_status(_("  - Hotkeys are X11-only and reach the focused window; use --finalize."), config.color_help_text)

    print_status(_("\n{style}  Manual commands:{reset}").format(style=title_style, reset=config.RESET), config.color_help_text)
    print_status(_("  - '/cancel', '/delete-word', '/nl'"), config.color_help_text)

    lang_settings = config.language_settings.get(config.current_lang, {})
    punctuation_sections = lang_settings.get('punctuation', {})
    if punctuation_sections:
        print_status(_("\n{style}  Punctuation commands:{reset}").format(style=title_style, reset=config.RESET), config.color_help_text)

        all_punctuation_cmds = {}
        for section in punctuation_sections.values():
            # `mode` / `trigger` are scalars, not command maps (T1).
            if isinstance(section, dict):
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
    # R5 (28/08 soir) : coupe les LOG (VoskAPI...) au boot — le bruit de Vosk
    # s'affichait après « Appuyez sur Ctrl+C pour quitter » (démarrage des
    # threads après l'aide). --diagnose n'a pas besoin de ces logs.
    vosk.SetLogLevel(-1)
    set_ui_language(config.default_model)
    _ = get_translation()

    parser = argparse.ArgumentParser(description=_("A Vosk-based command-line dictation tool."))
    parser.add_argument('-l', '--lang', type=str, default=None, help=_("Force the interface and model language."))
    ctl = parser.add_argument_group(_("control an already running session"))
    ctl.add_argument('--toggle', action='store_true', help=_("toggle dictation on/off"))
    ctl.add_argument('--dictation-on', action='store_true', help=_("start dictation"))
    ctl.add_argument('--dictation-off', action='store_true', help=_("stop dictation, keep listening"))
    ctl.add_argument('--finalize', action='store_true', help=_("finalize the session and copy the text"))
    ctl.add_argument('--cancel', action='store_true', help=_("discard the current session buffer"))
    ctl.add_argument('--sleep', action='store_true', help=_("enter deep sleep (release the microphone)"))
    ctl.add_argument('--wake', action='store_true', help=_("leave deep sleep"))
    ctl.add_argument('--sleep-toggle', action='store_true', help=_("toggle deep sleep"))
    ctl.add_argument('--status', action='store_true', help=_("print the current state"))
    ctl.add_argument('--stop', action='store_true', help=_("stop the running session"))
    ctl.add_argument('--diagnose', action='store_true', help=_("check the environment and exit"))
    args = parser.parse_args()

    if args.diagnose:
        from src.diagnose import run_diagnose
        sys.exit(run_diagnose())

    for attr, wire in CONTROL_FLAGS:
        if getattr(args, attr, False):
            reply = send_control_command(wire)
            if reply is None:
                print_status(_("No running vosk-cli-dictation session."), config.color_error)
                sys.exit(1)
            print(reply)
            sys.exit(0 if reply.startswith("OK") else 2)

    ui_lang = args.lang if args.lang else config.default_model

    if ui_lang != config.current_lang:
        set_ui_language(lang=ui_lang)
        _ = get_translation()

    config.set_language(ui_lang)
    atexit.register(exit_cleanup)

    # Instance unique (chantier 7 volet A). Une socket qui répond -> une session
    # tourne déjà. Une socket qui refuse la connexion est un résidu : on
    # continue, start_control_server la remplacera.
    if config.data.get('control_socket', True) and instance_running():
        print_status(_("A vosk-cli-dictation session is already running (see --status)."), config.color_error)
        return

    print_status(_("Checking external dependencies..."), config.color_info)
    if not injection_backend_available():
        print_status(_("No text-injection backend available for this session."), config.color_error)
        print_status(_("Install 'wtype' + 'wl-clipboard' (Wayland) or 'xdotool' (X11); 'ydotool' also works."), config.color_error)
        return
    if not check_command_exists("paplay"):
        print_status(_("'paplay' not found. Sound notifications will be disabled."), config.color_warning)
    print_status(_("Dependencies checked."), config.color_info)

    print_status(_("Attempting to load model for language: {lang}").format(lang=ui_lang), config.color_info)
    model, recognizer, loaded_model_name = load_model(ui_lang)

    if not recognizer:
        default_model_name = config.default_model_name
        if ui_lang != default_model_name:
            print_status(_("Failed. Attempting to load default model: {model_name}").format(model_name=default_model_name), config.color_info)
            model, recognizer, loaded_model_name = load_model(default_model_name)

    if not recognizer:
        print_status(_("FATAL: No speech recognition model could be loaded."), config.color_error)
        print_status(_("Please check the model paths and integrity in your config.yaml file."), config.color_error)
        return 1

    lang_of_loaded_model = config.get_lang_from_model_name(loaded_model_name)
    if lang_of_loaded_model and lang_of_loaded_model != config.current_lang:
        config.set_language(lang_of_loaded_model)
        set_ui_language(lang_of_loaded_model)
        _ = get_translation()

    p, stream = initialize_audio()
    if not p or not stream: return 1

    # Files bornées (chantier 7 volet C). audio_queue : ~2 s d'audio ; au-delà,
    # audio_capture_thread jette le bloc le plus ancien pour interdire la dérive
    # de latence. text_queue / control_queue : un remplissage y est
    # pathologique (UI figée), signalé bruyamment, jamais masqué.
    audio_queue = queue.Queue(maxsize=config.audio.get('queue_max_chunks', 16))
    text_queue = queue.Queue(maxsize=64)
    control_queue = queue.Queue(maxsize=32)
    stop_event = threading.Event()
    display_partials_event = threading.Event()
    sleep_event = threading.Event()
    # wake_event : posé = éveillé (reconnaissance active), effacé = VEILLE
    # (flux audio fermé, thread de reconnaissance bloqué). Chantier 7 volet D.
    wake_event = threading.Event()
    wake_event.set()

    processor = TextProcessor(config.current_lang)

    threads = [
        threading.Thread(target=recognition_thread, args=(model, recognizer, audio_queue, text_queue, control_queue, stop_event, display_partials_event, wake_event)),
        threading.Thread(target=audio_capture_thread, args=(p, stream, audio_queue, stop_event, sleep_event, wake_event)),
        threading.Thread(target=keyboard_listener_thread, args=(control_queue, stop_event)),
        threading.Thread(target=ui_thread, args=(text_queue, control_queue, stop_event, processor, display_partials_event, sleep_event, wake_event))
    ]

    for t in threads:
        if t is not threading.current_thread():
            t.daemon = True

    # Socket de contrôle (chantier 7 volet A). Non bloquant si le bind échoue :
    # l'outil reste utilisable en interactif, seules les sous-commandes CLI
    # sont indisponibles.
    control_server = None
    if config.data.get('control_socket', True):
        try:
            control_server = start_control_server(control_queue, stop_event)
            print_status(_("Control socket: {path}").format(path=socket_path()), config.color_info)
        except OSError as e:
            print_status(_("Could not open the control socket ({err}); CLI subcommands disabled.").format(err=e), config.color_warning)

    def _cleanup_socket():
        try:
            os.unlink(socket_path())
        except OSError:
            pass

    atexit.register(_cleanup_socket)
    # SIGTERM (kill, systemctl --user stop) : arrêt propre. Ctrl+C garde son
    # chemin KeyboardInterrupt existant.
    try:
        signal.signal(signal.SIGTERM, lambda *_a: stop_event.set())
    except (ValueError, OSError):
        pass

    ready_message = _("The script is ready. Current model: {model_name}").format(model_name=loaded_model_name.upper())
    print_status(ready_message, config.color_ready_message)
    print_help_message()

    try:
        for t in threads: t.start()

        while not stop_event.is_set():
            if sys.stdin.isatty() and select.select([sys.stdin], [], [], 0.1)[0]:
                line = sys.stdin.readline().strip()
                if line.startswith('/'):
                    try:
                        control_queue.put_nowait(line)
                    except queue.Full:
                        print_status(_("Control queue full; command ignored."), config.color_error)
            else:
                stop_event.wait(0.1)

    except KeyboardInterrupt:
        print_status(_("\nStop request received. Shutting down..."), config.color_info)
    finally:
        if not stop_event.is_set():
            stop_event.set()
        wake_event.set()          # débloque le thread de reconnaissance

        # Attendre la sortie effective des threads *avant* de fermer le flux et
        # de terminer PortAudio : sinon audio_capture_thread peut être encore
        # dans stream.read() quand p.terminate() passe, ce qui faisait sortir
        # le démon en code 1 sur --stop (chantier 7 volet H).
        for t in threads:
            if t is not threading.current_thread():
                t.join(timeout=2.0)

        # Le thread de capture possède le flux (ouverture/fermeture sur VEILLE) ;
        # cette fermeture-ci est un filet défensif, d'où le try/except.
        try:
            if stream is not None and stream.is_active():
                stream.stop_stream()
                stream.close()
        except Exception:
            pass

        if p:
            try:
                p.terminate()
            except Exception:
                pass

    return 0

if __name__ == "__main__":
    sys.exit(main() or 0)
