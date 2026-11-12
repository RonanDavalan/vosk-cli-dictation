"""Client de la socket de contrôle de la dictée.

`request` parle à la socket sans rien importer de Qt. `ControlClient` pose le
sondage `info` et l'envoi des commandes dans des fils à part : l'interface ne
bloque jamais sur une socket lente ou absente.
"""

import json
import os
import socket
import threading

from PySide6.QtCore import QObject, Signal

SOCKET_NAME = "vosk-cli-dictation.sock"
POLL_INTERVAL_S = 0.25
INFO_TIMEOUT_S = 0.2
COMMAND_TIMEOUT_S = 2.0
MAX_LINE = 65536


def default_socket_path() -> str:
    base = os.environ.get("XDG_RUNTIME_DIR")
    if not base or not os.path.isdir(base):
        base = "/run/user/{}".format(os.getuid())
    if not os.path.isdir(base):
        base = os.environ.get("TMPDIR", "/tmp")
    return os.path.join(base, SOCKET_NAME)


def request(path: str, command: str, timeout: float):
    """Envoie `command` et rend la réponse (sans saut de ligne), ou None si
    aucune dictée n'écoute ou ne répond dans le délai."""
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        sock.connect(path)
        sock.sendall((command.strip() + "\n").encode("utf-8"))
        data = b""
        while b"\n" not in data and len(data) < MAX_LINE:
            chunk = sock.recv(4096)
            if not chunk:
                break
            data += chunk
        return data.decode("utf-8", "replace").strip() or None
    except OSError:
        return None
    finally:
        sock.close()


def parse_info(reply):
    """Le dictionnaire de la réponse `OK {json}` de `info`, ou None."""
    if not reply or not reply.startswith("OK "):
        return None
    try:
        data = json.loads(reply[3:])
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


class ControlClient(QObject):
    """`info_changed(dict|None)` à chaque réponse (None : socket absente),
    `command_done(command, reply)` à chaque commande envoyée."""

    info_changed = Signal(object)
    command_done = Signal(str, object)

    def __init__(self, path: str, parent=None):
        super().__init__(parent)
        self.path = path
        self._stop = threading.Event()
        self._thread = None

    def start(self) -> None:
        if self._thread is None:
            self._thread = threading.Thread(target=self._poll, daemon=True)
            self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=1.0)

    def _poll(self) -> None:
        while not self._stop.is_set():
            self.info_changed.emit(parse_info(request(self.path, "info", INFO_TIMEOUT_S)))
            self._stop.wait(POLL_INTERVAL_S)

    def send(self, command: str) -> None:
        threading.Thread(target=self._send, args=(command,), daemon=True).start()

    def _send(self, command: str) -> None:
        self.command_done.emit(command, request(self.path, command, COMMAND_TIMEOUT_S))
