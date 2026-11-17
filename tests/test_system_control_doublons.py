# Signal sonore sans attente, collage X11, classe de fenêtre, avis XWayland.

import subprocess
import time

import pyperclip

import src.system_control as sc


class SlowChild:
    def wait(self):
        time.sleep(0.3)


def test_play_sound_does_not_block(monkeypatch):
    monkeypatch.setattr(sc, "check_command_exists", lambda name: True)
    monkeypatch.setattr(type(sc.config), "sound_file", property(lambda self: "/x.wav"))
    monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: SlowChild())
    start = time.monotonic()
    sc.play_sound()
    assert time.monotonic() - start < 0.05


def test_play_sound_without_paplay_returns(monkeypatch):
    monkeypatch.setattr(sc, "check_command_exists", lambda name: False)
    sc.play_sound()


def test_x11_clipboard_tool_prefers_xclip(monkeypatch):
    chosen = []
    monkeypatch.setattr(sc, "_x11_clipboard_tool_chosen", False)
    monkeypatch.setattr(sc, "check_command_exists", lambda name: True)
    monkeypatch.setattr(pyperclip, "set_clipboard", chosen.append)
    sc._choose_x11_clipboard_tool({"session": "x11"})
    sc._choose_x11_clipboard_tool({"session": "x11"})
    assert chosen == ["xclip"]


def test_x11_clipboard_tool_falls_back_to_xsel(monkeypatch):
    chosen = []
    monkeypatch.setattr(sc, "_x11_clipboard_tool_chosen", False)
    monkeypatch.setattr(sc, "check_command_exists", lambda name: name == "xsel")
    monkeypatch.setattr(pyperclip, "set_clipboard", chosen.append)
    sc._choose_x11_clipboard_tool({"session": "x11"})
    assert chosen == ["xsel"]


def test_x11_clipboard_tool_untouched_on_wayland(monkeypatch):
    chosen = []
    monkeypatch.setattr(sc, "_x11_clipboard_tool_chosen", False)
    monkeypatch.setattr(pyperclip, "set_clipboard", chosen.append)
    sc._choose_x11_clipboard_tool({"session": "wayland"})
    assert chosen == []


def test_window_class_falls_back_to_xprop(monkeypatch):
    def fake_run(cmd, timeout, stdin_text=None):
        if "getwindowclassname" in cmd:
            return False, ""
        if cmd[:2] == ["xdotool", "getactivewindow"]:
            return True, "42\n"
        if cmd[0] == "xprop":
            return True, 'WM_CLASS(STRING) = "xterm", "XTerm"\n'
        return False, ""

    monkeypatch.setattr(sc, "_run", fake_run)
    monkeypatch.setattr(sc, "check_command_exists", lambda name: True)
    assert sc._active_window_class_x11() == "XTerm"


def test_injection_limited_to_xwayland(monkeypatch):
    for session, backend, expected in (
        ("wayland", "xdotool", True),
        ("wayland", "wtype", False),
        ("x11", "xdotool", False),
    ):
        monkeypatch.setattr(
            sc,
            "_detect_caps",
            lambda s=session, b=backend: {"session": s, "key_backend": b},
        )
        assert sc.injection_limited_to_xwayland() is expected
