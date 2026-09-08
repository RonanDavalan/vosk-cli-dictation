# config/config.py

import yaml
import os
import shutil
from colorama import Fore, Style, init as colorama_init

colorama_init(autoreset=True)

class Config:
    """
    Handles loading and accessing the project configuration from config.yaml.
    """
    def __init__(self):
        # --- CONFIG FILE LOADING ---
        self.config_path = self._get_config_path()
        if not self.config_path:
            raise FileNotFoundError("Could not find config.yaml")
        # Set by _load_config when a sibling config_local.yaml overlay is applied.
        self.local_config_path = None
        self.data = self._load_config()

        # UPDATE: Initialize theme colors from the config file.
        self._initialize_theme()

        # Set initial language based on the default model in the config
        self.current_lang = self.data.get('default_model', 'en')
        self.set_language(self.current_lang)

    @staticmethod
    def _get_config_path(project_root=None,
                         system_template='/usr/share/vosk-cli-dictation/config.yaml'):
        """Finds the config.yaml file via the XDG cascade (DOCUMENTATION_MULTILINGUE.md §10.2).

        First matching level wins:

        1. ``VOSK_CONFIG`` env var — used as-is, never auto-created.
        2. Project-relative ``config/config.yaml`` in a git checkout
           (``PROJECT_ROOT/.git`` present) — used in place, so a developer's
           edits are not shadowed by a stale XDG file.
        3. Per-user XDG config
           ``$XDG_CONFIG_HOME/vosk-cli-dictation/config.yaml``.
        4. Factory template, copied to (3) on first run: the system template
           dropped by the .deb (``system_template``), or, when that is
           absent, the ``config/config.yaml`` bundled in the tree. The
           bundled fallback covers a source-tarball install -- a
           ``git archive`` has no ``.git`` (level 2 does not fire) and no
           ``/usr/share`` template, so without it the tool could not start.

        ``project_root`` defaults to the tree holding this file; both it and
        ``system_template`` are parameters so the cascade can be unit-tested
        in isolation.
        """
        if project_root is None:
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        env_path = os.environ.get('VOSK_CONFIG')
        if env_path:
            return env_path

        bundled_config = os.path.join(project_root, 'config', 'config.yaml')
        if os.path.isdir(os.path.join(project_root, '.git')) and os.path.exists(bundled_config):
            return bundled_config

        xdg_config_home = os.environ.get('XDG_CONFIG_HOME') or os.path.join(os.path.expanduser('~'), '.config')
        user_config = os.path.join(xdg_config_home, 'vosk-cli-dictation', 'config.yaml')
        if os.path.exists(user_config):
            return user_config

        for template in (system_template, bundled_config):
            if template and os.path.exists(template):
                os.makedirs(os.path.dirname(user_config), exist_ok=True)
                shutil.copy(template, user_config)
                print(f"Created default configuration at {user_config}")
                return user_config

        return None

    def _load_config(self):
        """Loads config.yaml, then overlays an optional sibling
        ``config_local.yaml`` (git-ignored) for machine-local overrides.

        ``config_local.yaml`` sits next to the resolved config file. Its keys
        are deep-merged over the base: two mappings under the same key merge
        recursively, every other value (scalar, list) replaces the base one.
        A missing or empty overlay leaves the base config untouched.
        """
        with open(self.config_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}

        local_path = os.path.join(
            os.path.dirname(os.path.abspath(self.config_path)), 'config_local.yaml'
        )
        if os.path.exists(local_path) and not os.environ.get('VOSK_IGNORE_LOCAL_CONFIG'):
            with open(local_path, 'r', encoding='utf-8') as f:
                overrides = yaml.safe_load(f)
            if overrides:
                data = self._deep_merge(data, overrides)
                self.local_config_path = local_path
        return data

    @staticmethod
    def _deep_merge(base: dict, override: dict) -> dict:
        """Recursively merge ``override`` into ``base``; returns ``base``.

        Two mappings under the same key merge recursively; any other value in
        ``override`` (scalar, list, or a type change) replaces the base value.
        """
        for key, value in override.items():
            base_value = base.get(key)
            if isinstance(base_value, dict) and isinstance(value, dict):
                base[key] = Config._deep_merge(base_value, value)
            else:
                base[key] = value
        return base

    def _initialize_theme(self):
        """
        Loads UI colors from config.yaml and maps them to colorama objects.
        Provides sane defaults if the theme section is missing.
        """
        color_map = {
            'BLACK': Fore.BLACK, 'RED': Fore.RED, 'GREEN': Fore.GREEN,
            'YELLOW': Fore.YELLOW, 'BLUE': Fore.BLUE, 'MAGENTA': Fore.MAGENTA,
            'CYAN': Fore.CYAN, 'WHITE': Fore.WHITE, 'RESET': Fore.RESET,
        }

        user_theme = self.data.get('theme', {})
        # La couleur ne marque que les accents (titres, bandeau « prêt ») ; le
        # corps du texte prend la couleur par défaut du terminal via `RESET`,
        # lisible sur thème clair comme sombre. `BLUE` proscrit pour du courant.
        defaults = {
            'ready_message': 'GREEN', 'help_text': 'RESET', 'help_title': 'CYAN',
            'info': 'RESET', 'success': 'GREEN', 'warning': 'YELLOW', 'error': 'RED',
        }

        # Dynamically create attributes like self.color_ready_message
        for key, default_color in defaults.items():
            color_name = user_theme.get(key, default_color).upper()
            color_obj = color_map.get(color_name, Fore.WHITE) # Default to white on invalid color
            setattr(self, f"color_{key}", color_obj)

        # Style attributes
        self.BRIGHT = Style.BRIGHT
        self.RESET = Style.RESET_ALL

    # Défauts de repli des phrases de déclenchement, par langue (chantier 7
    # volet E/F). N'entrent en jeu que si la langue n'a pas de bloc
    # voice_commands dans config.yaml.
    _WAKE_PHRASE_FALLBACK = {
        'en': 'start dictation', 'fr': 'active dictée',
        'de': 'diktat starten', 'es': 'iniciar dictado',
    }
    _STOP_PHRASE_FALLBACK = {
        'en': 'stop dictation', 'fr': 'stop dictée',
        'de': 'diktat stoppen', 'es': 'terminar dictado',
    }

    def set_language(self, lang_code: str):
        """
        Sets the active language for the application.
        """
        self.current_lang = lang_code
        lang_settings = self.language_settings.get(lang_code, {})
        voice_commands = lang_settings.get('voice_commands', {})
        # Chantier 7 volet E/F : phrases de déclenchement à deux mots. Les
        # anciennes clés mono-mot start_word / stop_word sont encore lues pour
        # ne pas casser une config utilisateur non migrée.
        default_wake = self._WAKE_PHRASE_FALLBACK.get(lang_code, 'start dictation')
        default_stop = self._STOP_PHRASE_FALLBACK.get(lang_code, 'stop dictation')
        self.WAKE_PHRASE = voice_commands.get(
            'wake_phrase', voice_commands.get('start_word', default_wake)
        )
        self.STOP_PHRASE = voice_commands.get(
            'stop_phrase', voice_commands.get('stop_word', default_stop)
        )

    def recognition_setting(self, key: str, default, lang_code: str = None):
        """Résout un réglage ``recognition.<key>`` avec surcharge par langue
        (chantier 7 bis).

        ``language_settings.<lang>.<key>`` l'emporte sur ``recognition.<key>``,
        lui-même sur ``default``. Même motif que ``restricted_grammar_in_listening``
        dans ``recognition._target_mode``.
        """
        lang_code = lang_code or self.current_lang
        global_value = self.data.get('recognition', {}).get(key, default)
        return self.language_settings.get(lang_code, {}).get(key, global_value)

    def typography(self, lang_code: str = None) -> dict:
        """Typography profile for a language (chantier 7 volet F).

        Data-driven replacement for the old hardcoded French branch in
        text_processing. Missing keys fall back to a neutral profile
        (no thin space, capitalize sentence starts, ASCII quotes).
        """
        lang_code = lang_code or self.current_lang
        raw = self.language_settings.get(lang_code, {}).get('typography', {})
        return {
            'thin_space': raw.get('thin_space', False),
            'space_before': list(raw.get('space_before', [])),
            'space_after': list(raw.get('space_after', [',', '.', ';', ':', '?', '!'])),
            'capitalize_sentence_start': raw.get('capitalize_sentence_start', True),
            'quote_open': raw.get('quote_open', '"'),
            'quote_close': raw.get('quote_close', '"'),
        }

    def model_search_roots(self, path_relative: str) -> list[str]:
        """Ordered list of roots searched for a model folder (§10.3), for error messages."""
        nom_dossier = os.path.basename(path_relative)
        xdg_data_home = os.environ.get('XDG_DATA_HOME') or os.path.join(os.path.expanduser('~'), '.local', 'share')
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return [
            os.path.join(xdg_data_home, 'vosk-models', nom_dossier),
            os.path.join('/usr/share/vosk-models', nom_dossier),
            os.path.join(project_root, path_relative),
        ]

    def get_model_path_by_name(self, model_name: str) -> str | None:
        """
        Resolves the full path to a Vosk model directory via the multi-root
        cascade (DOCUMENTATION_MULTILINGUE.md §10.3): an explicit absolute
        path in config.yaml wins outright; otherwise the first existing
        directory among $XDG_DATA_HOME/vosk-models/, /usr/share/vosk-models/,
        and the dev-mode ./vosk-model/ of a git clone.
        """
        for model in self.data.get('vosk_models', []):
            if model['name'] != model_name:
                continue
            path_relative = model['path_relative']
            if os.path.isabs(path_relative):
                return path_relative if os.path.isdir(path_relative) else None
            for candidat in self.model_search_roots(path_relative):
                if os.path.isdir(candidat):
                    return candidat
            return None
        return None

    def get_lang_from_model_name(self, model_name_on_disk: str) -> str | None:
        """
        Retrieves the language code ('fr', 'en') from a model's folder name.
        """
        for model in self.data.get('vosk_models', []):
            if model['path_relative'].endswith(model_name_on_disk):
                return model['name']
        return None

    # --- Properties to access config data easily ---
    @property
    def default_model(self) -> str:
        return self.data.get('default_model', 'en')

    @property
    def default_model_name(self) -> str | None:
        path = self.get_model_path_by_name(self.default_model)
        return os.path.basename(path) if path else None

    @property
    def audio(self) -> dict:
        return self.data.get('audio', {})

    @property
    def hotkeys(self) -> dict:
        return self.data.get('hotkeys', {})

    @property
    def language_settings(self) -> dict:
        return self.data.get('language_settings', {})

    @property
    def sound_file(self) -> str:
        return self.data.get('sound_file', '')

# Singleton instance of the configuration
config = Config()
