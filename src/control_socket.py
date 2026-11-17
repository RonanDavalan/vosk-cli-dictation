# src/control_socket.py
#
# Contrôle d'état universel.
#
# L'instance en cours ouvre une socket Unix privée dans $XDG_RUNTIME_DIR. Le
# même binaire, invoqué avec un drapeau de contrôle (`--toggle`, `--sleep`,
# `--status`, `--stop`…), s'y connecte, envoie une ligne, affiche la réponse et
# sort. L'utilisateur lie ces sous-commandes aux raccourcis globaux de son
# bureau — ce qui fonctionne sous Wayland natif là où pynput est aveugle.
#
# Protocole : une requête = « jeton[ argument] » terminé par \n. Réponse =
# "OK <ÉTAT>" ou "ERR <raison>", terminée par \n. <ÉTAT> ∈ {DICTÉE, ÉCOUTE,
# VEILLE}. `info` répond « OK <JSON> » sur une seule ligne ; `set-*` répond tout
# de suite « OK <ÉTAT> » et applique le réglage en arrière-plan ;
# `reset-selection` (sans argument) vide le choix mémorisé et revient à la config.

import json
import os
import queue
import socket
import threading

from src.runtime_state import runtime_state

SOCKET_NAME = "vosk-cli-dictation.sock"

# Jetons acceptés sur la socket.
COMMANDS = {
    "toggle",
    "dictation-on",
    "dictation-off",
    "finalize",
    "cancel",
    "sleep",
    "wake",
    "sleep-toggle",
    "status",
    "quit",
    "info",
    "set-lang",
    "set-model",
    "set-refine",
    "set-correction",
    "reset-selection",
}

# Jetons qui prennent un argument ; les autres le refusent.
ARG_COMMANDS = {"set-lang", "set-model", "set-refine", "set-correction"}

# Un `info` dépasse 256 octets ; la requête et la réponse sont lues jusqu'au
# saut de ligne, dans cette limite.
MAX_LINE = 65536

# Jeton -> message posé dans la control_queue (vocabulaire déjà géré par ui.py).
_TO_QUEUE = {
    "toggle": "TOGGLE_RECORDING",
    "finalize": "FINALIZE_SESSION",
    "sleep-toggle": "TOGGLE_SLEEP",
    "dictation-on": "DICTATION_ON",
    "dictation-off": "DICTATION_OFF",
    "sleep": "SLEEP_ON",
    "wake": "SLEEP_OFF",
    "cancel": "/cancel",
}


_ECHOABLE = {"TOGGLE_RECORDING", "FINALIZE_SESSION", "TOGGLE_SLEEP"}
_echo_notice_shown = False


def _echo_notice():
    global _echo_notice_shown
    if _echo_notice_shown:
        return
    _echo_notice_shown = True
    from config.config import config
    from src.i18n import get_translation

    _ = get_translation()
    print(
        f"\n{config.color_warning}"
        f"{_('A desktop shortcut and the program’s own hotkey fired together; the second one was ignored. Set hotkeys.pynput_enabled to false if the desktop owns this key.')}"
        f"{config.RESET}"
    )


def socket_path() -> str:
    base = os.environ.get("XDG_RUNTIME_DIR")
    if not base or not os.path.isdir(base):
        base = "/run/user/{}".format(os.getuid())
    if not os.path.isdir(base):
        base = os.environ.get("TMPDIR", "/tmp")
    return os.path.join(base, SOCKET_NAME)


# --------------------------------------------------------------------------- #
# Client — utilisé par le binaire invoqué avec un drapeau de contrôle          #
# --------------------------------------------------------------------------- #


def _read_line(sock) -> bytes:
    """Lit jusqu'au saut de ligne, à la fin du flux ou à MAX_LINE octets. Un
    délai dépassé après un premier octet rend ce qui est arrivé."""
    data = b""
    while b"\n" not in data and len(data) < MAX_LINE:
        try:
            chunk = sock.recv(4096)
        except socket.timeout:
            if data:
                break
            raise
        if not chunk:
            break
        data += chunk
    return data


def send_control_command(command: str):
    """Envoie `command` à l'instance en cours. Retourne la réponse (str) ou
    None si aucune instance n'écoute."""
    path = socket_path()
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.settimeout(2.0)
    try:
        s.connect(path)
        s.sendall((command.strip() + "\n").encode("utf-8"))
        return _read_line(s).decode("utf-8", "replace").strip()
    except (FileNotFoundError, ConnectionRefusedError, socket.timeout, OSError):
        return None
    finally:
        try:
            s.close()
        except OSError:
            pass


def instance_running() -> bool:
    reply = send_control_command("status")
    return reply is not None and reply.startswith("OK")


# --------------------------------------------------------------------------- #
# Serveur — tourne dans un thread de l'instance principale                     #
# --------------------------------------------------------------------------- #


def _info_fallback() -> dict:
    snap = runtime_state.snapshot()
    return {"state": snap["state"], "loading": False, "last_error": None}


def _handle(raw: str, control_queue, controller=None) -> str:
    """`controller` (src/engine_switch.py) répond à `info` et aux `set-*` ;
    sans lui, `info` rend l'état seul et les `set-*` rendent ERR unsupported."""
    token, _sep, arg = raw.strip().partition(" ")
    token = token.lower()
    arg = arg.strip()
    if token not in COMMANDS or (arg and token not in ARG_COMMANDS):
        return "ERR unknown-command"
    if token == "status":
        return "OK " + runtime_state.snapshot()["state"]
    if token == "quit":
        return "OK stopping"
    if token == "info":
        data = controller.info() if controller else _info_fallback()
        return "OK " + json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    if token == "reset-selection":
        refusal = controller.request(token, "") if controller else "unsupported"
        return (
            "ERR " + refusal if refusal else "OK " + runtime_state.snapshot()["state"]
        )
    if token in ARG_COMMANDS:
        if controller is None:
            return "ERR unsupported"
        if not arg:
            return "ERR bad-argument"
        refusal = controller.request(token, arg)
        if refusal:
            return "ERR " + refusal
        return "OK " + runtime_state.snapshot()["state"]
    msg = _TO_QUEUE.get(token)
    if msg is None:
        return "ERR unsupported"
    if msg in _ECHOABLE and runtime_state.is_hotkey_echo(msg):
        _echo_notice()
        return "OK " + runtime_state.snapshot()["state"]
    try:
        control_queue.put_nowait(msg)
    except queue.Full:
        return "ERR busy"
    return "OK " + runtime_state.snapshot()["state"]


def start_control_server(control_queue, stop_event, controller=None):
    """Ouvre la socket et sert les commandes jusqu'à stop_event. Retourne le
    thread serveur (démon). Lève OSError si le bind échoue."""
    path = socket_path()
    try:
        os.unlink(path)
    except FileNotFoundError:
        pass

    srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    srv.bind(path)
    os.chmod(path, 0o600)
    srv.listen(8)
    srv.settimeout(0.5)

    def loop():
        try:
            while not stop_event.is_set():
                try:
                    conn, _addr = srv.accept()
                except socket.timeout:
                    continue
                except OSError:
                    break
                with conn:
                    try:
                        conn.settimeout(2.0)
                        raw = _read_line(conn).decode("utf-8", "replace")
                        reply = _handle(raw, control_queue, controller)
                        conn.sendall((reply + "\n").encode("utf-8"))
                        if reply == "OK stopping":
                            stop_event.set()
                    except OSError:
                        pass
        finally:
            try:
                srv.close()
            finally:
                try:
                    os.unlink(path)
                except OSError:
                    pass

    t = threading.Thread(target=loop, daemon=True)
    t.start()
    return t
