# src/recognition.py

import json
import queue
import os
import time
from vosk import Model, KaldiRecognizer
from config.config import config
from src.i18n import get_translation
from src.runtime_state import (
    runtime_state, STATE_DICTATING, STATE_LISTENING, STATE_SLEEPING,
)
from src.voice_commands import (
    normalize_tokens, phrase_tokens, find_phrase, ends_with_phrase, mean_confidence,
)

MODE_FULL = "full"
MODE_LISTENING = "listening"


def load_model(model_name: str):
    """
    Loads a Vosk model by its name (e.g., 'fr').
    Returns (model, recognizer, model_name_on_disk) or (None, None, None) on failure.

    The Model object is returned alongside the recognizer so the recognition
    thread can rebuild a restricted-grammar recognizer for ÉCOUTE and a full
    one for DICTÉE without reloading the model from disk (chantier 7 volet E).
    """
    _ = get_translation()
    model_path = config.get_model_path_by_name(model_name)

    if not model_path:
        for model in config.data.get('vosk_models', []):
            if model['name'] != model_name or os.path.isabs(model['path_relative']):
                continue
            print(f"{config.color_error}{_('No model found for')} '{model_name}'.{config.RESET}")
            print(f"{config.color_info}{_('Searched:')}{config.RESET}")
            for racine in config.model_search_roots(model['path_relative']):
                print(f"  - {racine}")
            print(f"{config.color_info}{_('Download Vosk models from:')} https://alphacephei.com/vosk/models{config.RESET}")
            break
        return None, None, None

    model_name_on_disk = os.path.basename(model_path)

    if not os.path.isdir(model_path):
        print(f"{config.color_error}{_('Error: Model folder not found:')} {model_path}{config.RESET}")
        print(f"{config.color_info}{_('Please check your config.yaml and ensure the model is unzipped.')}{config.RESET}")
        return None, None, None

    try:
        print(f"{config.color_info}{_('Attempting to load model:')} {model_name_on_disk}...{config.RESET}")
        model = Model(model_path)
        recognizer = build_recognizer(model, MODE_FULL)
        print(f"{config.color_success}{_('Model loaded successfully:')} {model_name_on_disk}{config.RESET}")
        return model, recognizer, model_name_on_disk
    except Exception as e:
        error_msg = _("Fatal error while loading model '{model_name}': {error}").format(model_name=model_name_on_disk, error=e)
        print(f"{config.color_error}{error_msg}{config.RESET}")
        return None, None, None


def build_recognizer(model, mode: str):
    """Builds a KaldiRecognizer for the given mode (chantier 7 volet E).

    - MODE_FULL: full vocabulary, used in DICTÉE (and in ÉCOUTE when the
      restricted grammar is disabled).
    - MODE_LISTENING: grammar restricted to the wake phrase plus "[unk]", so
      the decoder does almost no work while idle. Rebuilt back to MODE_FULL on
      waking.
    """
    sample_rate = config.audio['sample_rate']
    if mode == MODE_LISTENING:
        # ensure_ascii=False est indispensable : Vosk ne déséchappe pas les
        # \uXXXX dans la grammaire, il traiterait « dictée » comme le mot
        # littéral "dictée" et le déclarerait hors vocabulaire.
        grammar = json.dumps([config.WAKE_PHRASE, "[unk]"], ensure_ascii=False)
        rec = KaldiRecognizer(model, sample_rate, grammar)
    else:
        rec = KaldiRecognizer(model, sample_rate)
    rec.SetWords(True)
    return rec


def _target_mode(state: str) -> str:
    """Which recognizer mode a given state wants.

    The restricted grammar in ÉCOUTE is opt-out per language: a
    `restricted_grammar_in_listening` key under `language_settings.<lang>`
    overrides the global `recognition.restricted_grammar_in_listening`.
    Disabled for `es` (chantier 7, banc du 28/08 : la grammaire restreinte y
    décode plus lentement que la grammaire complète).
    """
    if state != STATE_LISTENING:
        return MODE_FULL
    global_default = config.data.get('recognition', {}).get(
        'restricted_grammar_in_listening', True
    )
    per_lang = config.language_settings.get(config.current_lang, {}).get(
        'restricted_grammar_in_listening', global_default
    )
    return MODE_LISTENING if per_lang else MODE_FULL


def recognition_thread(model, recognizer, audio_queue: queue.Queue, text_queue: queue.Queue,
                       control_queue: queue.Queue, stop_event, display_partials_event, wake_event):
    """
    Decodes audio and drives the voice-command semantics (chantier 7 volet E).

    - In DICTÉE: final results (text + per-word confidence) go to the UI thread,
      which handles the stop phrase and typing.
    - In ÉCOUTE: the wake phrase is matched on the token sequence — on partial
      results when the restricted grammar is active (low-latency wake), on final
      results with a confidence gate otherwise. A match asks the UI thread to
      switch to DICTÉE and Resets the recognizer so the phrase is not re-emitted.
    - In VEILLE: the thread blocks on wake_event (volet D); on waking it rebuilds
      the recognizer for the current target state.
    """
    _ = get_translation()
    last_partial_length = 0
    in_progress_label = _("[In progress]")

    chunk_audio_s = config.audio['buffer_size'] / config.audio['sample_rate']
    last_rtf_warning = 0.0

    conf_threshold = config.data.get('recognition', {}).get('confidence_threshold', 0.85)
    wake_tokens = phrase_tokens(config.WAKE_PHRASE)

    # current_mode volontairement incohérent avec last_state=None : la première
    # itération réconcilie le recognizer avec l'état de départ. Au lancement
    # normal l'appli est en ÉCOUTE avec un recognizer complet ; sans cette
    # réconciliation la grammaire restreinte ne s'activerait jamais au repos.
    current_mode = MODE_FULL
    last_state = None
    # Après avoir demandé une transition, on cesse de détecter jusqu'à ce que
    # l'état ait réellement changé (évite les demandes en rafale, le temps que
    # le thread UI traite la control_queue).
    pending_wake = False

    def clear_partial():
        nonlocal last_partial_length
        if last_partial_length > 0:
            print(f"\r{' ' * last_partial_length}\r", end='', flush=True)
            last_partial_length = 0

    def rebuild_for(state):
        nonlocal recognizer, current_mode
        want = _target_mode(state)
        if want != current_mode:
            recognizer = build_recognizer(model, want)
            current_mode = want
        else:
            try:
                recognizer.Reset()
            except Exception:
                pass

    def request_wake():
        nonlocal pending_wake
        try:
            control_queue.put_nowait("DICTATION_ON")
            pending_wake = True
        except queue.Full:
            print(f"\n{config.color_error}"
                  f"{_('Control queue full; the UI thread is not responding.')}"
                  f"{config.RESET}")

    while not stop_event.is_set():
        if not wake_event.is_set():
            if wake_event.wait(timeout=1.0):
                clear_partial()
                # Sortie de VEILLE : reconstruire pour l'état courant.
                last_state = runtime_state.state
                pending_wake = False
                current_mode = None  # force la reconstruction
                rebuild_for(last_state)
            continue

        # Suivi des transitions d'état pour l'échange de grammaire.
        state = runtime_state.state
        if state != last_state:
            if state == STATE_SLEEPING:
                pass  # géré par wake_event au tour suivant
            else:
                rebuild_for(state)
            if state != STATE_LISTENING:
                pending_wake = False
            last_state = state

        try:
            data = audio_queue.get(timeout=0.1)

            t0 = time.perf_counter()
            is_final = recognizer.AcceptWaveform(data)
            if chunk_audio_s > 0:
                runtime_state.update_rtf((time.perf_counter() - t0) / chunk_audio_s)
                if runtime_state.rtf_over(0.9):
                    now = time.monotonic()
                    if now - last_rtf_warning >= 5.0:
                        last_rtf_warning = now
                        snap = runtime_state.snapshot()
                        print(f"\n{config.color_warning}"
                              f"{_('Decoding is slower than real time (RTF {rtf}); latency may drift.').format(rtf=snap['rtf_mean'])}"
                              f"{config.RESET}")

            if is_final:
                result_dict = json.loads(recognizer.Result())
                text = result_dict.get("text", "")
                words = result_dict.get("result", [])

                if state == STATE_LISTENING:
                    if not pending_wake and not runtime_state.in_debounce():
                        tokens = normalize_tokens(text)
                        idx = find_phrase(tokens, wake_tokens)
                        if idx != -1:
                            ok = True
                            if current_mode != MODE_LISTENING:
                                conf = mean_confidence(words, idx, len(wake_tokens))
                                ok = conf >= conf_threshold
                            if ok:
                                try:
                                    recognizer.Reset()
                                except Exception:
                                    pass
                                request_wake()
                    clear_partial()
                    continue

                if state == STATE_DICTATING and text:
                    try:
                        text_queue.put_nowait((text, words))
                    except queue.Full:
                        print(f"\n{config.color_error}"
                              f"{_('Text queue full; the UI thread is not consuming. Dropping a result.')}"
                              f"{config.RESET}")
                    clear_partial()
            else:
                partial_dict = json.loads(recognizer.PartialResult())
                partial_text = partial_dict.get("partial", "").strip()

                # Réveil à faible latence sur les partiels, uniquement sous
                # grammaire restreinte (le décodeur ne peut alors produire que
                # la phrase de réveil ou "[unk]").
                if (state == STATE_LISTENING and current_mode == MODE_LISTENING
                        and partial_text and not pending_wake
                        and not runtime_state.in_debounce()):
                    if ends_with_phrase(normalize_tokens(partial_text), wake_tokens):
                        try:
                            recognizer.Reset()
                        except Exception:
                            pass
                        clear_partial()
                        request_wake()
                        continue

                if display_partials_event.is_set() and partial_text:
                    print(f"\r{' ' * last_partial_length}\r", end='', flush=True)
                    display_text = f"{config.color_info}{in_progress_label} {partial_text}{config.RESET}"
                    print(display_text, end='', flush=True)
                    last_partial_length = len(in_progress_label) + 1 + len(partial_text)
                elif last_partial_length > 0:
                    print(f"\r{' ' * last_partial_length}\r", end='', flush=True)
                    last_partial_length = 0

        except queue.Empty:
            continue
        except Exception as e:
            clear_partial()
            print(f"\n{config.color_error}{_('Error in recognition thread:')} {e}{config.RESET}")
            break

    clear_partial()
