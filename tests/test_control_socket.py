# Couche IPC : socket Unix de contrôle.

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


# --- Jetons à argument et `info` ---------------------------------------------

import json


class FakeController:
    def __init__(self):
        self.requests = []
        self.refuse = None

    def info(self):
        return {
            "state": runtime_state.state,
            "lang": "fr",
            "loading": False,
            "last_error": None,
            "accents": "éàü",
        }

    def request(self, token, arg):
        self.requests.append((token, arg))
        return self.refuse


@pytest.fixture
def server_with_controller(runtime_dir):
    ctrl_q = queue.Queue(maxsize=32)
    stop = threading.Event()
    controller = FakeController()
    runtime_state.set_state(STATE_LISTENING)
    t = cs.start_control_server(ctrl_q, stop, controller)
    yield controller
    stop.set()
    t.join(timeout=2.0)


def test_status_still_answers_ok_ecoute(server_with_controller):
    assert cs.send_control_command("status") == "OK ÉCOUTE"


def test_info_is_read_as_json(server_with_controller):
    reply = cs.send_control_command("info")
    assert reply.startswith("OK ")
    data = json.loads(reply[3:])
    assert data["lang"] == "fr" and data["accents"] == "éàü"


def test_info_longer_than_256_bytes_is_read_whole(runtime_dir):
    class Big(FakeController):
        def info(self):
            return {"models": ["vosk-model-%03d" % i for i in range(60)]}

    stop = threading.Event()
    t = cs.start_control_server(queue.Queue(), stop, Big())
    try:
        reply = cs.send_control_command("info")
        assert len(reply) > 256
        assert len(json.loads(reply[3:])["models"]) == 60
    finally:
        stop.set()
        t.join(timeout=2.0)


def test_info_without_controller_gives_state_only(server):
    data = json.loads(cs.send_control_command("info")[3:])
    assert data["state"] == STATE_LISTENING and data["loading"] is False


def test_set_token_carries_its_argument_with_case_kept(server_with_controller):
    reply = cs.send_control_command("set-model vosk-model-FR-0.22")
    assert reply == "OK ÉCOUTE"
    assert server_with_controller.requests == [("set-model", "vosk-model-FR-0.22")]


def test_set_token_refusal_becomes_err(server_with_controller):
    server_with_controller.refuse = "unsupported"
    assert cs.send_control_command("set-refine none") == "ERR unsupported"


def test_set_token_without_argument_is_rejected(server_with_controller):
    assert cs.send_control_command("set-lang") == "ERR bad-argument"
    assert server_with_controller.requests == []


def test_set_token_without_controller_is_unsupported(server):
    assert cs.send_control_command("set-lang en") == "ERR unsupported"


def test_argument_on_a_plain_token_is_unknown(server):
    assert cs.send_control_command("status now") == "ERR unknown-command"
    assert cs.send_control_command("set-unknown x") == "ERR unknown-command"


def test_reset_selection_needs_a_controller_and_takes_no_argument(server):
    assert cs.send_control_command("reset-selection") == "ERR unsupported"
    assert cs.send_control_command("reset-selection now") == "ERR unknown-command"


# --- écho d'un raccourci pynput et d'une commande de bureau ------------------ #


def test_socket_command_right_after_hotkey_is_ignored(monkeypatch):
    monkeypatch.setattr(cs, "_echo_notice_shown", True)
    q = queue.Queue()
    runtime_state.note_hotkey("TOGGLE_RECORDING")
    reply = cs._handle("toggle", q)
    assert reply.startswith("OK") and q.empty()


def test_socket_command_after_window_is_queued(monkeypatch):
    q = queue.Queue()
    clock = [100.0]
    monkeypatch.setattr("src.runtime_state.time.monotonic", lambda: clock[0])
    runtime_state.note_hotkey("TOGGLE_RECORDING")
    clock[0] += 1.1
    cs._handle("toggle", q)
    assert q.get_nowait() == "TOGGLE_RECORDING"


def test_dictation_on_is_never_ignored():
    q = queue.Queue()
    runtime_state.note_hotkey("DICTATION_ON")
    cs._handle("dictation-on", q)
    assert q.get_nowait() == "DICTATION_ON"
