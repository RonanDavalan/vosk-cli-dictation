import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).parent))

import pytest

from fake_server import FakeServer


@pytest.fixture(autouse=True)
def isolated_env(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    (tmp_path / "run").mkdir()
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path / "run"))
    for name in ("LC_ALL", "LC_MESSAGES", "LANGUAGE"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("LANG", "en_US.UTF-8")


@pytest.fixture(scope="session")
def qapp():
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


@pytest.fixture
def server():
    # Chemin court : une socket Unix a une limite de longueur.
    with tempfile.TemporaryDirectory(prefix="vt") as d:
        srv = FakeServer(Path(d) / "s.sock").start()
        yield srv
        srv.stop()
