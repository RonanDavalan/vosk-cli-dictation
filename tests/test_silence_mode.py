# Mode interaction.mode = silence : la boucle de reconnaissance pousse
# elle-même FINALIZE_SESSION quand aucun résultat non vide (partiel ou final)
# n'est arrivé depuis silence_timeout_ms, une fois qu'au moins un mot a été
# capté dans la session en cours.
#
# Même harnais que test_recognition_semantics.py (FakeRec rejoue un script,
# aucun modèle Vosk requis) ; horloge réelle, délais en millisecondes tenus
# très courts pour que le test reste rapide.

import queue
import threading
import time

import src.recognition as rec
from config.config import config
from src.recognition import MODE_STOP
from src.runtime_state import runtime_state, STATE_DICTATING


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
            self.step = ("partial", {"partial": ""})  # silence une fois le script épuisé
        return self.step[0] == "final"

    def Result(self):
        return json_dumps(self.step[1])

    def PartialResult(self):
        return json_dumps(self.step[1])

    def Reset(self):
        self.reset_calls += 1

    def SetWords(self, flag):
        pass


def json_dumps(d):
    import json
    return json.dumps(d)


def _run_silence(monkeypatch, script, *, mode, timeout_ms, run_s=0.4):
    monkeypatch.setitem(config.data.setdefault("interaction", {}), "mode", mode)
    monkeypatch.setitem(config.data["interaction"], "silence_timeout_ms", timeout_ms)
    monkeypatch.delitem(config.language_settings["fr"], "silence_timeout_ms", raising=False)
    config.set_language("fr")

    fake = FakeRec(script)
    fake_stop = FakeRec([])
    monkeypatch.setattr(
        rec, "build_recognizer",
        lambda model, m: fake_stop if m == MODE_STOP else fake,
    )
    monkeypatch.setitem(config.language_settings["fr"], "restricted_stop_in_dictation", False)

    audio_q = queue.Queue(maxsize=256)
    text_q = queue.Queue(maxsize=256)
    ctrl_q = queue.Queue(maxsize=32)
    stop = threading.Event()
    display = threading.Event()
    display.set()
    wake = threading.Event()
    wake.set()

    runtime_state.set_state(STATE_DICTATING)
    runtime_state._last_transition = 0.0

    # Un flux continu de blocs "audio" : assez pour couvrir run_s au rythme du
    # thread (queue.get(timeout=0.1) et boucle serrée entre les items).
    for _ in range(2000):
        try:
            audio_q.put_nowait(b"\x00\x00")
        except queue.Full:
            break

    t = threading.Thread(
        target=rec.recognition_thread,
        args=(object(), fake, audio_q, text_q, ctrl_q, stop, display, wake),
        daemon=True,
    )
    t.start()
    time.sleep(run_s)
    stop.set()
    wake.set()
    t.join(timeout=2.0)
    return ctrl_q, text_q


def _drain(q):
    out = []
    try:
        while True:
            out.append(q.get_nowait())
    except queue.Empty:
        pass
    return out


def test_silence_mode_finalizes_after_timeout_once_a_word_was_captured(monkeypatch):
    script = [("final", {"text": "bonjour", "result": [{"word": "bonjour", "conf": 0.9}]})]
    ctrl, _text = _run_silence(monkeypatch, script, mode="silence", timeout_ms=50)
    assert "FINALIZE_SESSION" in _drain(ctrl)


def test_silence_mode_does_not_finalize_an_empty_session(monkeypatch):
    # Aucun mot capté -> une hésitation avant de parler ne doit pas finaliser
    # une session vide (cas écarté explicitement).
    ctrl, _text = _run_silence(monkeypatch, [], mode="silence", timeout_ms=50)
    assert "FINALIZE_SESSION" not in _drain(ctrl)


def test_toggle_mode_never_auto_finalizes_on_silence(monkeypatch):
    # Non-régression : le mode par défaut ne doit jamais finaliser tout seul.
    script = [("final", {"text": "bonjour", "result": [{"word": "bonjour", "conf": 0.9}]})]
    ctrl, _text = _run_silence(monkeypatch, script, mode="toggle", timeout_ms=50)
    assert "FINALIZE_SESSION" not in _drain(ctrl)


def test_maintenue_mode_never_auto_finalizes_on_silence(monkeypatch):
    script = [("final", {"text": "bonjour", "result": [{"word": "bonjour", "conf": 0.9}]})]
    ctrl, _text = _run_silence(monkeypatch, script, mode="maintenue", timeout_ms=50)
    assert "FINALIZE_SESSION" not in _drain(ctrl)


def test_silence_mode_does_not_finalize_before_timeout(monkeypatch):
    # Délai généreux : sur la courte durée du test, le minuteur n'a pas le
    # temps d'expirer -- un silence court en cours de phrase ne finalise pas.
    script = [("final", {"text": "bonjour", "result": [{"word": "bonjour", "conf": 0.9}]})]
    ctrl, _text = _run_silence(monkeypatch, script, mode="silence", timeout_ms=60_000, run_s=0.2)
    assert "FINALIZE_SESSION" not in _drain(ctrl)
