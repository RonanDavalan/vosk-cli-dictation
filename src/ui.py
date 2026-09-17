# src/ui.py

import queue
import time
import pyperclip

from config.config import config
from src.system_control import (
    type_text, press_key, play_sound, flush_deferred_clipboard,
)
from src.i18n import get_translation, set_ui_language
from src.text_processing import TextProcessor
from src.runtime_state import (
    runtime_state, STATE_DICTATING, STATE_LISTENING, STATE_SLEEPING,
)
from src.voice_commands import (
    normalize_tokens, phrase_tokens, find_phrase, is_doubled,
    strip_one_repetition, remove_phrase_and_after, mean_confidence,
)

# Cadence du rappel « micro en veille » tant que la VEILLE dure. Assez espacé
# pour ne pas harceler, assez fréquent pour qu'un utilisateur qui dicte dans
# le vide s'en aperçoive vite.
SLEEP_REMINDER_INTERVAL_S = 30.0

def ui_thread(text_queue: queue.Queue, control_queue: queue.Queue, stop_event, processor: TextProcessor, display_partials_event, sleep_event, wake_event):
    recording = False
    full_text_log = ""
    xdotool_failed_once = False

    # Détection tokenisée de la phrase d'arrêt. Le réveil (phrase de réveil en
    # ÉCOUTE) est piloté par le thread de reconnaissance, qui a accès aux
    # résultats partiels et à la grammaire restreinte.
    stop_tokens = phrase_tokens(config.STOP_PHRASE)
    conf_threshold = config.recognition_setting('confidence_threshold', 0.55)
    last_low_conf_hint = [0.0]  # horodatage du dernier indice, pour le throttle
    last_sleep_reminder = [0.0]  # horodatage du dernier rappel « micro en veille »

    def start_recording():
        nonlocal recording, full_text_log, xdotool_failed_once
        _ = get_translation()
        # Une demande de dictée pendant la VEILLE sort d'abord de veille
        # (rouvre le micro) AVANT de démarrer, sinon on ouvre une DICTÉE
        # fantôme sur un périphérique fermé. La garde est portée ici pour
        # qu'aucun chemin d'appel (TOGGLE_RECORDING, DICTATION_ON, /nl) ne
        # puisse la contourner.
        woke_from_sleep = False
        if sleep_event.is_set():
            sleep_event.clear()
            wake_event.set()
            runtime_state.set_state(STATE_LISTENING)
            woke_from_sleep = True
        recording = True
        runtime_state.set_state(STATE_DICTATING)
        display_partials_event.set()
        full_text_log = ""
        xdotool_failed_once = False
        processor.reset_state()
        # Couleurs du thème depuis la configuration
        # Sur une sortie de veille implicite, une seule ligne cohérente au lieu
        # de « veille désactivée » suivi de « enregistrement démarré » — deux
        # messages qui se lisent comme contradictoires.
        if woke_from_sleep:
            print(f"\n{config.color_success}{_('Waking from sleep; recording started.')}{config.RESET}")
        else:
            print(f"\n{config.color_success}{_('Recording started.')}{config.RESET}")
        play_sound()

    def stop_recording():
        nonlocal recording
        _ = get_translation()
        recording = False
        runtime_state.set_state(STATE_LISTENING)
        display_partials_event.clear()
        # Correctif de collage : fin de session de dictée -> on rend le
        # presse-papiers d'origine si clipboard.defer_restore l'a mis de côté.
        flush_deferred_clipboard()
        # Couleurs du thème depuis la configuration
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
        # Correctif de collage : rendre le presse-papiers d'origine (mode
        # clipboard.defer_restore) avant d'y copier le texte de session.
        flush_deferred_clipboard()
        text_to_copy = full_text_log.strip()
        # Sur une session sans presse-papiers accessible (SSH nu, pas de
        # DISPLAY, pas de xclip/xsel/wl-clipboard), pyperclip.copy lève une
        # exception qui remontait hors du thread UI et le tuait. On la capture :
        # le texte est imprimé sur stdout et la finalisation se poursuit
        # normalement. pyperclip reste le mécanisme de copie (acquis
        # technique), non remplacé.
        copied = True
        if text_to_copy:
            try:
                pyperclip.copy(text_to_copy)
            except Exception:
                copied = False
                print(f"\n{config.color_warning}"
                      f"{_('Clipboard unavailable — session text below:')}"
                      f"{config.RESET}\n{text_to_copy}")
        msg = _('Recording finished. Text copied.') if copied \
            else _('Recording finished. Clipboard unavailable — text printed above.')
        # Couleurs du thème depuis la configuration
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
            else:
                # stop_recording() l'aurait fait ; on couvre l'entrée en VEILLE
                # depuis l'ÉCOUTE (mode clipboard.defer_restore).
                flush_deferred_clipboard()
            sleep_event.set()
            wake_event.clear()
            runtime_state.set_state(STATE_SLEEPING)
            # Le premier rappel « micro en veille » attend un intervalle complet
            # après l'entrée en VEILLE.
            last_sleep_reminder[0] = time.monotonic()
            print(f"\n{config.color_warning}{_('Sleep mode enabled — the microphone is released.')}{config.RESET}")
        play_sound()

    def maybe_sleep_reminder():
        """Tant que la VEILLE dure, un rappel throttlé que le micro ne capte
        rien — entre le silence trompeur et la boucle « audio abandonné », un
        retour honnête à cadence fixe."""
        if not sleep_event.is_set():
            return
        now = time.monotonic()
        if now - last_sleep_reminder[0] >= SLEEP_REMINDER_INTERVAL_S:
            last_sleep_reminder[0] = now
            _ = get_translation()
            print(f"\n{config.color_warning}"
                  f"{_('Microphone asleep — Alt+W or --wake to resume.')}"
                  f"{config.RESET}")

    def execute_manual_command(command: str):
        nonlocal full_text_log, recording
        _ = get_translation()

        command = command.strip()
        if not command.startswith('/'): return
        cmd_parts = command[1:].split()
        if not cmd_parts: return
        cmd_name = cmd_parts[0].lower()

        # Couleurs du thème depuis la configuration
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
            # /nl est une demande de dictée — en VEILLE, on réveille et on
            # démarre l'enregistrement avant d'insérer le saut.
            if sleep_event.is_set():
                start_recording()
            if recording:
                process_and_type(to_add)
                print(f"{config.color_warning}{_('New paragraph inserted.')}{config.RESET}")
            else:
                full_text_log += to_add
                processor.capitalize_next_word = True
                print(f"{config.color_warning}{_('New paragraph added to buffer.')}{config.RESET}")
        else:
            print(f"{config.color_error}{_('Unknown command:')} {command}{config.RESET}")

    def emit_low_conf_hint():
        """Indice throttlé quand la phrase d'arrêt est entendue mais sous le
        seuil de confiance. La phrase est absorbée (pas tapée) ; cet indice
        dit à l'utilisateur comment arrêter malgré tout."""
        _ = get_translation()
        now = time.monotonic()
        if now - last_low_conf_hint[0] >= 2.0:
            last_low_conf_hint[0] = now
            msg = _("Heard the stop phrase but confidence was low. Repeat it, or use the stop hotkey / --finalize.")
            print(f"\n{config.color_warning}{msg}{config.RESET}")

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

        # Couleurs du thème depuis la configuration
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
            maybe_sleep_reminder()
            try:
                command = control_queue.get_nowait()
                if command == 'TOGGLE_RECORDING':
                    if recording: stop_recording()
                    else: start_recording()
                elif command == 'DICTATION_ON':
                    # Plus de garde `not sleep_event` ici — start_recording()
                    # sort de veille de lui-même.
                    if not recording: start_recording()
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
                    before = remove_phrase_and_after(raw_text, stop_tokens)
                    if before:
                        process_and_type(before)
                    if conf >= conf_threshold:
                        finalize_session()
                    else:
                        # Confiance insuffisante -> la phrase et ce qui la suit
                        # sont ABSORBÉS (ni finalisation, ni frappe). L'ancien
                        # code la tapait dans le document — seul résultat
                        # qu'une commande d'arrêt ne doit jamais produire.
                        # L'utilisateur répète, ou passe par --finalize / le
                        # raccourci.
                        emit_low_conf_hint()
                    continue

                if raw_text:
                    process_and_type(raw_text)
            except queue.Empty:
                time.sleep(0.01)
                continue
    except KeyboardInterrupt: pass
    finally:
        if not stop_event.is_set(): stop_event.set()
        # Couleurs du thème depuis la configuration
        msg = _("Stopping user interface...")
        print(f"\n{config.color_info}{msg}{config.RESET}")
