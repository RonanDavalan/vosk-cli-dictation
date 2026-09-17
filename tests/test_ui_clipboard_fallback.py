# finalize_session() ne tue plus le thread UI quand pyperclip.copy lève
# (SSH nu, pas de presse-papiers) : le texte est imprimé sur stdout, l'état
# repasse en ÉCOUTE, le thread survit.

import queue
import threading
import time

import pytest

import src.ui as ui
from config.config import config
from src.i18n import set_ui_language
from src.text_processing import TextProcessor
from src.runtime_state import runtime_state, STATE_LISTENING, STATE_DICTATING


class _BrokenClip:
    """pyperclip sans presse-papiers accessible."""

    @staticmethod
    def copy(text):
        raise RuntimeError("Pyperclip could not find a copy/paste mechanism")

    @staticmethod
    def paste():
        raise RuntimeError("Pyperclip could not find a copy/paste mechanism")


@pytest.fixture
def harness(monkeypatch):
    typed = []
    monkeypatch.setattr(ui, "type_text", lambda s: (typed.append(s), True)[1])
    monkeypatch.setattr(ui, "press_key", lambda *a, **k: True)
    monkeypatch.setattr(ui, "play_sound", lambda: None)
    monkeypatch.setattr(ui, "pyperclip", _BrokenClip)
    config.set_language("fr")
    # Les assertions ci-dessous portent sur les msgid anglais ; src.i18n._ est
    # un état global partagé entre modules de test, pas garanti à l'anglais
    # sans cette fixation explicite.
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
    ctrl_q.put_nowait("DICTATION_ON")
    time.sleep(0.5)
    runtime_state._last_transition = 0.0

    yield text_q, ctrl_q, stop, t, typed

    stop.set()
    t.join(timeout=2.0)


def test_finalize_survives_missing_clipboard(harness, capfd):
    text_q, ctrl_q, stop, thread, _typed = harness

    text_q.put_nowait(("bonjour le monde", [{"word": "bonjour", "conf": 0.95}]))
    time.sleep(0.2)
    capfd.readouterr()  # on ne garde que ce qui suit la finalisation

    ctrl_q.put_nowait("FINALIZE_SESSION")
    time.sleep(0.3)

    out = capfd.readouterr().out
    # Aucune exception n'a traversé : le thread est toujours vivant.
    assert thread.is_alive()
    assert not stop.is_set()
    # Le texte de session est rendu sur stdout, précédé d'un message clair.
    assert "Clipboard unavailable" in out
    assert "bonjour le monde" in out.lower()
    # L'état est bien repassé en ÉCOUTE.
    assert runtime_state.state == STATE_LISTENING


def test_thread_still_responds_after_clipboard_failure(harness):
    text_q, ctrl_q, stop, thread, _typed = harness

    text_q.put_nowait(("un texte", [{"word": "un", "conf": 0.95}]))
    time.sleep(0.2)
    ctrl_q.put_nowait("FINALIZE_SESSION")
    time.sleep(0.3)

    # Une nouvelle commande passe encore : la boucle du thread tourne toujours.
    ctrl_q.put_nowait("DICTATION_ON")
    time.sleep(0.3)
    assert thread.is_alive()
    assert runtime_state.state == STATE_DICTATING
