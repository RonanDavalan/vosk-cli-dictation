# src/main.py

import sys
import os
import threading
import queue
import atexit
import argparse
import select
import signal
import textwrap
import vosk

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from config.config import config
from src.i18n import set_ui_language, get_translation
from src.system_control import check_command_exists, injection_backend_available
from src.audio_capture import initialize_audio, audio_capture_thread
from src.recognition import load_model, recognition_thread, force_c_numeric_locale
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
    """Print status message with color, restoring the terminal default after."""
    print(f"{color}{message}{config.RESET}")

# Glyphes typographiques que la plupart des terminaux rendent sur deux cellules
# (largeur « ambiguë » Est-asiatique) : guillemets courbes, chevrons, tirets
# cadratin / demi-cadratin, points de suspension, ponctuation espagnole ouvrante.
# Ils apparaissent dans les libellés de la section `punctuation` des configs
# fr/de/es/en. `len()` les compte pour 1, ce qui décalait la seconde colonne du
# tableau d'aide en escalier ; on les compte pour 2 dans le calcul de largeur.
_WIDE_GLYPHS = set("„“”‘’«»—–…¡¿")

def _display_width(text):
    """Largeur d'affichage de `text` en cellules de terminal (voir _WIDE_GLYPHS)."""
    return sum(2 if ch in _WIDE_GLYPHS else 1 for ch in text)

def _wrap_help_line(text, width=74):
    """Replie une ligne d'aide à puce (« - … ») pour tenir dans un terminal de
    80 colonnes, les lignes de continuation alignées sous le texte de la puce.
    `width` reste sous 80 pour absorber les glyphes larges que `textwrap` compte
    pour un (les chevrons « » des libellés fr/de)."""
    return textwrap.fill(
        text, width=width, subsequent_indent="    ",
        break_long_words=False, break_on_hyphens=False,
    )

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

    # Chantier 11 : la bannière décrit le mode de déclenchement réellement actif
    # plutôt que de toujours présenter toggle -- un banc en maintenue/silence
    # affichant des instructions toggle induirait l'utilisateur en erreur.
    mode = config.interaction_mode
    if mode == 'maintenue':
        ptt_key = config.hotkeys.get('push_to_talk') or '?'
        intro_lines = (
            _("  - Hold [{key}] to dictate; release to stop and copy.").format(key=ptt_key),
            _("  - Say '{stop_phrase}' or run 'vosk-cli-dictation --finalize' to stop early.").format(stop_phrase=stop_phrase),
            _("  - Hotkeys reach the focused window and miss native-Wayland windows; use --finalize."),
        )
    elif mode == 'silence':
        timeout_ms = config.interaction_setting('silence_timeout_ms', 700)
        intro_lines = (
            _("  - Say '{wake_phrase}' or press {hotkey} to start.").format(wake_phrase=wake_phrase, hotkey=toggle_hotkey),
            _("  - Stops and copies on its own after {timeout_ms} ms of silence, or say '{stop_phrase}' / press {hotkey} / run 'vosk-cli-dictation --finalize' to stop early.").format(timeout_ms=timeout_ms, stop_phrase=stop_phrase, hotkey=finalize_hotkey),
            _("  - Hotkeys reach the focused window and miss native-Wayland windows; use --finalize."),
        )
    else:
        intro_lines = (
            _("  - Say '{wake_phrase}' or press {hotkey} to start/stop.").format(wake_phrase=wake_phrase, hotkey=toggle_hotkey),
            _("  - Say '{stop_phrase}', press {hotkey}, or run 'vosk-cli-dictation --finalize' to stop and copy.").format(stop_phrase=stop_phrase, hotkey=finalize_hotkey),
            _("  - Hotkeys reach the focused window and miss native-Wayland windows; use --finalize."),
        )
    for line in intro_lines:
        print_status(_wrap_help_line(line), config.color_help_text)

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

        # AFFICHE DYNAMIQUEMENT TOUTES les commandes de ponctuation de la config,
        # triées par ordre alphabétique. La largeur de colonne suit le libellé le
        # plus large de la langue courante, mesuré en cellules d'affichage
        # (`_display_width`, pas `len()` : un `„` ou un `—` occupe deux cellules
        # dans un terminal et décalait la colonne de droite en escalier). Si une
        # paire ne tient pas dans 80 colonnes, on passe à une seule colonne.
        entries = [
            f"{cmd} ({repr(all_punctuation_cmds[cmd])[1:-1]})"
            for cmd in sorted(all_punctuation_cmds.keys())
        ]
        widest = max((_display_width(e) for e in entries), default=0)
        if widest * 2 + 4 <= 80:
            col_width = widest + 2
            for i in range(0, len(entries), 2):
                line_str = "  " + entries[i]
                if i + 1 < len(entries):
                    line_str += " " * (col_width - _display_width(entries[i]))
                    line_str += entries[i + 1]
                print_status(line_str.rstrip(), config.color_help_text)
        else:
            for entry in entries:
                print_status("  " + entry, config.color_help_text)

    print(separator)
    print_status(_("Press Ctrl+C to exit the program."), config.color_help_text)


def supervise_threads(supervised, stop_event):
    """Chantier stabilité v0.5.1, défaut 1 : si l'un des threads cœur
    (`recognition`, `audio`, `ui`) meurt sans que `stop_event` soit posé, on
    pose `stop_event` et on retourne son nom pour que la boucle principale
    termine la session proprement au lieu de tourner à vide. Retourne None si
    tout va bien ou si l'arrêt est déjà demandé.
    """
    if stop_event.is_set():
        return None
    for name, t in supervised.items():
        if not t.is_alive():
            stop_event.set()
            return name
    return None


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
    # Chantier stabilité v0.5.1 : neutralise LC_NUMERIC pour tout le processus
    # avant que Vosk ne sérialise le moindre Result(). Sous une locale à virgule
    # (p. ex. fr_FR.UTF-8), les flottants de SetWords(True) sortent en
    # « 1,000000 » et cassent json.loads à chaque final avec mots. Répété
    # défensivement dans src/recognition.py avant chaque KaldiRecognizer.
    force_c_numeric_locale()

    # R5 (28/08 soir) : coupe les LOG (VoskAPI...) au boot — le bruit de Vosk
    # s'affichait après « Appuyez sur Ctrl+C pour quitter » (démarrage des
    # threads après l'aide). --diagnose n'a pas besoin de ces logs.
    vosk.SetLogLevel(-1)

    # -l/--lang doit s'appliquer à TOUT ce qui peut s'afficher avant la fin de
    # parse_args() (--help, --diagnose) — pas seulement à la dictée elle-même.
    # argparse fige le texte d'aide dans la langue de `_` au moment où chaque
    # add_argument() est appelé, donc trop tard pour agir après coup : on
    # pré-scanne sys.argv à la main pour connaître la langue demandée avant
    # de construire le parseur.
    pre_lang = None
    argv = sys.argv[1:]
    for i, token in enumerate(argv):
        if token in ('-l', '--lang') and i + 1 < len(argv):
            pre_lang = argv[i + 1]
            break
        if token.startswith('--lang='):
            pre_lang = token.split('=', 1)[1]
            break

    set_ui_language(pre_lang or config.default_model)
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
    parser.add_argument('--download-model', nargs='?', const='', default=None, metavar='LANG',
                        help=_("download the small model for LANG (or the current language) and exit"))
    args = parser.parse_args()

    if args.diagnose:
        from src.diagnose import run_diagnose
        sys.exit(run_diagnose())

    if args.download_model is not None:
        from src.model_download import download_model
        lang = args.download_model or args.lang or config.default_model
        sys.exit(0 if download_model(lang) else 1)

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

    if not recognizer and sys.stdin.isatty():
        answer = input(_("No speech recognition model could be loaded. Download the small model for '{lang}' now? [y/N] ").format(lang=ui_lang))
        if answer.strip().lower() in ("y", "yes", "o", "oui"):
            from src.model_download import download_model
            if download_model(ui_lang):
                model, recognizer, loaded_model_name = load_model(ui_lang)

    if not recognizer:
        print_status(_("No speech recognition model could be loaded."), config.color_error)
        print_status(_("Run 'vosk-cli-dictation --download-model {lang}' to download one.").format(lang=ui_lang), config.color_error)
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

    # Chantier stabilité v0.5.1, défaut 1 : threads cœur surveillés par la
    # boucle principale. Le listener clavier est exclu — son absence (pynput
    # indisponible) est un cas légitime, pas une panne.
    supervised = {
        "recognition": threads[0],
        "audio": threads[1],
        "ui": threads[3],
    }

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

    # Où l'outil a réellement trouvé le modèle et la config, pour éviter d'avoir
    # à se rappeler ~/.local/share contre ~/.config, et pour les rapports de bug.
    model_path = config.get_model_path_by_name(loaded_model_name)
    if model_path:
        print_status(_("Model directory: {path}").format(path=model_path), config.color_info)
    config_line = _("Config file in use: {path}").format(path=config.config_path)
    if config.local_config_path:
        config_line += f"  (+ {os.path.basename(config.local_config_path)})"
    print_status(config_line, config.color_info)

    ready_message = _("The script is ready. Current model: {model_name}").format(model_name=loaded_model_name)
    print_status(ready_message, config.color_ready_message)
    print_help_message()

    try:
        for t in threads: t.start()

        while not stop_event.is_set():
            dead = supervise_threads(supervised, stop_event)
            if dead is not None:
                print_status(
                    _("The {name} thread stopped; ending the session.").format(name=dead),
                    config.color_error,
                )
                break
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
