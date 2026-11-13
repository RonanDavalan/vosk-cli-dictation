# src/instance_lock.py
#
# Instance unique : un verrou exclusif sur un fichier de $XDG_RUNTIME_DIR, pris
# avant le chargement du modèle et tenu jusqu'à la mort du processus. Le noyau
# le libère seul, SIGKILL compris : il n'existe pas de verrou périmé.

import fcntl
import os

from src.control_socket import socket_path

LOCK_NAME = "vosk-cli-dictation.lock"
_held_fd = None


def lock_path() -> str:
    return os.path.join(os.path.dirname(socket_path()), LOCK_NAME)


def _birth_ticks(pid: int) -> int:
    """Instant de naissance du processus (champ 22 de /proc/<pid>/stat) : distingue
    un pid réutilisé d'un démon vivant."""
    with open("/proc/%d/stat" % pid) as f:
        return int(f.read().rsplit(")", 1)[1].split()[19])


def acquire() -> bool:
    """Prend le verrou d'instance. False si un autre démon vit."""
    global _held_fd
    fd = os.open(lock_path(), os.O_RDWR | os.O_CREAT, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        os.close(fd)
        return False
    os.ftruncate(fd, 0)
    os.write(fd, ("%d %d\n" % (os.getpid(), _birth_ticks(os.getpid()))).encode())
    _held_fd = fd
    return True


def owner_pid():
    """Pid du démon vivant qui tient le verrou, ou None. Ne prend jamais le verrou."""
    try:
        with open(lock_path()) as f:
            pid, born = (int(x) for x in f.read().split())
        return pid if _birth_ticks(pid) == born else None
    except (OSError, ValueError):
        return None
