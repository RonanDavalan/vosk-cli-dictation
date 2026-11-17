# src/refine/whisper_engine.py
#
# Moteur de finition faster-whisper. L'import de faster_whisper est facultatif :
# sans lui le moteur est indisponible et dit pourquoi.

import functools
import glob
import os

from src.refine import RefineEngine, RefineUnavailable

SIZES = ("tiny", "base", "small", "medium", "large-v3-turbo")
# Taille de la finition quand un GPU sert : la plus grande dont le 95e centile
# de latence par énoncé reste sous 500 ms (relevé du banc des moteurs). Aucune
# taille n'y parvient sur un processeur : pas de taille par défaut.
GPU_DEFAULT_SIZE = "large-v3-turbo"
CUBLAS_SONAME = "libcublas.so.12"
CUBLAS_REMEDY = "apt install libcublas12 libcublaslt12"
SPEC_PREFIX = "whisper:"


def models_dir() -> str:
    base = os.environ.get("XDG_DATA_HOME") or os.path.join(
        os.path.expanduser("~"), ".local", "share"
    )
    return os.path.join(base, "vosk-cli-dictation", "whisper-models")


def is_cached(size: str, directory: str = None) -> bool:
    """Les poids de cette taille sont-ils déjà sous `directory` ?"""
    pattern = os.path.join(
        directory or models_dir(), f"models--*--faster-whisper-{size}", "snapshots", "*"
    )
    return bool(glob.glob(pattern))


def missing_module():
    """None si faster_whisper s'importe, sinon le nom de ce qui manque."""
    try:
        import faster_whisper  # noqa: F401
    except ImportError as e:
        return e.name or "faster_whisper"
    return None


@functools.lru_cache(maxsize=1)
def gpu_detected() -> bool:
    try:
        import ctranslate2

        return ctranslate2.get_cuda_device_count() > 0
    except Exception:
        return False


@functools.lru_cache(maxsize=1)
def cublas_loadable() -> bool:
    """Sonde directe de libcublas : CTranslate2 ne vérifie que la présence d'un
    GPU et n'ouvre la bibliothèque qu'au premier transcribe(), d'où un échec
    tardif quand elle manque."""
    import ctypes

    try:
        ctypes.CDLL(CUBLAS_SONAME)
        return True
    except OSError:
        return False


def resolve_device(requested: str) -> str:
    """`cuda` si CTranslate2 voit un GPU et que libcublas se charge, sinon
    `cpu`. `cuda` demandé sans l'un des deux lève RefineUnavailable ; `auto`
    replie sur `cpu`."""
    if requested == "cpu":
        return "cpu"
    present = gpu_detected()
    if requested == "cuda":
        if present and cublas_loadable():
            return "cuda"
        raise RefineUnavailable("cuda-missing" if present else "no-gpu", CUBLAS_REMEDY)
    return "cuda" if present and cublas_loadable() else "cpu"


def probe_device(requested: str = "auto") -> str:
    """Matériel qui servirait, sans lever : `cpu` si le GPU est inutilisable."""
    try:
        return resolve_device(requested)
    except RefineUnavailable:
        return "cpu"


def cpu_threads() -> int:
    """Sur processeur, un cœur reste à Vosk : son décodage doit tenir le temps
    réel pendant que la finition travaille."""
    return max(1, (os.cpu_count() or 2) - 1)


def resolve_compute_type(requested: str, device: str) -> str:
    if requested and requested != "auto":
        return requested
    return "float16" if device == "cuda" else "int8"


class WhisperEngine(RefineEngine):
    def __init__(
        self,
        size: str,
        device: str = "auto",
        compute_type: str = "auto",
        directory: str = None,
    ):
        if size not in SIZES:
            raise RefineUnavailable("bad-size", size)
        self.size = size
        self.spec = SPEC_PREFIX + size
        self._requested_device = device
        self._requested_compute = compute_type
        self._directory = directory or models_dir()
        self._model = None
        self._device = None
        self.compute_type = None

    def device(self):
        return self._device

    def load(self) -> None:
        missing = missing_module()
        if missing:
            raise RefineUnavailable("missing-module", missing)
        from faster_whisper import WhisperModel

        self._device = resolve_device(self._requested_device)
        self.compute_type = resolve_compute_type(self._requested_compute, self._device)
        try:
            os.makedirs(self._directory, exist_ok=True)
            self._model = WhisperModel(
                self.size,
                device=self._device,
                compute_type=self.compute_type,
                download_root=self._directory,
                cpu_threads=cpu_threads() if self._device == "cpu" else 0,
            )
        except Exception as e:
            raise RefineUnavailable("load-failed", f"{self.size}: {e}") from e

    def refine(self, pcm: bytes, language: str) -> str:
        if self._model is None:
            raise RefineUnavailable("not-loaded", self.size)
        import numpy as np

        audio = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0
        segments, _info = self._model.transcribe(
            audio,
            language=language or None,
            beam_size=1,
            temperature=0.0,
            vad_filter=False,
            condition_on_previous_text=False,
        )
        return "".join(segment.text for segment in segments).strip()

    def close(self) -> None:
        self._model = None
