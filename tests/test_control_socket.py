# Chantier 7 volet A/H — couche IPC : socket Unix de contrôle.

import os
import queue
import stat
import threading
import time

import pytest

import src.control_socket as cs
from src.runtime_state import runtime_state, STATE_LISTENING, STATE_DICTATING


@pytest.fixture
def runtime_dir(tmp_path, monkeypatch):
    d = tmp_path / "run"
    d.mkdir()
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(d))
    return d


@pytest.fixture
def server(runtime_dir):
    ctrl_q = queue.Queue(maxsize=32)
    stop = threading.Event()
    runtime_state.set_state(STATE_LISTENING)
    t = cs.start_control_server(ctrl_q, stop)
    yield ctrl_q, stop
    stop.set()
    t.join(timeout=2.0)


def test_socket_path_follows_xdg_runtime_dir(runtime_dir):
    assert cs.socket_path() == os.path.join(str(runtime_dir), cs.SOCKET_NAME)


def test_socket_is_created_with_0600(server, runtime_dir):
    path = cs.socket_path()
    assert os.path.exists(path)
    mode = stat.S_IMODE(os.stat(path).st_mode)
    assert mode == 0o600


def test_status_round_trip(server):
    runtime_state.set_state(STATE_LISTENING)
    assert cs.send_control_command("status") == "OK " + STATE_LISTENING
    assert cs.instance_running() is True


def test_command_is_forwarded_to_the_queue(server):
    ctrl_q, _stop = server
    reply = cs.send_control_command("toggle")
    assert reply.startswith("OK")
    assert ctrl_q.get_nowait() == "TOGGLE_RECORDING"


def test_unknown_command_is_rejected(server):
    assert cs.send_control_command("frobnicate") == "ERR unknown-command"


def test_quit_sets_stop_event(server):
    _ctrl_q, stop = server
    assert cs.send_control_command("quit") == "OK stopping"
    time.sleep(0.2)
    assert stop.is_set()


def test_no_server_means_no_reply(runtime_dir):
    assert cs.send_control_command("status") is None
    assert cs.instance_running() is False


def test_stale_socket_file_is_replaced(runtime_dir):
    # Un fichier de socket résiduel (aucun serveur derrière) ne doit pas
    # empêcher un nouveau démarrage : start_control_server l'unlink et rebind.
    path = cs.socket_path()
    with open(path, "w") as f:
        f.write("stale")
    assert os.path.exists(path)

    ctrl_q = queue.Queue(maxsize=32)
    stop = threading.Event()
    t = cs.start_control_server(ctrl_q, stop)
    try:
        assert cs.send_control_command("status").startswith("OK")
        mode = stat.S_IMODE(os.stat(path).st_mode)
        assert mode == 0o600
    finally:
        stop.set()
        t.join(timeout=2.0)


def test_busy_queue_reports_err_busy(runtime_dir):
    full_q = queue.Queue(maxsize=1)
    full_q.put_nowait("x")
    stop = threading.Event()
    runtime_state.set_state(STATE_DICTATING)
    t = cs.start_control_server(full_q, stop)
    try:
        assert cs.send_control_command("finalize") == "ERR busy"
    finally:
        stop.set()
        t.join(timeout=2.0)
