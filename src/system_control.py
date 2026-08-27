# src/system_control.py
#
# Injection de texte et de touches dans la fenêtre active, plus retours sonores.
#
# Chantier 7 volet B — durcissement :
#   - `timeout=` sur tous les sous-processus : un backend figé ne fige plus l'UI.
#   - round-trip presse-papiers confirmé (relecture) avant le collage, délai de
#     restauration paramétrable, presse-papiers non textuel préservé (non écrasé
#     en silence, non restauré, averti).
#   - backend choisi par type de session : X11 → xdotool ; Wayland → wtype
#     (frappe par keysym, règle Dvorak/Bépo) + wl-clipboard, repli ydotool
#     (keycodes physiques), puis mode dégradé console.
#   - combo de collage adapté à la cible (Ctrl+Shift+V dans les terminaux).

import os
import subprocess
import time
import shutil

import pyperclip

from config.config import config
from src.i18n import get_translation

# Keycodes physiques Linux (repli ydotool uniquement — dépendants de la
# disposition clavier, d'où la préférence pour wtype qui parle keysyms).
KEYCODE = {'ctrl': 29, 'shift': 42, 'v': 47, 'BackSpace': 14}

_KEY_TIMEOUT = 2.0
_CLIP_TIMEOUT = 2.0
_SOUND_TIMEOUT = 5.0

_caps = None          # capacités détectées (session + outils), calculées une fois
_last_warn = 0.0


# --------------------------------------------------------------------------- #
# Détection de l'environnement                                                #
# --------------------------------------------------------------------------- #

def check_command_exists(command: str) -> bool:
    """Checks if an external command is available in the system's PATH."""
    return shutil.which(command) is not None


def _session_type() -> str:
    st = (os.environ.get("XDG_SESSION_TYPE") or "").lower()
    if st in ("wayland", "x11"):
        return st
    if os.environ.get("WAYLAND_DISPLAY"):
        return "wayland"
    if os.environ.get("DISPLAY"):
        return "x11"
    return "unknown"


def _ydotool_ready() -> bool:
    """ydotool présent ET démon joignable (test non destructif `key 0:0`)."""
    if not check_command_exists("ydotool"):
        return False
    try:
        subprocess.run(["ydotool", "key", "0:0"], check=True,
                       capture_output=True, text=True, timeout=_KEY_TIMEOUT)
        return True
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        return False


def _detect_caps() -> dict:
    global _caps
    if _caps is not None:
        return _caps
    session = _session_type()
    _caps = {
        "session": session,
        "xdotool": check_command_exists("xdotool"),
        "wtype": check_command_exists("wtype"),
        "wl_copy": check_command_exists("wl-copy"),
        "wl_paste": check_command_exists("wl-paste"),
        "xclip": check_command_exists("xclip"),
        "ydotool": _ydotool_ready(),
    }
    # Backend de frappe retenu : wtype (Wayland) > ydotool > xdotool.
    if session == "wayland" and _caps["wtype"]:
        _caps["key_backend"] = "wtype"
    elif session == "wayland" and _caps["ydotool"]:
        _caps["key_backend"] = "ydotool"
    elif _caps["xdotool"]:
        _caps["key_backend"] = "xdotool"
    elif _caps["ydotool"]:
        _caps["key_backend"] = "ydotool"
    elif _caps["wtype"]:
        _caps["key_backend"] = "wtype"
    else:
        _caps["key_backend"] = None
    return _caps


def injection_backend_available() -> bool:
    """Vrai si au moins un backend de frappe est utilisable pour cette session."""
    return _detect_caps()["key_backend"] is not None


def ydotool_disponible() -> bool:
    """Compat : conservé pour un appelant historique. Voir _detect_caps()."""
    return _detect_caps()["ydotool"]


# --------------------------------------------------------------------------- #
# Utilitaires                                                                 #
# --------------------------------------------------------------------------- #

def _warn(msg: str):
    """Avertissement throttlé (au plus un par seconde) sur stderr coloré."""
    global _last_warn
    now = time.monotonic()
    if now - _last_warn >= 1.0:
        _last_warn = now
        print(f"\n{config.color_warning}{msg}{config.RESET}")


def _run(cmd, timeout, stdin_text=None):
    """Lance un sous-processus borné. Retourne (ok, stdout). Ne lève jamais."""
    _ = get_translation()
    try:
        r = subprocess.run(
            cmd, input=stdin_text, capture_output=True, text=True,
            timeout=timeout, check=True,
        )
        return True, r.stdout
    except subprocess.TimeoutExpired:
        _warn(_("'{tool}' timed out; falling back.").format(tool=cmd[0]))
        return False, ""
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return False, ""


def _cfg(section, key, default):
    return config.data.get(section, {}).get(key, default)


def _parse_combo(combo: str):
    """'ctrl+shift+v' -> (['ctrl', 'shift'], 'v')."""
    parts = [p.strip().lower() for p in combo.split("+") if p.strip()]
    if not parts:
        return [], "v"
    return parts[:-1], parts[-1]


# --------------------------------------------------------------------------- #
# Presse-papiers                                                              #
# --------------------------------------------------------------------------- #

def _clipboard_is_text() -> bool:
    """Faux si le presse-papiers tient un contenu non textuel (image, fichier)."""
    caps = _detect_caps()
    if caps["session"] == "wayland" and caps["wl_paste"]:
        ok, out = _run(["wl-paste", "--list-types"], _CLIP_TIMEOUT)
        if ok:
            return any(t.startswith("text/") or "STRING" in t for t in out.split())
        return True  # presse-papiers vide -> wl-paste échoue ; rien à préserver
    if caps["xclip"]:
        ok, out = _run(["xclip", "-selection", "clipboard", "-o", "-t", "TARGETS"],
                       _CLIP_TIMEOUT)
        if ok:
            return any(t in out for t in ("UTF8_STRING", "STRING", "text/plain",
                                          "TEXT"))
        return True
    return True  # pas d'outil de sonde : on suppose du texte (comportement d'avant)


def _clipboard_get() -> str:
    caps = _detect_caps()
    if caps["session"] == "wayland" and caps["wl_paste"]:
        ok, out = _run(["wl-paste", "--no-newline"], _CLIP_TIMEOUT)
        return out if ok else ""
    if caps["xclip"]:
        ok, out = _run(["xclip", "-selection", "clipboard", "-o"], _CLIP_TIMEOUT)
        return out if ok else ""
    try:
        return pyperclip.paste()
    except Exception:
        return ""


def _wl_copy(text: str) -> bool:
    """`wl-copy` en fire-and-forget.

    wl-copy fork un démon détenteur de la sélection qui hérite des descripteurs.
    Avec `capture_output`, subprocess.run attendrait la fin de ce démon ->
    blocage jusqu'au timeout. On envoie donc stdout/stderr vers /dev/null et on
    n'attend que la sortie du parent. Le nouveau démon supersède l'ancien, qui
    se termine seul — pas d'accumulation.
    """
    try:
        p = subprocess.Popen(
            ["wl-copy"], stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        p.communicate(input=text.encode("utf-8"), timeout=_CLIP_TIMEOUT)
        return p.returncode == 0
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        return False


def _clipboard_set(text: str) -> bool:
    caps = _detect_caps()
    if caps["session"] == "wayland" and caps["wl_copy"]:
        return _wl_copy(text)
    # pyperclip gère correctement le fork de xclip/xsel (Popen sans attente).
    try:
        pyperclip.copy(text)
        return True
    except Exception:
        return False


def _clipboard_confirm(text: str, timeout_ms: int) -> bool:
    """Attend que le presse-papiers contienne réellement `text`."""
    deadline = time.monotonic() + timeout_ms / 1000.0
    while time.monotonic() < deadline:
        if _clipboard_get() == text:
            return True
        time.sleep(0.02)
    return _clipboard_get() == text


# --------------------------------------------------------------------------- #
# Frappe                                                                      #
# --------------------------------------------------------------------------- #

def get_active_window_id():
    """ID de la fenêtre active via xdotool (chemin X11 uniquement)."""
    ok, out = _run(["xdotool", "getactivewindow"], _KEY_TIMEOUT)
    return out.strip() if ok and out.strip() else None


def _active_window_class_x11() -> str:
    ok, out = _run(["xdotool", "getactivewindow", "getwindowclassname"], _KEY_TIMEOUT)
    return out.strip() if ok else ""


def _paste_combo_for_target() -> str:
    """Combo de collage : Ctrl+Shift+V si la fenêtre active est un terminal."""
    default = _cfg("injection", "paste_combo", "ctrl+v")
    term = _cfg("injection", "terminal_paste_combo", "ctrl+shift+v")
    classes = _cfg("injection", "terminal_window_classes",
                   ["konsole", "gnome-terminal-server", "xterm", "st",
                    "alacritty", "kitty", "foot", "xterm-256color"])
    if _detect_caps()["session"] == "x11":
        cls = _active_window_class_x11().lower()
        if cls and any(c.lower() in cls for c in classes):
            return term
        return default
    # Wayland : aucune API standard pour la fenêtre focalisée. L'utilisateur
    # règle `injection.paste_combo` selon sa cible habituelle.
    return default


def _send_combo_wtype(mods, key) -> bool:
    cmd = ["wtype"]
    for m in mods:
        cmd += ["-M", m]
    cmd += ["-k", key]
    for m in reversed(mods):
        cmd += ["-m", m]
    ok, _out = _run(cmd, _KEY_TIMEOUT)
    return ok


def _send_combo_ydotool(mods, key) -> bool:
    kc = dict(KEYCODE)
    kc.update(_cfg("injection", "ydotool_keycodes", {}))
    names = list(mods) + [key]
    if any(n not in kc for n in names):
        return False
    events = [f"{kc[n]}:1" for n in names] + [f"{kc[n]}:0" for n in reversed(names)]
    ok, _out = _run(["ydotool", "key"] + events, _KEY_TIMEOUT)
    return ok


def _send_combo_xdotool(combo: str) -> bool:
    wid = get_active_window_id()
    if not wid:
        return False
    ok, _out = _run(["xdotool", "key", "--window", wid, combo], _KEY_TIMEOUT)
    return ok


def _send_paste(combo: str) -> bool:
    backend = _detect_caps()["key_backend"]
    mods, key = _parse_combo(combo)
    if backend == "wtype":
        return _send_combo_wtype(mods, key)
    if backend == "ydotool":
        return _send_combo_ydotool(mods, key)
    if backend == "xdotool":
        return _send_combo_xdotool(combo)
    return False


def _send_key(key_name: str, count: int) -> bool:
    backend = _detect_caps()["key_backend"]
    if backend == "wtype":
        cmd = ["wtype"]
        for _i in range(count):
            cmd += ["-k", key_name]
        ok, _out = _run(cmd, _KEY_TIMEOUT)
        return ok
    if backend == "ydotool":
        kc = dict(KEYCODE)
        kc.update(_cfg("injection", "ydotool_keycodes", {}))
        if key_name not in kc:
            return False
        code = kc[key_name]
        events = []
        for _i in range(count):
            events += [f"{code}:1", f"{code}:0"]
        ok, _out = _run(["ydotool", "key"] + events, _KEY_TIMEOUT)
        return ok
    if backend == "xdotool":
        wid = get_active_window_id()
        if not wid:
            return False
        cmd = ["xdotool", "key", "--window", wid]
        if count > 1:
            cmd += ["--repeat", str(count), "--delay", "0"]
        cmd.append(key_name)
        ok, _out = _run(cmd, _KEY_TIMEOUT)
        return ok
    return False


# --------------------------------------------------------------------------- #
# API publique                                                               #
# --------------------------------------------------------------------------- #

def type_text(text: str) -> bool:
    """Injecte `text` via presse-papiers + collage. Retourne False -> mode dégradé."""
    _ = get_translation()
    if not text:
        return False
    if _detect_caps()["key_backend"] is None:
        return False

    want_restore = _cfg("clipboard", "restore", True)
    restore_delay = _cfg("clipboard", "restore_delay_ms", 250) / 1000.0
    confirm_ms = _cfg("clipboard", "confirm_timeout_ms", 500)

    saved = None
    if want_restore:
        if _clipboard_is_text():
            saved = _clipboard_get()
        else:
            _warn(_("Clipboard holds non-text content; it will not be restored."))

    if not _clipboard_set(text):
        _warn(_("Could not write to the clipboard."))
        return False

    if not _clipboard_confirm(text, confirm_ms):
        _warn(_("Clipboard did not take the text in time; skipping paste."))
        if saved is not None:
            _clipboard_set(saved)
        return False

    ok = _send_paste(_paste_combo_for_target())

    time.sleep(restore_delay)
    if saved is not None:
        _clipboard_set(saved)
    return ok


def press_key(key_name: str, count: int = 1) -> bool:
    """Simule l'appui d'une touche nommée (aujourd'hui : 'BackSpace')."""
    if _detect_caps()["key_backend"] is None:
        return False
    return _send_key(key_name, count)


def play_sound():
    """Retour sonore de notification via paplay, si disponible."""
    if not check_command_exists("paplay") or not config.sound_file:
        return
    _run(["paplay", config.sound_file], _SOUND_TIMEOUT)
