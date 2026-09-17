# Mode interaction.mode = maintenue (appui-pour-parler).
#
# GlobalHotKeys ne rend jamais le relâchement d'une touche ; un second listener
# pynput bas niveau (on_press/on_release) le fait, actif uniquement en mode
# maintenue, avec garde anti-répétition tant que la touche reste enfoncée.
# Aucun serveur X réel n'est requis : `pynput.keyboard` est remplacé par un
# double dont les callbacks sont invoqués directement par le test.

import queue
import sys
import threading
import types

import pytest

from config.config import config
from src import keyboard_listener


class FakeKey:
    ctrl_r = object()
    ctrl_l = object()


class FakeKeyCode:
    def __init__(self, char):
        self.char = char

    def __eq__(self, other):
        return isinstance(other, FakeKeyCode) and other.char == self.char

    def __hash__(self):
        return hash(self.char)

    @classmethod
    def from_char(cls, c):
        return cls(c)


class FakeGlobalHotKeys:
    def __init__(self, mapping):
        self.mapping = mapping

    def start(self):
        pass

    def stop(self):
        pass


class FakeListener:
    instances = []

    def __init__(self, on_press=None, on_release=None):
        self.on_press = on_press
        self.on_release = on_release
        self.started = False
        self.stopped = False
        FakeListener.instances.append(self)

    def start(self):
        self.started = True

    def stop(self):
        self.stopped = True


@pytest.fixture(autouse=True)
def _reset(monkeypatch):
    FakeListener.instances = []
    monkeypatch.setattr(keyboard_listener, "get_translation", lambda: (lambda s: s))
    yield


@pytest.fixture
def fake_pynput(monkeypatch):
    mod = types.ModuleType("pynput.keyboard")
    mod.GlobalHotKeys = FakeGlobalHotKeys
    mod.Key = FakeKey
    mod.KeyCode = FakeKeyCode
    mod.Listener = FakeListener
    pkg = types.ModuleType("pynput")
    pkg.keyboard = mod
    monkeypatch.setitem(sys.modules, "pynput", pkg)
    monkeypatch.setitem(sys.modules, "pynput.keyboard", mod)
    return mod


def run_listener(monkeypatch, control_queue, *, mode, push_to_talk=None):
    monkeypatch.setenv("DISPLAY", ":0")
    monkeypatch.setenv("XDG_SESSION_TYPE", "x11")
    block = {
        "pynput_enabled": True,
        "toggle_recording": {"pynput_keys": ["alt_l", "h"]},
    }
    if push_to_talk is not None:
        block["push_to_talk"] = push_to_talk
    monkeypatch.setitem(config.data, "hotkeys", block)
    monkeypatch.setitem(config.data.setdefault("interaction", {}), "mode", mode)

    stop_event = threading.Event()
    stop_event.set()  # les deux listeners tournent en tâche de fond ; on arrête tout de suite
    keyboard_listener.keyboard_listener_thread(control_queue, stop_event)


def _drain(q):
    out = []
    try:
        while True:
            out.append(q.get_nowait())
    except queue.Empty:
        pass
    return out


def test_toggle_mode_never_starts_push_to_talk_listener(monkeypatch, fake_pynput):
    run_listener(monkeypatch, queue.Queue(), mode="toggle", push_to_talk="ctrl_r")
    assert FakeListener.instances == []


def test_maintenue_mode_starts_and_stops_push_to_talk_listener(monkeypatch, fake_pynput):
    run_listener(monkeypatch, queue.Queue(), mode="maintenue", push_to_talk="ctrl_r")
    assert len(FakeListener.instances) == 1
    listener = FakeListener.instances[0]
    assert listener.started and listener.stopped


def test_press_then_release_starts_and_finalizes(monkeypatch, fake_pynput):
    ctrl = queue.Queue()
    run_listener(monkeypatch, ctrl, mode="maintenue", push_to_talk="ctrl_r")
    listener = FakeListener.instances[0]

    listener.on_press(FakeKey.ctrl_r)
    listener.on_release(FakeKey.ctrl_r)

    assert _drain(ctrl) == ["DICTATION_ON", "FINALIZE_SESSION"]


def test_held_key_does_not_repeat_dictation_on(monkeypatch, fake_pynput):
    """Garde anti-répétition : l'OS peut renvoyer plusieurs on_press pour une
    touche maintenue (auto-répétition clavier) ; un seul DICTATION_ON doit en
    sortir tant qu'elle n'a pas été relâchée."""
    ctrl = queue.Queue()
    run_listener(monkeypatch, ctrl, mode="maintenue", push_to_talk="ctrl_r")
    listener = FakeListener.instances[0]

    listener.on_press(FakeKey.ctrl_r)
    listener.on_press(FakeKey.ctrl_r)
    listener.on_press(FakeKey.ctrl_r)
    listener.on_release(FakeKey.ctrl_r)

    assert _drain(ctrl) == ["DICTATION_ON", "FINALIZE_SESSION"]


def test_other_keys_are_ignored(monkeypatch, fake_pynput):
    ctrl = queue.Queue()
    run_listener(monkeypatch, ctrl, mode="maintenue", push_to_talk="ctrl_r")
    listener = FakeListener.instances[0]

    listener.on_press(FakeKey.ctrl_l)
    listener.on_release(FakeKey.ctrl_l)

    assert _drain(ctrl) == []


def test_single_character_key_resolves_via_keycode(monkeypatch, fake_pynput):
    ctrl = queue.Queue()
    run_listener(monkeypatch, ctrl, mode="maintenue", push_to_talk="a")
    listener = FakeListener.instances[0]

    listener.on_press(FakeKeyCode.from_char("a"))
    listener.on_release(FakeKeyCode.from_char("a"))

    assert _drain(ctrl) == ["DICTATION_ON", "FINALIZE_SESSION"]


def test_missing_push_to_talk_key_disables_listener_with_warning(monkeypatch, fake_pynput, capsys):
    run_listener(monkeypatch, queue.Queue(), mode="maintenue", push_to_talk=None)
    assert FakeListener.instances == []
    assert "push_to_talk" in capsys.readouterr().out


def test_invalid_push_to_talk_key_disables_listener_with_warning(monkeypatch, fake_pynput, capsys):
    # Ni un membre de Key, ni un caractère unique -> aucune clé ne peut en sortir.
    run_listener(monkeypatch, queue.Queue(), mode="maintenue", push_to_talk="not-a-key")
    assert FakeListener.instances == []
    assert "push_to_talk" in capsys.readouterr().out
