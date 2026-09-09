# src/recognition.py

import json
import queue
import os
import time
import datetime
from vosk import Model, KaldiRecognizer
from config.config import config
from src.i18n import get_translation
from src.runtime_state import (
    runtime_state, STATE_DICTATING, STATE_LISTENING, STATE_SLEEPING,
)
from src.voice_commands import (
    normalize_tokens, phrase_tokens, find_phrase, mean_confidence,
)

MODE_FULL = "full"
MODE_LISTENING = "listening"

# Chantier stabilité v0.5.1, défaut 1 (révision 09/09 soir). Une trame malformée
# ne tue plus le thread : on reconstruit le recognizer. Mais si la
# reconstruction ne rétablit rien — cas observé sur `ada`, json.JSONDecodeError
# à chaque trame, Reset() sans effet — on ne boucle pas indéfiniment : au-delà
# de DECODE_ERROR_MAX_CONSECUTIVE trames en échec d'affilée, le thread pose
# stop_event et termine la session proprement. Tout décodage réussi remet le
# compteur à zéro.
DECODE_ERROR_MAX_CONSECUTIVE = 5


def _diagnostics_dir() -> str:
    """Répertoire d'écriture des captures de diagnostic (chaîne Result() fautive).

    Jamais /tmp, jamais le dépôt de code. Ordre de préférence :
    1. $VOSK_CLI_DIAG_DIR s'il est défini ;
    2. `scripts/diagnostics/` du répertoire tampon, à côté du dépôt de code, s'il
       existe déjà (cas du poste de développement) ;
    3. `~/.local/state/vosk-cli-dictation/diagnostics/` (cas paquet installé).
    """
    env = os.environ.get("VOSK_CLI_DIAG_DIR")
    if env:
        return env
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    tampon_scripts = os.path.join(os.path.dirname(repo_root), "scripts")
    if os.path.isdir(tampon_scripts):
        return os.path.join(tampon_scripts, "diagnostics")
    base = os.environ.get("XDG_STATE_HOME") or os.path.expanduser("~/.local/state")
    return os.path.join(base, "vosk-cli-dictation", "diagnostics")


def _capture_malformed_result(raw: str) -> str:
    """Écrit la chaîne brute renvoyée par Result()/PartialResult() qui n'a pas
    pu être parsée en JSON. Retourne le chemin écrit, ou '' si l'écriture a
    échoué. Tronque à 1 Kio."""
    snippet = raw[:1024] if isinstance(raw, str) else repr(raw)[:1024]
    try:
        d = _diagnostics_dir()
        os.makedirs(d, exist_ok=True)
        stamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
        path = os.path.join(d, f"vosk-result-malforme_{stamp}.txt")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(snippet)
        return path
    except Exception:
        return ""


# Chantier 7 bis : recognizer secondaire en DICTÉE, grammaire restreinte à la
# phrase d'arrêt. Détection d'arrêt de haute confiance, indépendante du garde
# de confiance sur le recognizer complet.
MODE_STOP = "stop"


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
            print(f"{config.color_info}{_('Or run:')} vosk-cli-dictation --download-model {model_name}{config.RESET}")
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
    if mode in (MODE_LISTENING, MODE_STOP):
        # ensure_ascii=False est indispensable : Vosk ne déséchappe pas les
        # \uXXXX dans la grammaire, il traiterait « dictée » comme le mot
        # littéral "dictée" et le déclarerait hors vocabulaire.
        phrase = config.WAKE_PHRASE if mode == MODE_LISTENING else config.STOP_PHRASE
        grammar = json.dumps([phrase, "[unk]"], ensure_ascii=False)
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
    per_lang = config.recognition_setting('restricted_grammar_in_listening', True)
    return MODE_LISTENING if per_lang else MODE_FULL


def recognition_thread(model, recognizer, audio_queue: queue.Queue, text_queue: queue.Queue,
                       control_queue: queue.Queue, stop_event, display_partials_event, wake_event):
    """
    Decodes audio and drives the voice-command semantics (chantier 7 volet E).

    - In DICTÉE: final results (text + per-word confidence) go to the UI thread,
      which handles the stop phrase and typing.
    - In ÉCOUTE: the wake phrase is matched on a final result with a
      confidence gate (R1, 28/08 soir) — the low-latency wake on partial
      results was removed: under the restricted grammar, partials force the
      phrase onto ambiguous audio and woke on « active » alone. A match asks
      the UI thread to switch to DICTÉE and Resets the recognizer so the
      phrase is not re-emitted.
    - In VEILLE: the thread blocks on wake_event (volet D); on waking it rebuilds
      the recognizer for the current target state.
    """
    _ = get_translation()
    last_partial_length = 0
    in_progress_label = _("[In progress]")

    chunk_audio_s = config.audio['buffer_size'] / config.audio['sample_rate']
    last_rtf_warning = 0.0
    # Chantier stabilité v0.5.1, défaut 1 : cadence fixe du log d'erreur de
    # décodage. Une trame malformée ne tue plus le thread ; on la journalise au
    # plus une fois toutes les DECODE_ERROR_THROTTLE_S secondes.
    last_decode_error_warning = 0.0
    DECODE_ERROR_THROTTLE_S = 5.0
    # Trames en échec de décodage consécutives (remis à zéro par tout décodage
    # réussi) et capture unique de la chaîne fautive pour la session.
    consecutive_decode_errors = 0
    malformed_result_captured = False

    conf_threshold = config.recognition_setting('confidence_threshold', 0.55)
    wake_tokens = phrase_tokens(config.WAKE_PHRASE)
    # Chantier 7 ter (T4) : après un réveil ÉCOUTE->DICTÉE, l'audio mis en file
    # pendant la reconstruction du recognizer contient la fin de « active
    # dictée » et du silence — décodé, il produisait un mot parasite (« Les »).
    # On vide la file à la transition et on ignore les résultats du recognizer
    # complet pendant cette courte fenêtre.
    wake_discard_ms = config.recognition_setting('wake_discard_ms', 300)
    discard_until = 0.0
    # Chantier 7 bis : détecteur d'arrêt à grammaire restreinte en DICTÉE.
    stop_tokens = phrase_tokens(config.STOP_PHRASE)
    restricted_stop_enabled = bool(
        config.recognition_setting('restricted_stop_in_dictation', True)
    )

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
    # Chantier 7 bis : recognizer d'arrêt (None hors DICTÉE ou si désactivé) et
    # verrou anti-rafale symétrique de pending_wake.
    stop_rec = None
    pending_stop = False

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

    def rebuild_stop_rec(state):
        """Chantier 7 bis : (re)construit le recognizer d'arrêt en DICTÉE, le
        libère ailleurs. Reset s'il existe déjà pour repartir d'un flux propre."""
        nonlocal stop_rec
        if state == STATE_DICTATING and restricted_stop_enabled:
            if stop_rec is None:
                stop_rec = build_recognizer(model, MODE_STOP)
            else:
                try:
                    stop_rec.Reset()
                except Exception:
                    pass
        else:
            stop_rec = None

    def request_stop():
        nonlocal pending_stop
        try:
            control_queue.put_nowait("FINALIZE_SESSION")
            pending_stop = True
        except queue.Full:
            print(f"\n{config.color_error}"
                  f"{_('Control queue full; the UI thread is not responding.')}"
                  f"{config.RESET}")

    def stop_rec_hit(data) -> bool:
        """Alimente le recognizer d'arrêt avec `data` et dit si la phrase d'arrêt
        vient d'être reconnue.

        Conservateur (chantier 7 bis, après le faux positif du 28/08) :
        - seulement sur un FINAL (les partiels sous grammaire restreinte sont
          instables et « forcent » la phrase sur de l'audio ambigu) ;
        - le texte du final doit être EXACTEMENT la phrase d'arrêt, pas la
          contenir ;
        - confiance moyenne des mots ≥ conf_threshold (une correspondance
          forcée sur de l'audio ambigu score bas).
        """
        try:
            if not stop_rec.AcceptWaveform(data):
                stop_rec.PartialResult()  # draine le partiel, jamais déclencheur
                return False
            res = json.loads(stop_rec.Result())
            toks = normalize_tokens(res.get("text", ""))
            if toks != stop_tokens:
                return False
            return mean_confidence(res.get("result", []), 0, len(stop_tokens)) >= conf_threshold
        except Exception:
            return False

    while not stop_event.is_set():
        if not wake_event.is_set():
            if wake_event.wait(timeout=1.0):
                clear_partial()
                # Sortie de VEILLE : reconstruire pour l'état courant.
                last_state = runtime_state.state
                pending_wake = False
                pending_stop = False
                current_mode = None  # force la reconstruction
                rebuild_for(last_state)
                rebuild_stop_rec(last_state)
            continue

        # Suivi des transitions d'état pour l'échange de grammaire.
        state = runtime_state.state
        if state != last_state:
            if state == STATE_SLEEPING:
                pass  # géré par wake_event au tour suivant
            else:
                rebuild_for(state)
                rebuild_stop_rec(state)
            if state != STATE_LISTENING:
                pending_wake = False
            if state != STATE_DICTATING:
                pending_stop = False
            # T4 : entrée en DICTÉE -> jeter l'audio d'avant la transition et
            # ouvrir une fenêtre d'ignorance des résultats.
            if state == STATE_DICTATING and last_state == STATE_LISTENING:
                try:
                    while True:
                        audio_queue.get_nowait()
                except queue.Empty:
                    pass
                discard_until = time.monotonic() + wake_discard_ms / 1000.0
            last_state = state

        try:
            data = audio_queue.get(timeout=0.1)

            # T4 : fenêtre d'ignorance juste après le réveil — on jette le bloc
            # sans le décoder, pour que le recognizer complet neuf démarre sur
            # de l'audio propre (pas la fin de « active dictée »).
            if state == STATE_DICTATING and time.monotonic() < discard_until:
                clear_partial()
                continue

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

            # Chantier 7 bis : arrêt vocal de haute confiance via le recognizer
            # restreint, avant même que le recognizer complet ait finalisé.
            if (state == STATE_DICTATING and stop_rec is not None
                    and not pending_stop and not runtime_state.in_debounce()):
                if stop_rec_hit(data):
                    try:
                        recognizer.Reset()
                    except Exception:
                        pass
                    try:
                        stop_rec.Reset()
                    except Exception:
                        pass
                    clear_partial()
                    request_stop()
                    continue

            if is_final:
                result_dict = json.loads(recognizer.Result())
                consecutive_decode_errors = 0
                text = result_dict.get("text", "")
                words = result_dict.get("result", [])

                if state == STATE_LISTENING:
                    if not pending_wake and not runtime_state.in_debounce():
                        tokens = normalize_tokens(text)
                        idx = find_phrase(tokens, wake_tokens)
                        if idx != -1:
                            # R1 (28/08 soir) : le garde de confiance s'applique
                            # dans TOUS les modes. Avant, sous grammaire
                            # restreinte, un final quelconque réveillait sans
                            # garde — et le chemin des partiels (supprimé
                            # ci-dessous) réveillait sur « active » seul.
                            conf = mean_confidence(words, idx, len(wake_tokens))
                            if conf >= conf_threshold:
                                try:
                                    recognizer.Reset()
                                except Exception:
                                    pass
                                request_wake()
                    clear_partial()
                    continue

                if state == STATE_DICTATING and text and not pending_stop:
                    try:
                        text_queue.put_nowait((text, words))
                    except queue.Full:
                        print(f"\n{config.color_error}"
                              f"{_('Text queue full; the UI thread is not consuming. Dropping a result.')}"
                              f"{config.RESET}")
                    clear_partial()
            else:
                partial_dict = json.loads(recognizer.PartialResult())
                consecutive_decode_errors = 0
                partial_text = partial_dict.get("partial", "").strip()

                # R1 (28/08 soir) : plus de réveil sur les partiels. La
                # grammaire restreinte force la phrase de réveil sur de l'audio
                # ambigu (« active » seul réveillait la dictée) et aucun garde
                # de confiance n'existe sur un partiel. Le réveil se fait
                # uniquement sur un final avec confiance (bloc ci-dessus).

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
            # Chantier stabilité v0.5.1, défaut 1 (révision 09/09 soir). Une
            # erreur sur une trame — au premier chef une json.JSONDecodeError sur
            # Result()/PartialResult() — ne termine plus le décodage. On
            # reconstruit le recognizer : Reset() seul s'est montré sans effet
            # sur `ada` (erreur à chaque trame). Si les échecs s'enchaînent
            # au-delà de DECODE_ERROR_MAX_CONSECUTIVE, la reconstruction ne
            # rétablit rien : on pose stop_event et on termine la session
            # proprement plutôt que de boucler à vide. Tout décodage réussi a
            # remis consecutive_decode_errors à zéro plus haut.
            clear_partial()
            consecutive_decode_errors += 1

            if isinstance(e, json.JSONDecodeError) and not malformed_result_captured:
                malformed_result_captured = True
                raw = getattr(e, "doc", "") or ""
                path = _capture_malformed_result(raw)
                where = f" — {path}" if path else ""
                print(f"\n{config.color_error}"
                      f"{_('Malformed decoder output captured:')} {raw[:200]!r}{where}"
                      f"{config.RESET}")

            now = time.monotonic()
            if now - last_decode_error_warning >= DECODE_ERROR_THROTTLE_S:
                last_decode_error_warning = now
                print(f"\n{config.color_error}"
                      f"{_('Recognition error on a frame (recovering):')} {e}"
                      f"{config.RESET}")

            if consecutive_decode_errors >= DECODE_ERROR_MAX_CONSECUTIVE:
                print(f"\n{config.color_error}"
                      f"{_('The recognition engine is not recovering; ending the session. Please restart the tool.')}"
                      f"{config.RESET}")
                stop_event.set()
                break

            try:
                recognizer = build_recognizer(model, current_mode or MODE_FULL)
            except Exception:
                try:
                    recognizer.Reset()
                except Exception:
                    pass
            if stop_rec is not None:
                try:
                    stop_rec = build_recognizer(model, MODE_STOP)
                except Exception:
                    pass
            continue

    clear_partial()
