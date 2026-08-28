# Chantier 7 bis — la phrase d'arrêt sous le seuil de confiance est ABSORBÉE
# (ni tapée, ni finalisée) au lieu d'être écrite dans le document.

import queue
import threading
import time

import pytest

import src.ui as ui
from config.config import config
from src.text_processing import TextProcessor
from src.runtime_state import runtime_state, STATE_LISTENING


@pytest.fixture
def harness(monkeypatch):
    typed = []
    copied = []
    monkeypatch.setattr(ui, "type_text", lambda s: (typed.append(s), True)[1])
    monkeypatch.setattr(ui, "press_key", lambda *a, **k: True)
    monkeypatch.setattr(ui, "play_sound", lambda: None)

    class _Clip:
        @staticmethod
        def copy(text):
            copied.append(text)

    monkeypatch.setattr(ui, "pyperclip", _Clip)
    config.set_language("fr")

    text_q = queue.Queue(maxsize=64)
    ctrl_q = queue.Queue(maxsize=32)
    stop = threading.Event()
    display = threading.Event()
    sleep_ev = threading.Event()
    wake_ev = threading.Event()
    wake_ev.set()
    processor = TextProcessor(config.current_lang)

    t = threading.Thread(
        target=ui.ui_thread,
        args=(text_q, ctrl_q, stop, processor, display, sleep_ev, wake_ev),
        daemon=True,
    )
    t.start()
    ctrl_q.put_nowait("DICTATION_ON")
    time.sleep(0.6)  # démarre l'enregistrement + purge la fenêtre d'anti-rebond
    runtime_state._last_transition = 0.0

    yield text_q, ctrl_q, typed, copied

    stop.set()
    t.join(timeout=2.0)


def _joined(chunks):
    return "".join(chunks)


def test_low_confidence_stop_phrase_is_not_typed(harness):
    text_q, _ctrl, typed, copied = harness
    low = [{"word": "stop", "conf": 0.2}, {"word": "dictée", "conf": 0.2}]
    text_q.put_nowait(("stop dictée", low))
    time.sleep(0.3)
    assert "stop" not in _joined(typed).lower()
    assert "dictée" not in _joined(typed).lower()
    assert copied == []  # pas de finalisation


def test_high_confidence_stop_phrase_finalizes(harness):
    text_q, _ctrl, typed, copied = harness
    text_q.put_nowait(("bonjour", [{"word": "bonjour", "conf": 0.95}]))
    time.sleep(0.15)
    high = [{"word": "stop", "conf": 0.97}, {"word": "dictée", "conf": 0.96}]
    text_q.put_nowait(("stop dictée", high))
    time.sleep(0.3)
    assert "bonjour" in _joined(copied).lower()  # finalize_session a copié le tampon
    assert "stop" not in _joined(copied).lower()


def test_text_before_low_confidence_stop_is_kept(harness):
    text_q, _ctrl, typed, copied = harness
    low = [
        {"word": "bonjour", "conf": 0.95},
        {"word": "stop", "conf": 0.2},
        {"word": "dictée", "conf": 0.2},
    ]
    text_q.put_nowait(("bonjour stop dictée", low))
    time.sleep(0.3)
    assert "bonjour" in _joined(typed).lower()
    assert "stop" not in _joined(typed).lower()
    assert copied == []
