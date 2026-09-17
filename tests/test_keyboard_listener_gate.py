# Garde de démarrage du listener pynput (COMPATIBILITE_WAYLAND.md §5). Le garde
# `XDG_SESSION_TYPE == "x11"` est retiré : le listener est un confort
# best-effort qui démarre dès qu'un serveur X est joignable, sur tout type de
# session, et se tait si `DISPLAY` est absent, si `hotkeys.pynput_enabled` est
# false, ou si le backend pynput est indisponible.
#
# Ces tests couvrent la matrice (DISPLAY présent/absent × XDG_SESSION_TYPE ×
# pynput_enabled × backend disponible/cassé) sans serveur X réel : le module
# `pynput.keyboard` est remplacé par un double.

import queue
import sys
import threading
import types

import pytest

from config.config import config
from src import keyboard_listener


class FakeKey:
    """Double minimal de `pynput.keyboard.Key` : quelques membres fixes, comme
    la véritable énumération — un nom absent lève AttributeError, exactement
    le signal dont `_parse_single_key` a besoin pour retomber sur
    KeyCode.from_char."""
    ctrl_r = object()
    ctrl_l = object()
    f9 = object()


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


class FakeListener:
    """Double de `pynput.keyboard.Listener` (mode appui-pour-parler) : ne se
    connecte à aucun serveur X, garde les callbacks accessibles pour que les
    tests les invoquent directement."""

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


class FakeGlobalHotKeys:
    """Double de `pynput.keyboard.GlobalHotKeys` : n'ouvre aucune connexion X."""

    instances = []
    raise_on_init = False

    def __init__(self, mapping):
        if FakeGlobalHotKeys.raise_on_init:
            raise RuntimeError("no X server")
        self.mapping = mapping
        self.started = False
        self.stopped = False
        FakeGlobalHotKeys.instances.append(self)

    def start(self):
        self.started = True

    def stop(self):
        self.stopped = True


@pytest.fixture(autouse=True)
def _reset_fake(monkeypatch):
    FakeGlobalHotKeys.instances = []
    FakeGlobalHotKeys.raise_on_init = False
    FakeListener.instances = []
    # `src.i18n._` est un état global : un test antérieur peut l'avoir bascule
    # dans une autre langue. On assertionne sur les msgid anglais, donc on
    # neutralise la traduction pour ce module.
    monkeypatch.setattr(keyboard_listener, "get_translation", lambda: (lambda s: s))
    yield


@pytest.fixture
def fake_pynput(monkeypatch):
    """Un `pynput.keyboard` synthétique qui expose `FakeGlobalHotKeys`."""
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


@pytest.fixture
def broken_pynput(monkeypatch):
    """Un `pynput.keyboard` sans `GlobalHotKeys` : l'import échoue dans le thread."""
    mod = types.ModuleType("pynput.keyboard")
    pkg = types.ModuleType("pynput")
    pkg.keyboard = mod
    monkeypatch.setitem(sys.modules, "pynput", pkg)
    monkeypatch.setitem(sys.modules, "pynput.keyboard", mod)
    return mod


@pytest.fixture
def hotkeys(monkeypatch):
    """Bloc `hotkeys` minimal et valide ; `pynput_enabled` ajusté par test."""
    block = {
        "pynput_enabled": True,
        "toggle_recording": {"pynput_keys": ["alt_l", "h"]},
    }
    monkeypatch.setitem(config.data, "hotkeys", block)
    return block


def run_listener(monkeypatch, *, display, session):
    """Lance le thread listener et rend la main aussitôt.

    Toutes les branches se terminent sur `stop_event.wait()` ; en armant
    l'événement avant l'appel, chacune retourne immédiatement.
    """
    if display is None:
        monkeypatch.delenv("DISPLAY", raising=False)
    else:
        monkeypatch.setenv("DISPLAY", display)
    if session is None:
        monkeypatch.delenv("XDG_SESSION_TYPE", raising=False)
    else:
        monkeypatch.setenv("XDG_SESSION_TYPE", session)

    stop_event = threading.Event()
    stop_event.set()
    keyboard_listener.keyboard_listener_thread(queue.Queue(), stop_event)


def test_disabled_by_config_never_starts(monkeypatch, capsys, fake_pynput, hotkeys):
    hotkeys["pynput_enabled"] = False
    run_listener(monkeypatch, display=":0", session="x11")
    assert FakeGlobalHotKeys.instances == []
    assert "disabled on this session" in capsys.readouterr().out


def test_no_display_never_starts(monkeypatch, capsys, fake_pynput, hotkeys):
    run_listener(monkeypatch, display=None, session="wayland")
    assert FakeGlobalHotKeys.instances == []
    assert "not available on this session" in capsys.readouterr().out


def test_x11_starts_without_xwayland_notice(monkeypatch, capsys, fake_pynput, hotkeys):
    run_listener(monkeypatch, display=":0", session="x11")
    assert len(FakeGlobalHotKeys.instances) == 1
    started = FakeGlobalHotKeys.instances[0]
    assert started.started and started.stopped
    out = capsys.readouterr().out
    assert "XWayland" not in out


def test_wayland_with_display_starts_best_effort_with_notice(monkeypatch, capsys, fake_pynput, hotkeys):
    run_listener(monkeypatch, display=":0", session="wayland")
    assert len(FakeGlobalHotKeys.instances) == 1
    assert "XWayland" in capsys.readouterr().out


def test_unknown_session_with_display_starts_with_notice(monkeypatch, capsys, fake_pynput, hotkeys):
    run_listener(monkeypatch, display=":0", session=None)
    assert len(FakeGlobalHotKeys.instances) == 1
    assert "XWayland" in capsys.readouterr().out


def test_backend_import_failure_is_survived(monkeypatch, capsys, broken_pynput, hotkeys):
    run_listener(monkeypatch, display=":0", session="x11")
    out = capsys.readouterr().out
    assert "not available on this session" in out


def test_backend_start_failure_is_survived(monkeypatch, capsys, fake_pynput, hotkeys):
    FakeGlobalHotKeys.raise_on_init = True
    run_listener(monkeypatch, display=":0", session="x11")
    assert FakeGlobalHotKeys.instances == []
    assert "not available on this session" in capsys.readouterr().out
