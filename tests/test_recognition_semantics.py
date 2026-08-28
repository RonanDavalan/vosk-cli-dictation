# Chantier 7 volet E/H — sémantique des commandes vocales dans le thread de
# reconnaissance : réveil sur les partiels sous grammaire restreinte, garde de
# confiance sur les finaux, anti-rebond, transmission du texte en DICTÉE.
#
# Le recognizer Vosk est remplacé par un faux qui rejoue un script de résultats,
# donc aucun modèle n'est requis.

import json
import queue
import threading
import time

import pytest

import src.recognition as rec
from config.config import config
from src.recognition import _target_mode, MODE_FULL, MODE_LISTENING, MODE_STOP
from src.runtime_state import (
    runtime_state, STATE_DICTATING, STATE_LISTENING, STATE_SLEEPING,
)


def test_target_mode_restricted_grammar_is_per_language():
    # Global défaut true, es le désactive (banc du 28/08).
    config.set_language("fr")
    assert _target_mode(STATE_LISTENING) == MODE_LISTENING
    config.set_language("en")
    assert _target_mode(STATE_LISTENING) == MODE_LISTENING
    config.set_language("de")
    assert _target_mode(STATE_LISTENING) == MODE_LISTENING
    config.set_language("es")
    assert _target_mode(STATE_LISTENING) == MODE_FULL
    # DICTÉE et VEILLE : toujours grammaire complète.
    for lang in ("fr", "es"):
        config.set_language(lang)
        assert _target_mode(STATE_DICTATING) == MODE_FULL
        assert _target_mode(STATE_SLEEPING) == MODE_FULL
    config.set_language("fr")


class FakeRec:
    def __init__(self, script):
        self.script = list(script)
        self.i = 0
        self.step = ("partial", {"partial": ""})
        self.reset_calls = 0

    def AcceptWaveform(self, data):
        if self.i < len(self.script):
            self.step = self.script[self.i]
            self.i += 1
        else:
            self.step = ("partial", {"partial": ""})
        return self.step[0] == "final"

    def Result(self):
        return json.dumps(self.step[1])

    def PartialResult(self):
        return json.dumps(self.step[1])

    def Reset(self):
        self.reset_calls += 1

    def SetWords(self, flag):
        pass


def _run_thread(script, state, monkeypatch, feed=None, stop_script=None):
    config.set_language("fr")
    fake = FakeRec(script)
    fake_stop = FakeRec(stop_script or [])
    fake.stop = fake_stop  # accès pour les tests du recognizer d'arrêt (7 bis)
    monkeypatch.setattr(
        rec, "build_recognizer",
        lambda model, mode: fake_stop if mode == MODE_STOP else fake,
    )

    audio_q = queue.Queue(maxsize=64)
    text_q = queue.Queue(maxsize=64)
    ctrl_q = queue.Queue(maxsize=32)
    stop = threading.Event()
    display = threading.Event()
    wake = threading.Event()
    wake.set()
    if state == STATE_DICTATING:
        display.set()

    runtime_state.set_state(state)
    # neutraliser l'anti-rebond hérité d'un test précédent
    runtime_state._last_transition = 0.0

    steps = feed if feed is not None else max(len(script), len(stop_script or []))
    for _ in range(steps + 2):
        audio_q.put_nowait(b"\x00\x00")

    t = threading.Thread(
        target=rec.recognition_thread,
        args=(object(), fake, audio_q, text_q, ctrl_q, stop, display, wake),
        daemon=True,
    )
    t.start()
    time.sleep(0.4)
    stop.set()
    wake.set()
    t.join(timeout=2.0)
    return text_q, ctrl_q, fake


def _drain(q):
    out = []
    try:
        while True:
            out.append(q.get_nowait())
    except queue.Empty:
        pass
    return out


def test_wake_phrase_on_partial_requests_dictation(monkeypatch):
    script = [("partial", {"partial": "active dictée"})]
    _text, ctrl, fake = _run_thread(script, STATE_LISTENING, monkeypatch)
    assert "DICTATION_ON" in _drain(ctrl)
    assert fake.reset_calls >= 1  # la phrase est retirée du flux


def test_isolated_words_do_not_wake(monkeypatch):
    script = [
        ("partial", {"partial": "active"}),
        ("partial", {"partial": "je reprends la dictée"}),
        ("final", {"text": "active la dictée maintenant", "result": []}),
    ]
    _text, ctrl, _fake = _run_thread(script, STATE_LISTENING, monkeypatch)
    assert "DICTATION_ON" not in _drain(ctrl)


def test_listening_final_swallows_text(monkeypatch):
    # En ÉCOUTE, un final qui n'est pas la phrase de réveil ne doit pas être tapé.
    script = [("final", {"text": "bla bla bla", "result": []})]
    text_q, ctrl, _fake = _run_thread(script, STATE_LISTENING, monkeypatch)
    assert _drain(text_q) == []
    assert "DICTATION_ON" not in _drain(ctrl)


def test_dictating_final_forwards_text_and_words(monkeypatch):
    words = [{"word": "bonjour", "conf": 0.98}]
    script = [("final", {"text": "bonjour", "result": words})]
    text_q, _ctrl, _fake = _run_thread(script, STATE_DICTATING, monkeypatch)
    items = _drain(text_q)
    assert items == [("bonjour", words)]


def test_wake_on_final_needs_confidence_when_grammar_is_full(monkeypatch):
    # grammaire complète en ÉCOUTE -> le garde de confiance s'applique.
    # On force le mode complet global ET pour fr (surcharge par langue).
    monkeypatch.setitem(config.data["recognition"], "restricted_grammar_in_listening", False)
    monkeypatch.setitem(config.language_settings["fr"], "restricted_grammar_in_listening", False)
    low = [{"word": "active", "conf": 0.30}, {"word": "dictée", "conf": 0.20}]
    script = [("final", {"text": "active dictée", "result": low})]
    _text, ctrl, _fake = _run_thread(script, STATE_LISTENING, monkeypatch)
    assert "DICTATION_ON" not in _drain(ctrl)

    high = [{"word": "active", "conf": 0.97}, {"word": "dictée", "conf": 0.95}]
    script = [("final", {"text": "active dictée", "result": high})]
    _text, ctrl, _fake = _run_thread(script, STATE_LISTENING, monkeypatch)
    assert "DICTATION_ON" in _drain(ctrl)


# --- chantier 7 bis : détecteur d'arrêt à grammaire restreinte en DICTÉE -----

def test_restricted_stop_recognizer_finalizes_on_final(monkeypatch):
    monkeypatch.setitem(config.language_settings["fr"], "restricted_stop_in_dictation", True)
    stop_script = [("final", {"text": "stop dictée", "result": []})]
    _text, ctrl, fake = _run_thread(
        [], STATE_DICTATING, monkeypatch, stop_script=stop_script
    )
    assert "FINALIZE_SESSION" in _drain(ctrl)
    assert fake.reset_calls >= 1  # le recognizer complet est réinitialisé


def test_restricted_stop_recognizer_ignores_partials(monkeypatch):
    # Conservateur (28/08) : un partiel « stop dictée » ne déclenche PAS —
    # les partiels sous grammaire restreinte sont instables.
    monkeypatch.setitem(config.language_settings["fr"], "restricted_stop_in_dictation", True)
    stop_script = [("partial", {"partial": "stop dictée"}),
                   ("partial", {"partial": "stop dictée"})]
    _text, ctrl, _fake = _run_thread(
        [], STATE_DICTATING, monkeypatch, stop_script=stop_script
    )
    assert "FINALIZE_SESSION" not in _drain(ctrl)


def test_restricted_stop_recognizer_ignores_low_confidence_final(monkeypatch):
    # Correspondance exacte mais confiance faible (match « forcé » sur audio
    # ambigu) -> pas de déclenchement.
    monkeypatch.setitem(config.language_settings["fr"], "restricted_stop_in_dictation", True)
    low = [{"word": "stop", "conf": 0.2}, {"word": "dictée", "conf": 0.2}]
    stop_script = [("final", {"text": "stop dictée", "result": low})]
    _text, ctrl, _fake = _run_thread(
        [], STATE_DICTATING, monkeypatch, stop_script=stop_script
    )
    assert "FINALIZE_SESSION" not in _drain(ctrl)


def test_restricted_stop_recognizer_ignores_phrase_with_extra_words(monkeypatch):
    # Le final doit être EXACTEMENT la phrase, pas la contenir.
    monkeypatch.setitem(config.language_settings["fr"], "restricted_stop_in_dictation", True)
    stop_script = [("final", {"text": "voilà stop dictée maintenant", "result": []})]
    _text, ctrl, _fake = _run_thread(
        [], STATE_DICTATING, monkeypatch, stop_script=stop_script
    )
    assert "FINALIZE_SESSION" not in _drain(ctrl)


def test_restricted_stop_recognizer_ignores_unk(monkeypatch):
    monkeypatch.setitem(config.language_settings["fr"], "restricted_stop_in_dictation", True)
    stop_script = [
        ("partial", {"partial": "bla bla"}),
        ("final", {"text": "", "result": []}),
    ]
    _text, ctrl, _fake = _run_thread(
        [], STATE_DICTATING, monkeypatch, stop_script=stop_script
    )
    assert "FINALIZE_SESSION" not in _drain(ctrl)


def test_restricted_stop_recognizer_off_per_language(monkeypatch):
    monkeypatch.setitem(
        config.language_settings["fr"], "restricted_stop_in_dictation", False
    )
    stop_script = [("final", {"text": "stop dictée", "result": []})]
    _text, ctrl, _fake = _run_thread(
        [], STATE_DICTATING, monkeypatch, stop_script=stop_script
    )
    assert "FINALIZE_SESSION" not in _drain(ctrl)


def test_restricted_stop_recognizer_absent_in_listening(monkeypatch):
    # En ÉCOUTE, aucun recognizer d'arrêt : « stop dictée » n'y finalise rien.
    stop_script = [("final", {"text": "stop dictée", "result": []})]
    _text, ctrl, _fake = _run_thread(
        [], STATE_LISTENING, monkeypatch, stop_script=stop_script
    )
    assert "FINALIZE_SESSION" not in _drain(ctrl)


def test_dictating_text_suppressed_while_stop_pending(monkeypatch):
    monkeypatch.setitem(config.language_settings["fr"], "restricted_stop_in_dictation", True)
    # Le recognizer d'arrêt matche au 1er bloc ; le final tardif du recognizer
    # complet contenant encore « stop dictée » ne doit pas être tapé.
    script = [
        ("partial", {"partial": "bonjour"}),
        ("final", {"text": "bonjour stop dictée", "result": []}),
    ]
    stop_script = [("final", {"text": "stop dictée", "result": []})]
    text_q, ctrl, _fake = _run_thread(
        script, STATE_DICTATING, monkeypatch, stop_script=stop_script, feed=6
    )
    assert "FINALIZE_SESSION" in _drain(ctrl)
    assert _drain(text_q) == []


# --- chantier 7 ter (T4) : fenêtre d'ignorance après le réveil -----------------

def test_wake_discard_window_drops_audio_buffered_before_transition(monkeypatch):
    """Après ÉCOUTE->DICTÉE, l'audio déjà en file (fin de « active dictée ») est
    jeté sans décodage ; aucun mot parasite n'est remonté."""
    config.set_language("fr")
    monkeypatch.setitem(config.data["recognition"], "wake_discard_ms", 300)

    # Le faux recognizer complet : chaque bloc produit un final « les » (ce qui,
    # sans la fenêtre T4, serait remonté au thread UI).
    full = FakeRec([("final", {"text": "les", "result": []})] * 50)
    monkeypatch.setattr(rec, "build_recognizer", lambda model, mode: full)

    audio_q = queue.Queue(maxsize=200)
    text_q = queue.Queue(maxsize=200)
    ctrl_q = queue.Queue(maxsize=32)
    stop = threading.Event()
    display = threading.Event()
    display.set()
    wake = threading.Event()
    wake.set()

    runtime_state.set_state(STATE_LISTENING)
    runtime_state._last_transition = 0.0

    t = threading.Thread(
        target=rec.recognition_thread,
        args=(object(), full, audio_q, text_q, ctrl_q, stop, display, wake),
        daemon=True,
    )
    t.start()
    time.sleep(0.05)
    # De l'audio arrive pendant qu'on est encore en ÉCOUTE (fin du réveil).
    for _ in range(20):
        audio_q.put_nowait(b"\x00\x00")
    # Bascule en DICTÉE : le thread doit vider la file et ouvrir la fenêtre.
    runtime_state.set_state(STATE_DICTATING)
    runtime_state._last_transition = 0.0
    # On alimente encore un peu pendant la fenêtre de 300 ms.
    for _ in range(10):
        audio_q.put_nowait(b"\x00\x00")
        time.sleep(0.01)
    time.sleep(0.15)  # toujours dans la fenêtre
    stop.set()
    t.join(timeout=2.0)

    assert _drain(text_q) == []  # rien remonté pendant la fenêtre
