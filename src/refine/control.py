# src/refine/control.py
#
# Pilotage de la finition : choix du moteur au lancement (config.yaml, puis
# choix mémorisé), changement à chaud par la socket (`set-refine`), ce que
# `info` annonce à l'icône, et les lignes de `--diagnose`.

import threading
import time

from config.config import config
from config.selection import save_selection
from src.i18n import get_translation
from src.refine import NONE, RefineUnavailable
from src.refine import whisper_engine as we
from src.refine.pipeline import RefinePipeline

DEFAULTS = {
    "engine": NONE,
    "model": "auto",
    "device": "auto",
    "compute_type": "auto",
    "timeout_ms": 2000,
}
REPORT_INTERVAL_S = 10.0


def settings() -> dict:
    return {**DEFAULTS, **(config.data.get("refine") or {})}


def valid_spec(spec) -> bool:
    return spec == NONE or (
        isinstance(spec, str)
        and spec.startswith(we.SPEC_PREFIX)
        and spec[len(we.SPEC_PREFIX) :] in we.SIZES
    )


def configured_spec(conf: dict):
    """(spec, note) d'après la clé `refine` de config.yaml. `model: auto` donne
    la taille que le relevé du banc retient quand un GPU sert, et aucune finition
    sur un processeur, où aucune taille ne tient sous 500 ms par énoncé."""
    if conf.get("engine") != "whisper":
        return NONE, None
    model = conf.get("model")
    if model == "auto":
        if we.probe_device(conf.get("device", "auto")) == "cuda":
            return we.SPEC_PREFIX + we.GPU_DEFAULT_SIZE, None
        return NONE, "cpu-no-default"
    spec = we.SPEC_PREFIX + str(model)
    return (spec, None) if valid_spec(spec) else (NONE, "bad-model")


def reason_text(error: RefineUnavailable) -> str:
    _ = get_translation()
    code, detail = error.code, error.detail
    if code == "missing-module":
        return _(
            "faster-whisper is not installed in this dictation (pip install faster-whisper)"
        )
    if code == "no-gpu":
        return _("device: cuda is set but no GPU is detected; use device: auto or cpu")
    if code == "cuda-missing":
        return _(
            "device: cuda is set but {lib} cannot be loaded; install it ({remedy}) or use device: cpu"
        ).format(lib=we.CUBLAS_SONAME, remedy=detail)
    if code == "bad-size":
        return _("unknown Whisper size: {size}").format(size=detail)
    if code == "load-failed":
        return _("cannot load the Whisper model ({detail})").format(detail=detail)
    return detail or code


def note_text(note: str) -> str:
    _ = get_translation()
    if note == "cpu-no-default":
        return _(
            "Refinement is off: no Whisper size keeps up on a processor. Choose one in refine.model or in the icon menu."
        )
    return _("refine.model is not a known Whisper size; refinement is off.")


class RefineController:
    """Possède la file de finition (`pipeline`) et le moteur qui la sert.
    `deliver(text, words, refined)` rend les énoncés à l'UI."""

    def __init__(self, deliver, conf: dict = None, selected: str = None):
        self.conf = {**DEFAULTS, **(conf or {})}
        self.pipeline = RefinePipeline(deliver, self.conf["timeout_ms"], self._report)
        self.spec = NONE
        self.loading = False
        self.last_error = None
        self.downloading = None
        self._lock = threading.Lock()
        self._device = None
        self._last_report = 0.0
        self._selected = selected if valid_spec(selected) else None
        self.note = None
        threading.Thread(target=self._probe, daemon=True).start()

    def _probe(self):
        if we.missing_module() is None:
            self._device = we.probe_device(self.conf["device"])

    def _report(self, kind, detail):
        now = time.monotonic()
        if now - self._last_report < REPORT_INTERVAL_S:
            return
        self._last_report = now
        _ = get_translation()
        print(
            f"\n{config.color_warning}"
            f"{_('Refinement failed, typing the Vosk text: {error}').format(error=detail)}"
            f"{config.RESET}"
        )

    # --- lancement et changement à chaud ---------------------------------------- #

    def start(self) -> None:
        """Choix au lancement : le choix mémorisé, sinon config.yaml. Le moteur
        se charge en arrière-plan ; le texte de Vosk est tapé en attendant."""
        if self._selected is not None:
            spec = self._selected
        else:
            spec, self.note = configured_spec(self.conf)
            if self.note:
                _ = get_translation()
                print(f"{config.color_info}{note_text(self.note)}{config.RESET}")
        if spec != NONE:
            self._begin(spec, persist=False)

    def reset(self) -> None:
        """« Revenir à la configuration » : la finition de config.yaml."""
        spec, self.note = configured_spec(self.conf)
        self._selected = None
        if spec == self.spec:
            return
        if spec == NONE:
            self._apply(None, NONE)
        else:
            self._begin(spec, persist=False)

    def request(self, arg: str):
        """Prend `set-refine <none|whisper:taille>`. None si acceptée, sinon la
        raison du refus."""
        if not valid_spec(arg):
            return "bad-argument"
        if self.loading:
            return "busy"
        if arg == NONE:
            self._apply(None, NONE)
            save_selection({"refine": NONE})
            return None
        if we.missing_module() is not None:
            return "unsupported"
        if arg == self.spec:
            save_selection({"refine": arg})
            return None
        self._begin(arg, persist=True)
        return None

    def _begin(self, spec, persist):
        with self._lock:
            self.loading = True
            self.last_error = None
        threading.Thread(target=self._load, args=(spec, persist), daemon=True).start()

    def _load(self, spec, persist):
        _ = get_translation()
        size = spec[len(we.SPEC_PREFIX) :]
        try:
            engine = we.WhisperEngine(
                size, self.conf["device"], self.conf["compute_type"]
            )
            if not we.is_cached(size):
                self.downloading = size
                print(
                    f"\n{config.color_info}"
                    f"{_('Downloading the Whisper {size} model (first use, kept in {path})...').format(size=size, path=we.models_dir())}"
                    f"{config.RESET}"
                )
            else:
                print(
                    f"\n{config.color_info}"
                    f"{_('Loading the Whisper {size} model...').format(size=size)}{config.RESET}"
                )
            engine.load()
        except RefineUnavailable as e:
            text = reason_text(e)
            with self._lock:
                self.loading = False
                self.last_error = text
            self.downloading = None
            print(
                f"\n{config.color_error}"
                f"{_('Refinement change failed, keeping the current setting: {error}').format(error=text)}"
                f"{config.RESET}"
            )
            return
        self.downloading = None
        self._apply(engine, spec)
        if persist:
            save_selection({"refine": spec})
        print(
            f"\n{config.color_success}"
            f"{_('Refinement ready: {spec} on {device}.').format(spec=spec, device=engine.device().upper())}"
            f"{config.RESET}"
        )
        if engine.device() == "cpu" and we.gpu_detected() and not we.cublas_loadable():
            print(
                f"{config.color_warning}"
                f"{_('A GPU is present but {lib} cannot be loaded; using the processor ({remedy}).').format(lib=we.CUBLAS_SONAME, remedy=we.CUBLAS_REMEDY)}"
                f"{config.RESET}"
            )

    def _apply(self, engine, spec):
        self.pipeline.set_engine(engine)
        with self._lock:
            self.spec = spec
            self.loading = False

    # --- ce que la socket annonce ------------------------------------------------- #

    def options(self):
        if we.missing_module() is not None:
            return [NONE]
        return [NONE] + [we.SPEC_PREFIX + s for s in we.SIZES]

    def reason(self):
        missing = we.missing_module()
        if missing is None:
            return None
        return reason_text(RefineUnavailable("missing-module", missing))

    def info(self) -> dict:
        engine = self.pipeline.engine
        return {
            "refine": self.spec,
            "refine_options": self.options(),
            "refine_reason": self.reason(),
            "refine_download": self.downloading,
            "device": engine.device() if engine is not None else self._device,
        }

    def shutdown(self):
        self.pipeline.shutdown()


def diagnose_lines(selected: str = None):
    """(ok, libellé, détail) pour la section « Refinement » de --diagnose. Un
    manque de faster-whisper n'est un échec que si config.yaml demande la
    finition."""
    _ = get_translation()
    conf = settings()
    spec, note = (selected, None) if valid_spec(selected) else configured_spec(conf)
    origin = "selection" if valid_spec(selected) else "config"
    lines = [(True, _("Engine"), "{}  ({})".format(spec, origin))]
    if note:
        lines.append((True, _("Note"), note_text(note)))
    missing = we.missing_module()
    wanted = conf["engine"] == "whisper" or (valid_spec(selected) and selected != NONE)
    if missing:
        lines.append(
            (
                not wanted,
                "faster-whisper",
                _("missing (pip install faster-whisper)")
                if wanted
                else _("not installed (optional)"),
            )
        )
    else:
        lines.append((True, "faster-whisper", _("found")))
        gpu = we.gpu_detected()
        cublas = we.cublas_loadable() if gpu else None
        device = we.probe_device(conf["device"])
        detail = device.upper()
        if gpu and not cublas:
            detail += "  " + _(
                "GPU present but {lib} cannot be loaded ({remedy})"
            ).format(lib=we.CUBLAS_SONAME, remedy=we.CUBLAS_REMEDY)
        elif not gpu:
            detail += "  " + _("no GPU detected")
        lines.append((True, _("Hardware"), detail))
        cached = [s for s in we.SIZES if we.is_cached(s)]
        lines.append(
            (
                True,
                _("Models directory"),
                "{}  ({})".format(
                    we.models_dir(), ", ".join(cached) if cached else _("no model yet")
                ),
            )
        )
    lines.append((True, _("Typing delay limit"), "{} ms".format(conf["timeout_ms"])))
    return lines
