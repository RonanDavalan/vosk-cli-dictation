"""Lancer la dictée détachée du programme de l'icône, ou lui faire télécharger un modèle."""

import os
import shlex
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

ENV_COMMAND = "VOSK_CLI_DICTATION_COMMAND"
REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass
class Command:
    argv: list
    cwd: str | None = None

    def with_args(self, *args) -> "Command":
        return Command(self.argv + list(args), self.cwd)


def dictation_command(override: str | None = None) -> Command | None:
    """La commande qui lance la dictée : `--dictation-command`, puis la variable
    d'environnement, puis `vosk-cli-dictation` du PATH, puis le clone du dépôt
    (son venv `vosk-env`, depuis la racine du dépôt). None si rien n'existe."""
    text = override or os.environ.get(ENV_COMMAND)
    if text:
        return Command(shlex.split(text))
    found = shutil.which("vosk-cli-dictation")
    if found:
        return Command([found])
    clone_python = REPO_ROOT / "vosk-env" / "bin" / "python3"
    clone_main = REPO_ROOT / "src" / "main.py"
    if clone_python.is_file() and clone_main.is_file():
        return Command([str(clone_python), str(clone_main)], str(REPO_ROOT))
    return None


def state_dir() -> Path:
    base = os.environ.get("XDG_STATE_HOME") or str(Path.home() / ".local" / "state")
    return Path(base) / "vosk-cli-dictation"


def log_path() -> Path:
    return state_dir() / "instance.log"


def launch_detached(command: Command) -> int:
    """Lance la dictée dans sa propre session, sans terminal, sa sortie dans le
    journal. Rend son PID ; lève OSError si le lancement échoue."""
    log = log_path()
    log.parent.mkdir(parents=True, exist_ok=True)
    with open(log, "ab") as out:
        out.write(time.strftime("\n=== %Y-%m-%d %H:%M:%S ===\n").encode())
        process = subprocess.Popen(
            command.argv,
            cwd=command.cwd,
            stdin=subprocess.DEVNULL,
            stdout=out,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        out.write(("pid %d\n" % process.pid).encode())
    return process.pid


LOCK_NAME = "vosk-cli-dictation.lock"


def lock_path() -> Path:
    base = os.environ.get("XDG_RUNTIME_DIR")
    if not base or not os.path.isdir(base):
        base = "/run/user/{}".format(os.getuid())
    if not os.path.isdir(base):
        base = os.environ.get("TMPDIR", "/tmp")
    return Path(base) / LOCK_NAME


def _birth_ticks(pid: int) -> int:
    with open("/proc/%d/stat" % pid) as f:
        return int(f.read().rsplit(")", 1)[1].split()[19])


def running_pid():
    """Pid du démon vivant qui tient le verrou d'instance, ou None. Ne prend jamais le verrou."""
    try:
        pid, born = (int(x) for x in lock_path().read_text().split())
        return pid if _birth_ticks(pid) == born else None
    except (OSError, ValueError):
        return None


def download_arguments(lang: str, size: str) -> list:
    return ["--download-model", lang, "--model-size", size]
