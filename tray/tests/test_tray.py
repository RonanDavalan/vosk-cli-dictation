# Icône et menu hors écran, face à un faux serveur du protocole de la socket.

import time
from collections import Counter

import pytest
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QSystemTrayIcon

from vosk_cli_dictation_tray.client import ControlClient
from vosk_cli_dictation_tray.i18n import Translator
from vosk_cli_dictation_tray.tray import DictationTray

COLORS = {
    "dictating": (0xE5, 0x32, 0x2D),
    "listening": (0xDB, 0x75, 0x00),
    "sleeping": (0x3B, 0x82, 0xF6),
    "off": (0x2E, 0x9E, 0x4F),
}
STATES = {
    "DICTÉE": "dictating",
    "ÉCOUTE": "listening",
    "VEILLE": "sleeping",
    None: "off",
}


class StubClient(QObject):
    info_changed = Signal(object)
    command_done = Signal(str, object)

    def __init__(self):
        super().__init__()
        self.sent = []

    def send(self, command):
        self.sent.append(command)

    def stop(self):
        pass


def info(**kw):
    data = {
        "state": "ÉCOUTE",
        "lang": "en",
        "lang_source": "config",
        "langs": ["fr", "en", "de", "es"],
        "model": "vosk-model-small-fr-0.22",
        "models": [
            {"folder": "vosk-model-small-fr-0.22", "size": "small"},
            {"folder": "vosk-model-fr-0.22", "size": "big"},
        ],
        "refine": "none",
        "device": None,
        "correction": "none",
        "loading": False,
        "last_error": None,
    }
    data.update(kw)
    return data


@pytest.fixture
def make(qapp):
    made = []

    def build(notes=None, system_lang="en"):
        client = StubClient()
        notes = [] if notes is None else notes
        tray = DictationTray(client, Translator("en"), system_lang, notify=notes.append)
        made.append(tray)
        return tray, client, notes

    yield build
    for tray in made:
        tray.hide()
        tray.deleteLater()


def dominant_color(tray):
    image = tray.icon().pixmap(48, 48).toImage()
    counts = Counter()
    for y in range(image.height()):
        for x in range(image.width()):
            c = image.pixelColor(x, y)
            if c.alpha() > 200:
                counts[(c.red(), c.green(), c.blue())] += 1
    return counts.most_common(1)[0][0]


def mask(tray):
    image = tray.icon().pixmap(48, 48).toImage()
    return tuple(
        image.pixelColor(x, y).alpha() > 128
        for y in range(image.height())
        for x in range(image.width())
    )


@pytest.mark.parametrize("state", list(STATES))
def test_color_follows_the_state(make, state):
    tray, _, _ = make()
    tray.on_info(info(state=state) if state else None)
    assert tray.icon_name == STATES[state]
    got = dominant_color(tray)
    want = COLORS[STATES[state]]
    assert all(abs(g - w) <= 12 for g, w in zip(got, want)), (got, want)


def test_four_states_have_four_distinct_shapes(make):
    tray, _, _ = make()
    masks = {}
    for state in STATES:
        tray.on_info(info(state=state) if state else None)
        masks[state] = mask(tray)
    assert len(set(masks.values())) == 4


def test_socket_absent_gives_green_and_launch_entry(make):
    tray, _, _ = make()
    tray.on_info(None)
    assert tray.icon_name == "off"
    assert tray.a_launch.text() == "Activate voice dictation"
    assert tray.a_launch.isEnabled()
    for action in (tray.a_dictation, tray.a_sleep, tray.a_finalize, tray.a_cancel):
        assert not action.isEnabled()
    for menu in (tray.m_lang, tray.m_model, tray.m_refine, tray.m_correction):
        assert not menu.isEnabled()
    assert not tray.a_revert.isEnabled()
    assert tray.status_text() == "Dictation not running"


@pytest.mark.parametrize(
    "state,dictation,sleep",
    [
        ("DICTÉE", "Turn dictation off", "Enter deep sleep"),
        ("ÉCOUTE", "Turn dictation on", "Enter deep sleep"),
        ("VEILLE", "Turn dictation on", "Leave deep sleep"),
    ],
)
def test_entries_follow_the_state(make, state, dictation, sleep):
    tray, client, _ = make()
    tray.on_info(info(state=state))
    assert tray.a_dictation.text() == dictation
    assert tray.a_sleep.text() == sleep
    assert tray.a_launch.text() == "Quit dictation"
    assert tray.a_finalize.isEnabled() == (state != "VEILLE")
    assert tray.a_cancel.isEnabled() == (state != "VEILLE")
    tray.a_dictation.trigger()
    tray.a_sleep.trigger()
    assert client.sent == [
        ("dictation-off" if state == "DICTÉE" else "dictation-on"),
        ("wake" if state == "VEILLE" else "sleep"),
    ]


def test_menu_order(make):
    tray, _, _ = make()
    tray.on_info(info())
    titles = [
        (a.menu().title() if a.menu() else a.text()) or "-"
        for a in tray.contextMenu().actions()
    ]
    texts = [t.split(" — ")[0] for t in titles]
    assert texts[0].startswith("Listening")
    order = [
        "Turn dictation on",
        "Enter deep sleep",
        "Finish and copy the text",
        "Cancel the session",
        "Language",
        "Model",
        "Refinement",
        "Correction",
        "Revert to the configuration",
        "Quit dictation",
        "Launch the icon at login",
        "Quit the icon",
    ]
    positions = [texts.index(o) for o in order]
    assert positions == sorted(positions)


def test_refinement_and_correction_are_greyed_with_their_reason(make):
    tray, _, _ = make()
    tray.on_info(info())
    for menu, name in (
        (tray.m_refine, "Refinement"),
        (tray.m_correction, "Correction"),
    ):
        assert not menu.isEnabled()
        assert menu.title() == name + " — not available in this dictation"


def test_refinement_announced_by_info_is_offered(make):
    tray, client, _ = make()
    tray.on_info(
        info(
            refine_options=["none", "whisper:small", "whisper:medium"],
            refine="whisper:small",
            device="cuda",
        )
    )
    assert tray.m_refine.isEnabled()
    labels = [a.text() for a in tray.m_refine.actions()]
    assert labels == ["None", "Whisper small (GPU)", "Whisper medium (GPU)"]
    assert [a.isChecked() for a in tray.m_refine.actions()] == [False, True, False]
    tray.m_refine.actions()[2].trigger()
    assert client.sent == ["set-refine whisper:medium"]


def test_refinement_reason_comes_from_info(make):
    tray, _, _ = make()
    tray.on_info(
        info(refine_options=["none"], refine_reason="faster-whisper is not installed")
    )
    assert not tray.m_refine.isEnabled()
    assert tray.m_refine.title() == "Refinement — faster-whisper is not installed"


def test_status_line_and_tooltip(make):
    tray, _, _ = make()
    tray.on_info(
        info(state="DICTÉE", model="vosk-model-fr-0.22", refine="whisper:small")
    )
    assert tray.status_text() == "Dictating — English — Vosk full + Whisper small"
    assert tray.toolTip() == tray.status_text()
    tray.on_info(info(loading=True))
    assert tray.toolTip().endswith("Loading model…")
    assert not tray.m_lang.isEnabled()


def test_language_entries_and_choice(make):
    tray, client, _ = make(system_lang="de")
    tray.on_info(info(langs=["fr", "en"]))
    assert tray.a_lang["system"].text() == "Follow the system (German)"
    assert tray.a_lang["en"].isChecked()
    assert tray.a_lang["de"].text() == "German (to download, 46 MB)"
    tray.a_lang["en"].trigger()
    tray.a_lang["system"].trigger()
    assert client.sent == ["set-lang en", "set-lang system"]
    tray.on_info(info(lang_source="system"))
    assert tray.a_lang["system"].isChecked()


def test_missing_model_size_uses_the_language_units(make):
    tray, _client, _ = make()
    tray.on_info(
        info(
            lang="fr",
            langs=["fr"],
            models=[{"folder": "vosk-model-small-fr-0.22", "size": "small"}],
        )
    )
    assert tray.a_model["big"].text() == "Modèle complet (à télécharger, 1,5 Go)"
    assert tray.a_lang["es"].text() == "Espagnol (à télécharger, 40 Mo)"


def test_model_entries_carry_the_measured_memory_in_their_tooltip(make):
    tray, _client, _ = make()
    tray.on_info(
        info(
            lang="fr", models=[{"folder": "vosk-model-small-fr-0.22", "size": "small"}]
        )
    )
    assert (
        tray.a_model["small"].toolTip() == "Mémoire après chargement : environ 171 Mo"
    )
    assert tray.a_model["big"].toolTip() == "Mémoire après chargement : environ 3,3 Go"
    tray.on_info(
        info(
            lang="en",
            models=[{"folder": "vosk-model-small-en-us-0.15", "size": "small"}],
        )
    )
    assert "more than 5.0 GB" in tray.a_model["big"].toolTip()


def test_model_entries_and_choice(make):
    tray, client, _ = make()
    tray.on_info(info(models=[{"folder": "vosk-model-small-fr-0.22", "size": "small"}]))
    assert tray.a_model["small"].isChecked()
    assert tray.a_model["big"].text() == "Full model (to download, 1.9 GB)"
    tray.on_info(info())
    tray.a_model["big"].trigger()
    assert client.sent == ["set-model vosk-model-fr-0.22"]


def test_missing_model_starts_a_download(make, monkeypatch):
    tray, client, notes = make()
    asked = []
    monkeypatch.setattr(
        tray, "download_model", lambda lang, size: asked.append((lang, size))
    )
    tray.on_info(
        info(
            langs=["en"],
            models=[{"folder": "vosk-model-small-fr-0.22", "size": "small"}],
        )
    )
    tray.a_model["big"].trigger()
    tray.a_lang["de"].trigger()
    assert asked == [("en", "big"), ("de", "small")]
    assert client.sent == []


def test_left_click_toggles_or_launches(make, monkeypatch):
    tray, client, _ = make()
    launched = []
    monkeypatch.setattr(tray, "launch_dictation", lambda: launched.append(True))
    tray.on_info(info())
    tray.activated.emit(QSystemTrayIcon.ActivationReason.Trigger)
    tray.activated.emit(QSystemTrayIcon.ActivationReason.Context)
    assert client.sent == ["toggle"] and launched == []
    tray.on_info(None)
    tray.activated.emit(QSystemTrayIcon.ActivationReason.Trigger)
    assert client.sent == ["toggle"] and launched == [True]


def test_revert_and_quit_dictation(make):
    tray, client, _ = make()
    tray.on_info(info())
    tray.a_revert.trigger()
    tray.a_launch.trigger()
    assert client.sent == ["reset-selection", "quit"]


def test_error_is_notified_once(make):
    tray, _, notes = make()
    tray.on_info(info(last_error="disk full"))
    tray.on_info(info(last_error="disk full"))
    tray.on_info(info(last_error=None))
    tray.on_info(info(last_error="disk full"))
    assert notes == ["Dictation error: disk full"] * 2


def test_first_download_of_a_whisper_model_is_notified_at_start_and_end(make):
    tray, _, notes = make()
    tray.on_info(info(refine_download="small", loading=True))
    tray.on_info(info(refine_download="small", loading=True))
    tray.on_info(info(refine_download=None, loading=False, refine="whisper:small"))
    tray.on_info(info(refine_download=None, refine="whisper:small"))
    assert len(notes) == 2
    assert "Whisper small" in notes[0] and "first use" in notes[0]
    assert notes[1] == "The Whisper small model is ready."


def test_failed_download_is_not_announced_as_ready(make):
    tray, _, notes = make()
    tray.on_info(info(refine_download="small", loading=True))
    tray.on_info(info(refine_download=None, last_error="disk full"))
    assert len(notes) == 2 and "ready" not in notes[1] and "disk full" in notes[1]


def test_choosing_a_whisper_size_sends_set_refine(make):
    tray, client, _ = make()
    tray.on_info(
        info(
            device="cuda",
            refine_options=["none", "whisper:small", "whisper:large-v3-turbo"],
        )
    )
    assert [a.text() for a in tray.m_refine.actions()] == [
        "None",
        "Whisper small (GPU)",
        "Whisper large-v3-turbo (GPU)",
    ]
    tray.m_refine.actions()[2].trigger()
    assert client.sent == ["set-refine whisper:large-v3-turbo"]


def test_refusals_are_notified(make):
    tray, client, notes = make()
    client.command_done.emit("set-lang de", "ERR busy")
    client.command_done.emit("set-lang de", "ERR no-model")
    client.command_done.emit("toggle", None)
    client.command_done.emit("toggle", "OK ÉCOUTE")
    assert len(notes) == 3 and "loading" in notes[0]


def test_menu_follows_the_language_of_the_dictation(make):
    tray, _, _ = make()
    tray.on_info(info(lang="de"))
    assert tray.m_lang.title() == "Sprache"
    tray.on_info(None)
    assert tray.m_lang.title() == "Language"


def test_dictation_command_missing_is_notified(make, monkeypatch):
    tray, _, notes = make()
    monkeypatch.setattr(
        "vosk_cli_dictation_tray.launcher.dictation_command", lambda o=None: None
    )
    tray.launch_dictation()
    tray.download_model("fr", "big")
    assert notes == ["The dictation program was not found."] * 2


# --- avec le vrai client et le faux serveur -----------------------------------


def wait_for(qapp, predicate, timeout=3.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        qapp.processEvents()
        if predicate():
            return True
        time.sleep(0.01)
    return False


def test_end_to_end_with_the_fake_server(qapp, server):
    client = ControlClient(server.path)
    tray = DictationTray(client, Translator("en"), "en", notify=lambda m: None)
    client.start()
    try:
        assert wait_for(qapp, lambda: tray.icon_name == "listening")
        tray.activated.emit(QSystemTrayIcon.ActivationReason.Trigger)
        assert wait_for(qapp, lambda: tray.icon_name == "dictating")
        assert "toggle" in server.received
        tray.a_lang["de"].trigger()
        assert wait_for(qapp, lambda: "set-lang de" in server.received)
        assert wait_for(qapp, lambda: tray.a_lang["de"].isChecked())
        server.stop()
        assert wait_for(qapp, lambda: tray.icon_name == "off")
    finally:
        client.stop()
        tray.hide()


def test_request_times_out_quickly_on_a_silent_socket(tmp_path):
    import socket
    from vosk_cli_dictation_tray.client import INFO_TIMEOUT_S, request

    path = str(tmp_path / "x.sock")
    silent = socket.socket(socket.AF_UNIX)
    silent.bind(path)
    silent.listen(1)
    start = time.monotonic()
    assert request(path, "info", INFO_TIMEOUT_S) is None
    assert time.monotonic() - start < 0.6
    silent.close()


def test_alive_daemon_without_socket_offers_quit_not_launch(make, monkeypatch):
    tray, client, notes = make()
    monkeypatch.setattr("vosk_cli_dictation_tray.launcher.running_pid", lambda: 4242)
    launched = []
    monkeypatch.setattr(
        "vosk_cli_dictation_tray.launcher.launch_detached",
        lambda command: launched.append(command),
    )
    tray.on_info(None)
    assert tray.icon_name == "off"
    assert tray.a_launch.text() == "Quit dictation"
    assert tray.status_text() == "The dictation is not answering yet"
    tray.activated.emit(QSystemTrayIcon.ActivationReason.Trigger)
    assert launched == []
    assert notes and "already running" in notes[-1]


def test_quit_on_alive_daemon_sends_sigterm(make, monkeypatch):
    import signal

    tray, client, _ = make()
    monkeypatch.setattr("vosk_cli_dictation_tray.launcher.running_pid", lambda: 4242)
    killed = []
    monkeypatch.setattr("os.kill", lambda pid, sig: killed.append((pid, sig)))
    tray.on_info(None)
    tray.a_launch.trigger()
    assert killed == [(4242, signal.SIGTERM)] and client.sent == []


def test_tooltip_written_only_when_it_changes(make, monkeypatch):
    tray, _, _ = make()
    writes = []
    monkeypatch.setattr(tray, "setToolTip", lambda text: writes.append(text))
    tray._tip = None
    tray.on_info(info())
    tray.on_info(info())
    tray.on_info(info())
    assert len(writes) == 1
    tray.on_info(info(state="VEILLE"))
    assert len(writes) == 2


def test_running_pid_cases(monkeypatch, tmp_path):
    import os
    import subprocess
    from vosk_cli_dictation_tray import launcher

    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path))
    path = launcher.lock_path()
    assert launcher.running_pid() is None
    path.write_text("")
    assert launcher.running_pid() is None
    dead = subprocess.Popen(["true"])
    dead.wait()
    path.write_text("%d %d\n" % (dead.pid, 1))
    assert launcher.running_pid() is None
    me = os.getpid()
    path.write_text("%d %d\n" % (me, launcher._birth_ticks(me) + 1))
    assert launcher.running_pid() is None
    path.write_text("%d %d\n" % (me, launcher._birth_ticks(me)))
    assert launcher.running_pid() == me


def test_launch_detached_writes_header_in_log(monkeypatch, tmp_path):
    from vosk_cli_dictation_tray import launcher

    pid = launcher.launch_detached(launcher.Command(["true"]))
    text = launcher.log_path().read_text()
    assert "=== " in text and "pid %d" % pid in text
