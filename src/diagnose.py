# src/diagnose.py
#
# `vosk-cli-dictation --diagnose` (chantier 7 volet G) : vérifie en une commande
# ce qu'il faut pour que l'outil fonctionne, au lieu d'un débogage manuel.

import os

from config.config import config
from src.i18n import get_translation


def _line(ok, label, detail=""):
    mark = "OK  " if ok else "!!  "
    print("{}{:<32} {}".format(mark, label, detail))
    return bool(ok)


def run_diagnose():
    _ = get_translation()
    from src import system_control as sc
    caps = sc._detect_caps()
    ok_all = True

    print(_("Environment"))
    ok_all &= _line(caps["session"] in ("x11", "wayland"),
                    _("Session type"), caps["session"])
    ok_all &= _line(caps["key_backend"] is not None,
                    _("Text-injection backend"), caps["key_backend"] or _("none"))

    print()
    print(_("Tools"))
    for name, present in (
        ("xdotool", caps["xdotool"]), ("wtype", caps["wtype"]),
        ("wl-copy", caps["wl_copy"]), ("wl-paste", caps["wl_paste"]),
        ("xclip", caps["xclip"]), ("ydotool (+ daemon)", caps["ydotool"]),
        ("paplay", sc.check_command_exists("paplay")),
    ):
        _line(present, name, _("found") if present else _("missing"))

    if caps["ydotool"]:
        uinput = "/dev/uinput"
        rw = os.access(uinput, os.R_OK | os.W_OK)
        _line(rw, _("Access to {path}").format(path=uinput),
              "" if rw else _("no rw access (add your user to the 'input' group)"))

    print()
    print(_("Models"))
    for model in config.data.get("vosk_models", []):
        path = config.get_model_path_by_name(model["name"])
        ok = bool(path) and os.path.isdir(path)
        ok_all &= _line(ok, model["name"], path or _("not found"))

    print()
    print(_("Audio input"))
    audio_ok = False
    try:
        import pyaudio
        p = pyaudio.PyAudio()
        try:
            s = p.open(format=pyaudio.paInt16,
                       channels=config.audio["channels"],
                       rate=config.audio["sample_rate"],
                       input=True,
                       frames_per_buffer=config.audio["frames_per_buffer"])
            s.close()
            audio_ok = True
        finally:
            p.terminate()
    except Exception as e:
        audio_ok = False
        _line(False, _("Open an input stream"), str(e))
    if audio_ok:
        _line(True, _("Open an input stream"),
              "{} Hz mono".format(config.audio["sample_rate"]))
    ok_all &= audio_ok

    print()
    print(_("Clipboard"))
    try:
        marker = "vosk-diagnose-probe"
        saved_text = sc._clipboard_is_text()
        saved = sc._clipboard_get() if saved_text else None
        wrote = sc._clipboard_set(marker) and sc._clipboard_confirm(marker, 800)
        if saved is not None:
            sc._clipboard_set(saved)
        _line(wrote, _("Read / write round-trip"),
              "" if wrote else _("failed (install wl-clipboard or xclip)"))
        ok_all &= wrote
    except Exception as e:
        ok_all &= _line(False, _("Read / write round-trip"), str(e))

    print()
    print(_("Control socket"))
    from src.control_socket import socket_path, instance_running
    path = socket_path()
    running = instance_running()
    _line(True, _("Socket path"), path)
    _line(True, _("Session running"), _("yes") if running else _("no"))
    dir_ok = os.access(os.path.dirname(path), os.W_OK)
    ok_all &= _line(dir_ok, _("Runtime dir writable"), os.path.dirname(path))

    print()
    print(_("Config file in use: {path}").format(path=config.config_path))
    print()
    print(_("All checks passed.") if ok_all else _("Some checks failed (see !! above)."))
    return 0 if ok_all else 1
