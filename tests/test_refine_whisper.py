"""Moteur de finition Whisper : choix du matériel, poids, et transcription d'un
WAV du corpus du banc quand faster-whisper et les poids sont présents."""

import os
import re
import sys
import types
import wave

import pytest

from src.refine import RefineUnavailable
from src.refine import whisper_engine as we

CORPUS = os.environ.get("VOSK_REFINE_TEST_CORPUS", "")
WAV = os.path.join(CORPUS, "audio", "fr", "fr_FR-siwis-medium", "propre", "01.wav")
REFERENCE = os.path.join(CORPUS, "corpus", "fr.tape.txt")


@pytest.fixture(autouse=True)
def fresh_probes():
    we.gpu_detected.cache_clear()
    we.cublas_loadable.cache_clear()
    yield
    we.gpu_detected.cache_clear()
    we.cublas_loadable.cache_clear()


def test_models_dir_follows_xdg_data_home(monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", "/data")
    assert we.models_dir() == "/data/vosk-cli-dictation/whisper-models"


def test_is_cached_reads_the_hub_layout(tmp_path):
    assert not we.is_cached("tiny", str(tmp_path))
    (tmp_path / "models--Systran--faster-whisper-tiny" / "snapshots" / "abc").mkdir(
        parents=True
    )
    assert we.is_cached("tiny", str(tmp_path))
    assert not we.is_cached("base", str(tmp_path))


def test_device_cuda_needs_gpu_and_cublas(monkeypatch):
    monkeypatch.setattr(we, "gpu_detected", lambda: True)
    monkeypatch.setattr(we, "cublas_loadable", lambda: True)
    assert we.resolve_device("auto") == "cuda"
    assert we.resolve_device("cuda") == "cuda"
    assert we.resolve_device("cpu") == "cpu"


def test_device_auto_falls_back_to_cpu_without_cublas(monkeypatch):
    monkeypatch.setattr(we, "gpu_detected", lambda: True)
    monkeypatch.setattr(we, "cublas_loadable", lambda: False)
    assert we.resolve_device("auto") == "cpu"
    assert we.probe_device("cuda") == "cpu"
    with pytest.raises(RefineUnavailable) as err:
        we.resolve_device("cuda")
    assert err.value.code == "cuda-missing"
    assert "libcublas12" in err.value.detail


def test_device_cuda_without_gpu_says_so(monkeypatch):
    monkeypatch.setattr(we, "gpu_detected", lambda: False)
    monkeypatch.setattr(we, "cublas_loadable", lambda: True)
    assert we.resolve_device("auto") == "cpu"
    with pytest.raises(RefineUnavailable) as err:
        we.resolve_device("cuda")
    assert err.value.code == "no-gpu"


def test_compute_type_defaults_follow_the_device():
    assert we.resolve_compute_type("auto", "cuda") == "float16"
    assert we.resolve_compute_type("auto", "cpu") == "int8"
    assert we.resolve_compute_type("int8_float16", "cuda") == "int8_float16"


def test_cpu_leaves_a_core_to_vosk(monkeypatch):
    monkeypatch.setattr(os, "cpu_count", lambda: 4)
    assert we.cpu_threads() == 3
    monkeypatch.setattr(os, "cpu_count", lambda: 1)
    assert we.cpu_threads() == 1
    monkeypatch.setattr(os, "cpu_count", lambda: None)
    assert we.cpu_threads() == 1


def test_unknown_size_is_refused():
    with pytest.raises(RefineUnavailable) as err:
        we.WhisperEngine("gigantic")
    assert err.value.code == "bad-size"


def test_missing_faster_whisper_makes_the_engine_unavailable(monkeypatch):
    monkeypatch.setattr(we, "missing_module", lambda: "faster_whisper")
    engine = we.WhisperEngine("tiny")
    with pytest.raises(RefineUnavailable) as err:
        engine.load()
    assert err.value.code == "missing-module"


def test_refine_before_load_is_refused():
    with pytest.raises(RefineUnavailable):
        we.WhisperEngine("tiny").refine(b"\0\0", "fr")


def _words(text):
    return re.findall(r"[\w'’-]+", text.lower())


def _word_errors(reference, hypothesis):
    r, h = _words(reference), _words(hypothesis)
    row = list(range(len(h) + 1))
    for i, rw in enumerate(r, 1):
        new = [i]
        for j, hw in enumerate(h, 1):
            new.append(min(row[j] + 1, new[j - 1] + 1, row[j - 1] + (rw != hw)))
        row = new
    return row[-1] / max(1, len(r))


@pytest.mark.skipif(we.missing_module() is not None, reason="faster-whisper absent")
@pytest.mark.skipif(
    not os.path.exists(WAV),
    reason="VOSK_REFINE_TEST_CORPUS ne désigne pas le corpus du banc",
)
def test_transcribes_a_corpus_wav():
    """Sur fichier, aucune instance : le WAV de la première phrase du corpus
    français. Le dossier du corpus, la taille et le dossier de poids se règlent par
    VOSK_REFINE_TEST_CORPUS, VOSK_REFINE_TEST_SIZE et VOSK_REFINE_TEST_MODELS."""
    size = os.environ.get("VOSK_REFINE_TEST_SIZE", "tiny")
    directory = os.environ.get("VOSK_REFINE_TEST_MODELS") or None
    with wave.open(WAV, "rb") as w:
        assert (w.getframerate(), w.getnchannels(), w.getsampwidth()) == (16000, 1, 2)
        pcm = w.readframes(w.getnframes())
    engine = we.WhisperEngine(size, directory=directory)
    engine.load()
    text = engine.refine(pcm, "fr")
    with open(REFERENCE, encoding="utf-8") as f:
        reference = f.readline().strip()
    rate = _word_errors(reference, text)
    print(
        f"{size} {engine.device()} {engine.compute_type}: {text!r} (erreur {rate:.0%})"
    )
    assert text
    assert rate <= (0.6 if size in ("tiny", "base") else 0.3)


def test_unwritable_models_directory_is_a_load_failure(monkeypatch, tmp_path):
    fake = types.ModuleType("faster_whisper")
    fake.WhisperModel = lambda *a, **k: None
    monkeypatch.setitem(sys.modules, "faster_whisper", fake)
    monkeypatch.setattr(we, "missing_module", lambda: None)
    monkeypatch.setattr(we, "resolve_device", lambda requested: "cpu")

    def refuse(*args, **kwargs):
        raise PermissionError("lecture seule")

    monkeypatch.setattr(os, "makedirs", refuse)
    engine = we.WhisperEngine("tiny", "cpu", "auto", directory=str(tmp_path / "w"))
    with pytest.raises(RefineUnavailable) as err:
        engine.load()
    assert err.value.code == "load-failed"
