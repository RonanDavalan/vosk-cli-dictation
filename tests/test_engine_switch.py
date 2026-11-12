# Changement de langue et de modèle à chaud : contrôleur de la socket, chargeur
# factice, point d'échange du fil de reconnaissance.

import json
import queue
import threading
import time

import pytest

import src.recognition as rec
from config import selection as sel
from config.config import config
from src.engine_switch import EngineSwitch, LoadedEngine
from src.recognition import MODE_STOP
from src.runtime_state import runtime_state, STATE_LISTENING, STATE_SLEEPING

INSTALLED = [
    {"folder": "vosk-model-small-fr-0.22", "path": "/m/fr-small", "lang": "fr", "size": "small"},
    {"folder": "vosk-model-fr-0.22", "path": "/m/fr-big", "lang": "fr", "size": "big"},
    {"folder": "vosk-model-small-en-us-0.15", "path": "/m/en-small", "lang": "en", "size": "small"},
    {"folder": "vosk-model-small-de-0.15", "path": "/m/de-small", "lang": "de", "size": "small"},
]


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setattr(config, "installed_models", lambda: list(INSTALLED))
    config.set_language("fr")
    runtime_state.set_state(STATE_LISTENING)
    yield
    config.set_language("fr")


class FakeLoader:
    def __init__(self, fail=None, gate=None):
        self.paths = []
        self.fail = fail
        self.gate = gate

    def __call__(self, path):
        self.paths.append(path)
        if self.gate is not None:
            self.gate.wait(timeout=5.0)
        if self.fail:
            raise RuntimeError(self.fail)
        return "model@" + path


def make_switch(loader=None, folder="vosk-model-small-fr-0.22", lang="fr", size="small"):
    return EngineSwitch(lang, folder, size, "config", loader or FakeLoader())


def wait_until(predicate, timeout=3.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if predicate():
            return True
        time.sleep(0.01)
    return False


def test_info_is_a_json_serialisable_dict():
    data = make_switch().info()
    assert json.loads(json.dumps(data)) == data
    assert data["lang"] == "fr" and data["lang_source"] == "config"
    assert data["langs"] == ["de", "en", "fr"]
    assert [m["size"] for m in data["models"]] == ["small", "big"]
    assert data["loading"] is False and data["last_error"] is None


def test_set_lang_loads_in_background_then_waits_for_the_swap_point():
    loader = FakeLoader()
    sw = make_switch(loader)
    assert sw.request("set-lang", "en") is None
    assert wait_until(sw.has_ready)
    assert loader.paths == ["/m/en-small"]
    assert sw.info()["loading"] is True      # tant que l'échange n'est pas fait
    assert sw.info()["lang"] == "fr"         # l'ancien modèle sert encore
    engine = sw.take_ready()
    sw.commit(engine)
    info = sw.info()
    assert (info["lang"], info["model"], info["loading"]) == ("en", "vosk-model-small-en-us-0.15", False)
    assert info["lang_source"] == "selection"
    assert config.current_lang == "en"
    assert sel.load_selection() == {"lang": "en", "model": "vosk-model-small-en-us-0.15"}


def test_set_lang_keeps_the_chosen_size_when_it_exists():
    loader = FakeLoader()
    sw = make_switch(loader, folder="vosk-model-small-en-us-0.15", lang="en", size="big")
    assert sw.request("set-lang", "fr") is None
    assert wait_until(sw.has_ready)
    assert loader.paths == ["/m/fr-big"]


def test_set_model_changes_size_inside_the_language():
    loader = FakeLoader()
    sw = make_switch(loader)
    assert sw.request("set-model", "vosk-model-fr-0.22") is None
    assert wait_until(sw.has_ready)
    sw.commit(sw.take_ready())
    assert sw.info()["model"] == "vosk-model-fr-0.22"
    assert config.current_lang == "fr"


def test_failed_load_keeps_the_old_model_and_fills_last_error():
    sw = make_switch(FakeLoader(fail="archive corrompue"))
    assert sw.request("set-lang", "de") is None
    assert wait_until(lambda: sw.info()["last_error"] is not None)
    info = sw.info()
    assert info["last_error"] == "archive corrompue"
    assert info["loading"] is False
    assert (info["lang"], info["model"]) == ("fr", "vosk-model-small-fr-0.22")
    assert sw.has_ready() is False
    assert config.current_lang == "fr"
    assert sel.load_selection() == {}


def test_a_new_request_clears_last_error():
    loader = FakeLoader(fail="boum")
    sw = make_switch(loader)
    sw.request("set-lang", "de")
    assert wait_until(lambda: sw.info()["last_error"])
    loader.fail = None
    assert sw.request("set-lang", "en") is None
    assert sw.info()["last_error"] is None


def test_request_while_loading_is_busy():
    gate = threading.Event()
    sw = make_switch(FakeLoader(gate=gate))
    assert sw.request("set-lang", "en") is None
    assert sw.request("set-lang", "de") == "busy"
    gate.set()
    assert wait_until(sw.has_ready)


@pytest.mark.parametrize("token", ["set-refine", "set-correction"])
def test_refine_and_correction_are_unsupported(token):
    assert make_switch().request(token, "none") == "unsupported"


def test_bad_arguments():
    sw = make_switch()
    assert sw.request("set-lang", "klingon") == "bad-argument"
    assert sw.request("set-lang", "es") == "no-model"
    assert sw.request("set-model", "vosk-model-inconnu") == "no-model"


def test_same_model_is_a_no_op_that_still_remembers_the_choice():
    loader = FakeLoader()
    sw = make_switch(loader)
    assert sw.request("set-lang", "fr") is None
    assert loader.paths == []
    assert sw.info()["lang_source"] == "selection"
    assert sel.load_selection()["lang"] == "fr"


def test_set_lang_system_follows_the_session(monkeypatch):
    for name in ("LC_ALL", "LC_MESSAGES", "LANGUAGE"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("LANG", "de_DE.UTF-8")
    loader = FakeLoader()
    sw = make_switch(loader)
    assert sw.request("set-lang", "system") is None
    assert wait_until(sw.has_ready)
    assert loader.paths == ["/m/de-small"]
    sw.commit(sw.take_ready())
    assert sw.info()["lang_source"] == "system"
    assert sel.load_selection()["lang"] == "system"


# --- point d'échange du fil de reconnaissance --------------------------------

class SeqRec:
    """Faux recognizer : rend les étapes dans l'ordre, puis du silence."""

    def __init__(self, script):
        self.script = list(script)
        self.i = 0
        self.step = ("partial", {"partial": ""})

    def AcceptWaveform(self, data):
        if self.i < len(self.script):
            self.step = self.script[self.i]
            self.i += 1
        else:
            self.step = ("partial", {"partial": ""})
        return self.step[0] == "final"

    def Result(self):
        return json.dumps(self.step[1])

    def PartialResult(self):
        return json.dumps(self.step[1])

    def Reset(self):
        pass

    def SetWords(self, flag):
        pass


class Harness:
    def __init__(self, monkeypatch, script, switch, state=STATE_LISTENING):
        self.built = []
        self.fake = SeqRec(script)
        monkeypatch.setattr(
            rec, "build_recognizer",
            lambda model, mode: (self.built.append((model, mode)), self.fake)[1])
        self.audio = queue.Queue(maxsize=64)
        self.stop = threading.Event()
        self.wake = threading.Event()
        self.wake.set()
        runtime_state.set_state(state)
        runtime_state._last_transition = 0.0
        self.thread = threading.Thread(
            target=rec.recognition_thread,
            args=("old-model", self.fake, self.audio, queue.Queue(), queue.Queue(),
                  self.stop, threading.Event(), self.wake, switch),
            daemon=True)
        self.thread.start()

    def feed(self, n=1):
        for _ in range(n):
            self.audio.put_nowait(b"\x00\x00")

    def close(self):
        self.stop.set()
        self.wake.set()
        self.thread.join(timeout=2.0)

    def models_built(self):
        return {m for m, mode in self.built if mode != MODE_STOP}


def ready_engine(switch, lang="en"):
    engine = LoadedEngine("new-model", lang, "vosk-model-small-en-us-0.15", "small", "selection")
    engine.selection_updates = {"lang": lang, "model": engine.folder}
    switch._ready = engine
    switch.loading = True
    return engine


def test_swap_happens_in_listening_between_two_utterances(monkeypatch):
    sw = make_switch()
    ready_engine(sw)
    h = Harness(monkeypatch, [], sw)
    try:
        assert wait_until(lambda: not sw.has_ready())
        assert wait_until(lambda: "new-model" in h.models_built())
        assert config.current_lang == "en"
        assert sw.info()["loading"] is False
    finally:
        h.close()


def test_swap_waits_for_the_end_of_the_utterance(monkeypatch):
    sw = make_switch()
    script = [("partial", {"partial": "bon"}), ("partial", {"partial": "bonjour"}),
              ("partial", {"partial": "bonjour à"}), ("final", {"text": "bonjour à tous", "result": []})]
    h = Harness(monkeypatch, script, sw)
    try:
        h.feed(1)                              # un énoncé commence
        assert wait_until(lambda: h.fake.i == 1)
        ready_engine(sw)
        h.feed(2)                              # il continue
        assert wait_until(lambda: h.fake.i == 3)
        time.sleep(0.25)
        assert sw.has_ready(), "échange pendant un énoncé"
        assert config.current_lang == "fr"
        h.feed(1)                              # le final clôt l'énoncé
        assert wait_until(lambda: not sw.has_ready())
        assert config.current_lang == "en"
    finally:
        h.close()


def test_swap_in_sleep_takes_the_model_and_rebuilds_on_wake(monkeypatch):
    sw = make_switch()
    h = Harness(monkeypatch, [], sw, state=STATE_SLEEPING)
    try:
        h.wake.clear()
        time.sleep(0.2)
        ready_engine(sw)
        assert wait_until(lambda: not sw.has_ready(), timeout=3.0)
        runtime_state.set_state(STATE_LISTENING)
        h.wake.set()
        assert wait_until(lambda: "new-model" in h.models_built())
    finally:
        h.close()


def test_ui_thread_follows_the_new_language():
    from src.text_processing import TextProcessor
    from src.ui import ui_thread
    config.set_language("fr")
    processor = TextProcessor("fr")
    stop = threading.Event()
    t = threading.Thread(
        target=ui_thread,
        args=(queue.Queue(), queue.Queue(), stop, processor, threading.Event(),
              threading.Event(), threading.Event()),
        daemon=True)
    t.start()
    try:
        config.set_language("en")
        assert wait_until(lambda: processor.lang == "en")
    finally:
        stop.set()
        t.join(timeout=2.0)
