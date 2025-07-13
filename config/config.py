# config/config.py

import yaml
import os
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
        """Finds the absolute path of the config.yaml file."""
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config_file = os.path.join(project_root, 'config', 'config.yaml')
        return config_file if os.path.exists(config_file) else None

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

    def set_language(self, lang_code: str):
        """
        Sets the active language for the application.
        """
        self.current_lang = lang_code
        lang_settings = self.language_settings.get(lang_code, {})
        voice_commands = lang_settings.get('voice_commands', {})
        self.START_WORD = voice_commands.get('start_word', 'start')
        self.STOP_WORD = voice_commands.get('stop_word', 'stop')

    def get_model_path_by_name(self, model_name: str) -> str | None:
        """
        Gets the full path to a Vosk model directory.
        """
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        for model in self.data.get('vosk_models', []):
            if model['name'] == model_name:
                return os.path.join(project_root, model['path_relative'])
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
