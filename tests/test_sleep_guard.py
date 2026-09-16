# Chantier stabilité v0.5.1, défaut 3 — on ne peut plus ouvrir une DICTÉE
# fantôme en VEILLE : toute demande de dictée (TOGGLE_RECORDING, DICTATION_ON,
# /nl) sort d'abord de veille, puis démarre. Plus un retour périodique honnête
# tant que la VEILLE dure.

import queue
import threading
import time

import pytest

import src.ui as ui
from config.config import config
from src.i18n import set_ui_language
from src.text_processing import TextProcessor
from src.runtime_state import (
    runtime_state, STATE_LISTENING, STATE_DICTATING, STATE_SLEEPING,
)


def _mk_thread(monkeypatch):
    monkeypatch.setattr(ui, "type_text", lambda s: True)
    monkeypatch.setattr(ui, "press_key", lambda *a, **k: True)
    monkeypatch.setattr(ui, "play_sound", lambda: None)

    class _Clip:
        @staticmethod
        def copy(text):
            pass

    monkeypatch.setattr(ui, "pyperclip", _Clip)
    config.set_language("fr")
    # Les assertions ci-dessous portent sur les msgid anglais ; src.i18n._ est
    # un état global partagé entre modules de test, pas garanti à l'anglais
    # sans cette fixation explicite (constaté au chantier 11).
    set_ui_language("en")

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
    return text_q, ctrl_q, stop, sleep_ev, wake_ev, t


@pytest.fixture
def sleeping(monkeypatch):
    """Un thread UI démarré, mis en VEILLE, prêt pour la demande de dictée."""
    text_q, ctrl_q, stop, sleep_ev, wake_ev, t = _mk_thread(monkeypatch)
    ctrl_q.put_nowait("SLEEP_ON")
    time.sleep(0.3)
    assert sleep_ev.is_set()
    assert not wake_ev.is_set()
    assert runtime_state.state == STATE_SLEEPING
    runtime_state._last_transition = 0.0

    yield text_q, ctrl_q, stop, sleep_ev, wake_ev

    stop.set()
    t.join(timeout=2.0)


def _assert_woke_into_dictation(sleep_ev, wake_ev):
    assert not sleep_ev.is_set()          # sorti de veille
    assert wake_ev.is_set()               # thread de reconnaissance débloqué
    assert runtime_state.state == STATE_DICTATING


def test_toggle_recording_in_sleep_wakes_then_dictates(sleeping):
    _text_q, ctrl_q, _stop, sleep_ev, wake_ev = sleeping
    ctrl_q.put_nowait("TOGGLE_RECORDING")
    time.sleep(0.3)
    _assert_woke_into_dictation(sleep_ev, wake_ev)


def test_dictation_on_in_sleep_wakes_then_dictates(sleeping):
    _text_q, ctrl_q, _stop, sleep_ev, wake_ev = sleeping
    ctrl_q.put_nowait("DICTATION_ON")
    time.sleep(0.3)
    _assert_woke_into_dictation(sleep_ev, wake_ev)


def test_nl_in_sleep_wakes_then_dictates(sleeping):
    _text_q, ctrl_q, _stop, sleep_ev, wake_ev = sleeping
    ctrl_q.put_nowait("/nl")
    time.sleep(0.3)
    _assert_woke_into_dictation(sleep_ev, wake_ev)


def test_periodic_reminder_cadence(monkeypatch, capfd):
    monkeypatch.setattr(ui, "SLEEP_REMINDER_INTERVAL_S", 0.15)
    _text_q, ctrl_q, stop, sleep_ev, _wake_ev, t = _mk_thread(monkeypatch)
    try:
        ctrl_q.put_nowait("SLEEP_ON")
        time.sleep(0.62)  # ~4 intervalles complets après l'entrée en VEILLE

        n = capfd.readouterr().out.count("wake to resume")
        # Émis à cadence fixe : quelques fois sur 0,6 s, jamais en rafale.
        assert 2 <= n <= 5

        # Réveil : le rappel cesse.
        ctrl_q.put_nowait("SLEEP_OFF")
        time.sleep(0.1)
        assert not sleep_ev.is_set()
        capfd.readouterr()
        time.sleep(0.4)
        assert capfd.readouterr().out.count("wake to resume") == 0
    finally:
        stop.set()
        t.join(timeout=2.0)
