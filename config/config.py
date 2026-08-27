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
        self.data = self._load_config()

        # UPDATE: Initialize theme colors from the config file.
        self._initialize_theme()

        # Set initial language based on the default model in the config
        self.current_lang = self.data.get('default_model', 'en')
        self.set_language(self.current_lang)

    def _get_config_path(self):
        """Finds the config.yaml file via the XDG cascade (DOCUMENTATION_MULTILINGUE.md §10.2).

        First matching level wins: VOSK_CONFIG env var (as-is, never
        auto-created) > project-relative config in a git checkout (dev mode
        primes over a stale XDG file) > per-user XDG config, auto-created
        from the factory template on first run > the factory template
        itself (fallback, e.g. dev mode with no XDG file yet).
        """
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        env_path = os.environ.get('VOSK_CONFIG')
        if env_path:
            return env_path

        dev_config = os.path.join(project_root, 'config', 'config.yaml')
        if os.path.isdir(os.path.join(project_root, '.git')) and os.path.exists(dev_config):
            return dev_config

        xdg_config_home = os.environ.get('XDG_CONFIG_HOME') or os.path.join(os.path.expanduser('~'), '.config')
        user_config = os.path.join(xdg_config_home, 'vosk-cli-dictation', 'config.yaml')
        if os.path.exists(user_config):
            return user_config

        factory_config = '/usr/share/vosk-cli-dictation/config.yaml'
        if os.path.exists(factory_config):
            os.makedirs(os.path.dirname(user_config), exist_ok=True)
            shutil.copy(factory_config, user_config)
            print(f"Created default configuration at {user_config}")
            return user_config

        return None

    def _load_config(self):
        """Loads the YAML configuration file."""
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

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
        defaults = {
            'ready_message': 'GREEN', 'help_text': 'BLUE', 'help_title': 'CYAN',
            'info': 'BLUE', 'success': 'GREEN', 'warning': 'YELLOW', 'error': 'RED',
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
