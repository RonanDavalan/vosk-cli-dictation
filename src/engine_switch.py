# src/engine_switch.py
#
# Changer de langue ou de modèle sans relancer la dictée. Une requête de la
# socket (`set-lang`, `set-model`) charge le nouveau modèle dans un fil à part
# pendant que l'ancien continue de servir ; le fil de reconnaissance prend le
# modèle chargé entre deux énoncés (point d'échange de src/recognition.py), puis
# la langue de la session, les messages et le choix mémorisé suivent.

import threading

from config.config import config
from config.selection import SUPPORTED_LANGS, SYSTEM, save_selection, system_language
from src.i18n import get_translation, set_ui_language
from src.runtime_state import runtime_state

# Réglages de finition et de correction : aucun moteur n'existe encore.
UNSUPPORTED_TOKENS = ("set-refine", "set-correction")


def default_loader(path):
    from vosk import Model
    return Model(path)


class LoadedEngine:
    """Un modèle chargé qui attend le point d'échange."""

    def __init__(self, model, lang, folder, size, lang_source):
        self.model = model
        self.lang = lang
        self.folder = folder
        self.size = size
        self.lang_source = lang_source


def choose_model(lang: str, prefer_size: str = "small"):
    """Modèle installé de `lang` à la taille voulue, sinon le petit, sinon le
    premier. None si aucun modèle de cette langue n'est installé."""
    candidates = [m for m in config.installed_models() if m["lang"] == lang]
    for wanted in (prefer_size, "small"):
        for m in candidates:
            if m["size"] == wanted:
                return m
    return candidates[0] if candidates else None


class EngineSwitch:
    """Contrôleur de la socket (`info`, `set-*`) et file d'échange du fil de
    reconnaissance. `loader(path)` rend l'objet modèle (un faux dans les tests)."""

    def __init__(self, lang, folder, size="small", lang_source="config", loader=default_loader):
        self._loader = loader
        self._lock = threading.Lock()
        self._ready = None
        self._thread = None
        self.lang = lang
        self.folder = folder
        self.size = size
        self.lang_source = lang_source
        self.loading = False
        self.last_error = None

    # --- côté socket ------------------------------------------------------- #

    def info(self) -> dict:
        installed = config.installed_models()
        with self._lock:
            return {
                "state": runtime_state.snapshot()["state"],
                "lang": self.lang,
                "lang_source": self.lang_source,
                "langs": sorted({m["lang"] for m in installed}),
                "model": self.folder,
                "models": [{"folder": m["folder"], "size": m["size"]}
                           for m in installed if m["lang"] == self.lang],
                "refine": "none",
                "device": None,
                "correction": "none",
                "loading": self.loading,
                "last_error": self.last_error,
            }

    def request(self, token: str, arg: str):
        """Prend une requête `set-*`. Rend None si elle est acceptée, sinon la
        raison du refus (le mot qui suit « ERR »)."""
        if token in UNSUPPORTED_TOKENS:
            return "unsupported"
        with self._lock:
            if self.loading:
                return "busy"
        if token == "set-lang":
            return self._request_lang(arg)
        if token == "set-model":
            return self._request_model(arg)
        return "unknown-command"

    def _request_lang(self, arg):
        if arg != SYSTEM and arg not in SUPPORTED_LANGS:
            return "bad-argument"
        if arg == SYSTEM:
            system = system_language()
            lang = system if system in {m["lang"] for m in config.installed_models()} else "en"
            source = "system"
        else:
            lang, source = arg, "selection"
        target = choose_model(lang, self.size)
        if target is None:
            return "no-model"
        return self._begin(target, source, arg)

    def _request_model(self, arg):
        target = config.installed_model(arg)
        if target is None:
            return "no-model"
        return self._begin(target, "selection", target["lang"])

    def _begin(self, target, lang_source, lang_choice):
        updates = {"lang": lang_choice, "model": target["folder"]}
        if target["folder"] == self.folder:
            with self._lock:
                self.lang_source = lang_source
            save_selection(updates)
            return None
        with self._lock:
            self.loading = True
            self.last_error = None
        self._thread = threading.Thread(
            target=self._load, args=(target, lang_source, updates), daemon=True)
        self._thread.start()
        return None

    def _load(self, target, lang_source, updates):
        _ = get_translation()
        print(f"\n{config.color_info}{_('Attempting to load model:')} {target['folder']}...{config.RESET}")
        try:
            model = self._loader(target["path"])
        except Exception as e:
            with self._lock:
                self.loading = False
                self.last_error = str(e)
            print(f"\n{config.color_error}"
                  f"{_('Model change failed, keeping the current model: {error}').format(error=e)}"
                  f"{config.RESET}")
            return
        engine = LoadedEngine(model, target["lang"], target["folder"], target["size"], lang_source)
        engine.selection_updates = updates
        with self._lock:
            self._ready = engine

    # --- côté fil de reconnaissance ---------------------------------------- #

    def has_ready(self) -> bool:
        with self._lock:
            return self._ready is not None

    def take_ready(self):
        with self._lock:
            engine, self._ready = self._ready, None
            return engine

    def commit(self, engine) -> None:
        """Appelé par le fil de reconnaissance au point d'échange : la langue
        de la session, des messages et du `TextProcessor` (que ui_thread
        rafraîchit quand `config.current_lang` change), puis le choix mémorisé."""
        if engine.lang != config.current_lang:
            config.set_language(engine.lang)
            set_ui_language(engine.lang)
        save_selection(engine.selection_updates)
        _ = get_translation()
        print(f"\n{config.color_success}"
              f"{_('Model switched: {model_name}').format(model_name=engine.folder)}"
              f"{config.RESET}")
        with self._lock:
            self.lang = engine.lang
            self.folder = engine.folder
            self.size = engine.size
            self.lang_source = engine.lang_source
            self.loading = False
