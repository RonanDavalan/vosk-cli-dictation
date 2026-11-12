# Sous Wayland, le texte copié par pyperclip (GTK) reste illisible sans fenêtre : wl-copy le publie.
import src.system_control as sc


def _wayland(monkeypatch, read):
    monkeypatch.setattr(sc, "_detect_caps", lambda: {"session": "wayland", "wl_copy": True})
    monkeypatch.setattr(sc, "_clipboard_get", lambda: read)
    published = []
    monkeypatch.setattr(sc, "_clipboard_set", lambda text: published.append(text) or True)
    monkeypatch.setattr(sc, "_clipboard_confirm", lambda text, timeout_ms: True)
    return published


def test_unreadable_text_is_published_by_wl_copy(monkeypatch):
    published = _wayland(monkeypatch, "")
    assert sc.ensure_clipboard_text("bonjour") is True
    assert published == ["bonjour"]


def test_readable_text_is_left_alone(monkeypatch):
    published = _wayland(monkeypatch, "bonjour")
    assert sc.ensure_clipboard_text("bonjour") is True
    assert published == []


def test_x11_is_left_alone(monkeypatch):
    monkeypatch.setattr(sc, "_detect_caps", lambda: {"session": "x11", "wl_copy": True})
    monkeypatch.setattr(sc, "_clipboard_set", lambda text: (_ for _ in ()).throw(AssertionError("appelé")))
    assert sc.ensure_clipboard_text("bonjour") is True
