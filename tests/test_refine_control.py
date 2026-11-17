# Pilotage de la finition : choix au lancement, set-refine sur la socket, choix
# mémorisé, ce que info annonce, lignes de --diagnose. Le moteur est un faux.

import time

import pytest

from config import selection as sel
from config.config import config
from src.control_socket import _handle
from src.engine_switch import EngineSwitch
from src.refine import RefineEngine, RefineUnavailable
from src.refine import control as ctl
from src.refine import whisper_engine as we
from src.runtime_state import STATE_LISTENING, runtime_state

INSTALLED = [
    {
        "folder": "vosk-model-small-fr-0.22",
        "path": "/m/fr-small",
        "lang": "fr",
        "size": "small",
    },
]


class FakeWhisper(RefineEngine):
    built = []
    fail = None

    def __init__(self, size, device="auto", compute_type="auto"):
        self.size = size
        self.spec = "whisper:" + size
        self.built.append(size)

    def load(self):
        if FakeWhisper.fail:
            raise RefineUnavailable("load-failed", FakeWhisper.fail)

    def device(self):
        return "cpu"

    def refine(self, pcm, language):
        return "ok"


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setattr(config, "installed_models", lambda: list(INSTALLED))
    monkeypatch.setattr(we, "missing_module", lambda: None)
    monkeypatch.setattr(we, "probe_device", lambda requested="auto": "cpu")
    monkeypatch.setattr(we, "WhisperEngine", FakeWhisper)
    FakeWhisper.built = []
    FakeWhisper.fail = None
    config.set_language("fr")
    runtime_state.set_state(STATE_LISTENING)
    yield


def wait_until(predicate, timeout=3.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if predicate():
            return True
        time.sleep(0.01)
    return False


def make(conf=None, selected=None):
    delivered = []
    controller = ctl.RefineController(lambda *a: delivered.append(a), conf, selected)
    switch = EngineSwitch(
        "fr", "vosk-model-small-fr-0.22", "small", "config", refine=controller
    )
    return switch, controller


def test_default_is_no_refinement_and_changes_nothing():
    switch, controller = make()
    controller.start()
    assert controller.spec == "none" and not controller.pipeline.active()
    info = switch.info()
    assert info["refine"] == "none" and info["loading"] is False


def test_configured_spec_follows_the_survey_defaults(monkeypatch):
    monkeypatch.setattr(we, "probe_device", lambda requested="auto": "cuda")
    assert ctl.configured_spec({"engine": "whisper", "model": "auto"}) == (
        "whisper:large-v3-turbo",
        None,
    )
    monkeypatch.setattr(we, "probe_device", lambda requested="auto": "cpu")
    assert ctl.configured_spec({"engine": "whisper", "model": "auto"}) == (
        "none",
        "cpu-no-default",
    )
    assert ctl.configured_spec({"engine": "whisper", "model": "small"}) == (
        "whisper:small",
        None,
    )
    assert ctl.configured_spec({"engine": "whisper", "model": "huge"}) == (
        "none",
        "bad-model",
    )
    assert ctl.configured_spec({"engine": "none", "model": "small"}) == ("none", None)


def test_start_loads_the_configured_engine_in_the_background():
    switch, controller = make({"engine": "whisper", "model": "base"})
    controller.start()
    assert wait_until(lambda: controller.pipeline.active())
    assert controller.spec == "whisper:base"
    assert sel.load_selection() == {}  # le lancement ne mémorise rien


def test_a_remembered_choice_wins_over_the_configuration():
    switch, controller = make(
        {"engine": "whisper", "model": "base"}, selected="whisper:small"
    )
    controller.start()
    assert wait_until(lambda: controller.spec == "whisper:small")


def test_set_refine_on_the_socket_loads_and_remembers():
    switch, controller = make()
    assert _handle("set-refine whisper:tiny", None, switch) == "OK ÉCOUTE"
    assert wait_until(lambda: controller.spec == "whisper:tiny")
    assert controller.pipeline.active()
    assert sel.load_selection() == {"refine": "whisper:tiny"}
    info = switch.info()
    assert info["refine"] == "whisper:tiny" and info["device"] == "cpu"
    assert (
        "whisper:large-v3-turbo" in info["refine_options"]
        and info["refine_options"][0] == "none"
    )
    assert info["refine_reason"] is None


def test_set_refine_none_stops_the_refinement_and_remembers():
    switch, controller = make({"engine": "whisper", "model": "base"})
    controller.start()
    assert wait_until(lambda: controller.pipeline.active())
    assert _handle("set-refine none", None, switch) == "OK ÉCOUTE"
    assert not controller.pipeline.active() and controller.spec == "none"
    assert sel.load_selection() == {"refine": "none"}


def test_set_refine_refusals():
    switch, controller = make()
    assert _handle("set-refine", None, switch) == "ERR bad-argument"
    assert _handle("set-refine whisper:gigantic", None, switch) == "ERR bad-argument"
    assert _handle("set-refine ollama:gemma", None, switch) == "ERR bad-argument"
    assert _handle("set-refine WHISPER:small", None, switch) == "ERR bad-argument"


def test_set_refine_is_busy_while_loading_and_info_says_loading():
    switch, controller = make()
    gate = []

    class Slow(FakeWhisper):
        def load(self):
            while not gate:
                time.sleep(0.01)

    we.WhisperEngine = Slow
    assert _handle("set-refine whisper:small", None, switch) == "OK ÉCOUTE"
    assert switch.info()["loading"] is True
    assert _handle("set-refine whisper:base", None, switch) == "ERR busy"
    assert _handle("set-lang en", None, switch) == "ERR busy"
    gate.append(1)
    assert wait_until(lambda: controller.spec == "whisper:small")
    assert switch.info()["loading"] is False


def test_failed_load_keeps_the_previous_engine_and_says_why():
    switch, controller = make({"engine": "whisper", "model": "base"})
    controller.start()
    assert wait_until(lambda: controller.spec == "whisper:base")
    FakeWhisper.fail = "disque plein"
    assert _handle("set-refine whisper:small", None, switch) == "OK ÉCOUTE"
    assert wait_until(lambda: not controller.loading)
    assert controller.spec == "whisper:base" and controller.pipeline.active()
    assert "disque plein" in switch.info()["last_error"]
    assert sel.load_selection() == {}


def test_download_is_announced_until_the_weights_are_there(monkeypatch):
    switch, controller = make()
    seen = []

    class Download(FakeWhisper):
        def load(self):
            seen.append(controller.downloading)

    we.WhisperEngine = Download
    controller.request("whisper:small")
    assert wait_until(lambda: controller.spec == "whisper:small")
    assert seen == ["small"] and controller.downloading is None


def test_no_download_announced_when_weights_are_cached(tmp_path):
    switch, controller = make()
    (
        tmp_path
        / "data"
        / "vosk-cli-dictation"
        / "whisper-models"
        / "models--Systran--faster-whisper-small"
        / "snapshots"
        / "x"
    ).mkdir(parents=True)
    seen = []

    class Cached(FakeWhisper):
        def load(self):
            seen.append(controller.downloading)

    we.WhisperEngine = Cached
    controller.request("whisper:small")
    assert wait_until(lambda: controller.spec == "whisper:small")
    assert seen == [None]


def test_without_faster_whisper_the_entry_is_off_with_its_reason(monkeypatch):
    monkeypatch.setattr(we, "missing_module", lambda: "faster_whisper")
    switch, controller = make()
    info = switch.info()
    assert info["refine_options"] == ["none"]
    assert "faster-whisper" in info["refine_reason"]
    assert _handle("set-refine whisper:small", None, switch) == "ERR unsupported"
    assert _handle("set-refine none", None, switch) == "OK ÉCOUTE"


def test_without_controller_set_refine_is_unsupported():
    switch = EngineSwitch("fr", "vosk-model-small-fr-0.22", "small", "config")
    assert _handle("set-refine none", None, switch) == "ERR unsupported"
    assert switch.info()["refine"] == "none" and "refine_options" not in switch.info()


def test_reset_selection_goes_back_to_the_configured_finish():
    switch, controller = make({"engine": "whisper", "model": "base"})
    controller.start()
    assert wait_until(lambda: controller.spec == "whisper:base")
    controller.request("none")
    assert controller.spec == "none"
    assert _handle("reset-selection", None, switch) == "OK ÉCOUTE"
    assert wait_until(lambda: controller.spec == "whisper:base")


def test_diagnose_lines_report_the_missing_module_only_when_wanted(monkeypatch):
    monkeypatch.setattr(we, "missing_module", lambda: "faster_whisper")
    monkeypatch.setitem(config.data, "refine", {"engine": "none"})
    lines = ctl.diagnose_lines()
    assert all(ok for ok, _l, _d in lines)
    monkeypatch.setitem(config.data, "refine", {"engine": "whisper", "model": "small"})
    lines = ctl.diagnose_lines()
    assert [ok for ok, label, _d in lines if label == "faster-whisper"] == [False]


def test_diagnose_lines_give_the_libcublas_remedy(monkeypatch):
    monkeypatch.setattr(we, "gpu_detected", lambda: True)
    monkeypatch.setattr(we, "cublas_loadable", lambda: False)
    monkeypatch.setitem(config.data, "refine", {"engine": "whisper", "model": "small"})
    text = " ".join(d for _ok, _l, d in ctl.diagnose_lines())
    assert "libcublas.so.12" in text and "apt install libcublas12" in text
