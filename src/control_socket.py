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
# Protocole : une requête = un jeton, terminé par \n. Réponse = "OK <ÉTAT>" ou
# "ERR <raison>", terminée par \n. <ÉTAT> ∈ {DICTÉE, ÉCOUTE, VEILLE}.

import os
import queue
import socket
import threading

from src.runtime_state import runtime_state

SOCKET_NAME = "vosk-cli-dictation.sock"

# Jetons acceptés sur la socket.
COMMANDS = {
    "toggle", "dictation-on", "dictation-off", "finalize", "cancel",
    "sleep", "wake", "sleep-toggle", "status", "quit",
}

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

def send_control_command(command: str):
    """Envoie `command` à l'instance en cours. Retourne la réponse (str) ou
    None si aucune instance n'écoute."""
    path = socket_path()
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.settimeout(2.0)
    try:
        s.connect(path)
        s.sendall((command.strip() + "\n").encode("utf-8"))
        return s.recv(256).decode("utf-8", "replace").strip()
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

def _handle(raw: str, control_queue) -> str:
    cmd = raw.strip().lower()
    if cmd not in COMMANDS:
        return "ERR unknown-command"
    if cmd == "status":
        return "OK " + runtime_state.snapshot()["state"]
    if cmd == "quit":
        return "OK stopping"
    msg = _TO_QUEUE.get(cmd)
    if msg is None:
        return "ERR unsupported"
    try:
        control_queue.put_nowait(msg)
    except queue.Full:
        return "ERR busy"
    return "OK " + runtime_state.snapshot()["state"]


def start_control_server(control_queue, stop_event):
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
                        raw = conn.recv(256).decode("utf-8", "replace")
                        reply = _handle(raw, control_queue)
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
