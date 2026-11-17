# config/config.py
#
# Chargement de `config.yaml` (cascade XDG, gabarit par langue) et accès typé à
# ses valeurs, avec surcharges par langue. Pourquoi : tous les réglages passent
# par un seul objet `config`, que les autres modules lisent sans connaître
# l'emplacement du fichier.

import yaml
import os
import shutil
from config.selection import load_selection, resolve_language
from colorama import Fore, Style, init as colorama_init

colorama_init(autoreset=True)


class Config:
    """
    Charge la configuration du projet depuis config.yaml et y donne accès.
    """

    # Langues pour lesquelles un gabarit config.<lang>.yaml est livré.
    SUPPORTED_CONFIG_LANGS = ("en", "fr", "de", "es")

    # Incrémenté chaque fois qu'un gabarit livré gagne une section qu'un
    # fichier utilisateur ancien n'aurait pas ; comparé au config_version du
    # fichier utilisateur pour décider si la notice de démarrage se déclenche
    # (voir config_is_outdated).
    CURRENT_CONFIG_VERSION = 3

    def __init__(self):
        # --- CHARGEMENT DU FICHIER DE CONFIGURATION ---
        self.config_path = self._get_config_path()
        if not self.config_path:
            raise FileNotFoundError("Could not find config.yaml")
        # Posé par _load_config quand une surcharge sœur config_local.yaml est appliquée.
        self.local_config_path = None
        self.data = self._load_config()

        # Initialise les couleurs du thème depuis le fichier de configuration.
        self._initialize_theme()

        # Langue initiale d'après le modèle par défaut de la configuration
        # (« system » ou clé absente : langue de la session).
        self.current_lang = self.default_model
        self.set_language(self.current_lang)

        # Ne vaut jamais True pour un fichier de développement (chargé en
        # place) ou une surcharge VOSK_CONFIG explicite -- seul le fichier
        # utilisateur XDG réel est concerné par la notice de démarrage.
        self.config_is_outdated = (
            os.path.abspath(self.config_path)
            == os.path.abspath(self._user_config_path())
            and self.data.get("config_version", 0) < self.CURRENT_CONFIG_VERSION
        )

    @staticmethod
    def _user_config_path() -> str:
        xdg_config_home = os.environ.get("XDG_CONFIG_HOME") or os.path.join(
            os.path.expanduser("~"), ".config"
        )
        return os.path.join(xdg_config_home, "vosk-cli-dictation", "config.yaml")

    @staticmethod
    def _detect_config_lang() -> str:
        """Langue de gabarit à choisir : même heuristique que
        ``src/i18n.py::set_ui_language`` (``LANGUAGE`` puis ``LANG``), repli
        sur ``en`` si la variable est absente ou ne correspond à aucun
        gabarit livré (``SUPPORTED_CONFIG_LANGS``)."""
        env_lang = os.environ.get("LANGUAGE") or os.environ.get("LANG")
        if env_lang:
            candidate = env_lang.split(".")[0].split("_")[0].lower()
            if candidate in Config.SUPPORTED_CONFIG_LANGS:
                return candidate
        return "en"

    @staticmethod
    def _get_config_path(
        project_root=None, system_template_dir="/usr/share/vosk-cli-dictation"
    ):
        """Localise config.yaml via la cascade XDG.

        Premier niveau concordant gagne :

        1. Variable d'env ``VOSK_CONFIG`` — prise telle quelle, jamais créée.
        2. ``config/config.<lang>.yaml`` relatif au projet dans un checkout git
           (``PROJECT_ROOT/.git`` présent) — utilisé en place, pour que les
           retouches d'un développeur ne soient pas masquées par un fichier
           XDG périmé.
        3. Config XDG par utilisateur
           ``$XDG_CONFIG_HOME/vosk-cli-dictation/config.yaml``.
        4. Gabarit d'usine, copié vers (3) au premier lancement :
           ``system_template_dir/config.<lang>.yaml`` déposé par le .deb ou,
           à défaut, ``config/config.<lang>.yaml`` embarqué dans l'arborescence.
           Le repli embarqué couvre une install depuis le tarball de sources —
           une ``git archive`` n'a pas de ``.git`` (le niveau 2 ne se déclenche
           pas) ni de gabarit ``/usr/share``, donc sans lui l'outil ne
           démarrerait pas. Le fichier copié s'appelle toujours ``config.yaml``
           dans le répertoire XDG, quel que soit le gabarit de langue source.

        Les niveaux 2 et 4 prennent le gabarit qui correspond à
        ``_detect_config_lang()``, avec repli sur ``config.en.yaml`` si cette
        langue n'a pas de gabarit dans le répertoire cherché.

        ``project_root`` vaut par défaut l'arborescence qui porte ce fichier ;
        lui et ``system_template_dir`` sont des paramètres pour que la cascade
        reste testable unitairement en isolation.
        """
        if project_root is None:
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        env_path = os.environ.get("VOSK_CONFIG")
        if env_path:
            return env_path

        lang = Config._detect_config_lang()

        def _template_in(directory):
            if not directory:
                return None
            candidate = os.path.join(directory, f"config.{lang}.yaml")
            if os.path.exists(candidate):
                return candidate
            fallback = os.path.join(directory, "config.en.yaml")
            return fallback if os.path.exists(fallback) else None

        bundled_dir = os.path.join(project_root, "config")
        bundled_config = _template_in(bundled_dir)
        if os.path.isdir(os.path.join(project_root, ".git")) and bundled_config:
            return bundled_config

        user_config = Config._user_config_path()
        if os.path.exists(user_config):
            return user_config

        for template in (_template_in(system_template_dir), bundled_config):
            if template:
                os.makedirs(os.path.dirname(user_config), exist_ok=True)
                shutil.copy(template, user_config)
                print(f"Created default configuration at {user_config}")
                return user_config

        return None

    def _load_config(self):
        """Charge config.yaml, puis applique en surcharge un éventuel
        ``config_local.yaml`` frère (ignoré par git) pour les retouches locales
        à la machine.

        ``config_local.yaml`` voisine le fichier de configuration résolu. Ses
        clés fusionnent en profondeur par-dessus la base : deux tables sous la
        même clé fusionnent récursivement, toute autre valeur (scalaire,
        liste) remplace celle de la base. Une surcharge absente ou vide laisse
        la base intacte.
        """
        with open(self.config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        local_path = os.path.join(
            os.path.dirname(os.path.abspath(self.config_path)), "config_local.yaml"
        )
        if os.path.exists(local_path) and not os.environ.get(
            "VOSK_IGNORE_LOCAL_CONFIG"
        ):
            with open(local_path, "r", encoding="utf-8") as f:
                overrides = yaml.safe_load(f)
            if overrides:
                data = self._deep_merge(data, overrides)
                self.local_config_path = local_path
        return data

    @staticmethod
    def _deep_merge(base: dict, override: dict) -> dict:
        """Fusionne récursivement ``override`` dans ``base`` ; retourne ``base``.

        Deux tables sous la même clé fusionnent récursivement ; toute autre
        valeur de ``override`` (scalaire, liste ou changement de type)
        remplace celle de la base.
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
        Charge les couleurs de l'UI depuis config.yaml et les associe aux
        objets colorama. Fournit des défauts sains si la section theme manque.
        """
        color_map = {
            "BLACK": Fore.BLACK,
            "RED": Fore.RED,
            "GREEN": Fore.GREEN,
            "YELLOW": Fore.YELLOW,
            "BLUE": Fore.BLUE,
            "MAGENTA": Fore.MAGENTA,
            "CYAN": Fore.CYAN,
            "WHITE": Fore.WHITE,
            "RESET": Fore.RESET,
        }

        user_theme = self.data.get("theme", {})
        # La couleur ne marque que les accents (titres, bandeau « prêt ») ; le
        # corps du texte prend la couleur par défaut du terminal via `RESET`,
        # lisible sur thème clair comme sombre. `BLUE` proscrit pour du courant.
        defaults = {
            "ready_message": "GREEN",
            "help_text": "RESET",
            "help_title": "CYAN",
            "info": "RESET",
            "success": "GREEN",
            "warning": "YELLOW",
            "error": "RED",
        }

        # Crée dynamiquement des attributs comme self.color_ready_message
        for key, default_color in defaults.items():
            color_name = user_theme.get(key, default_color).upper()
            color_obj = color_map.get(
                color_name, Fore.WHITE
            )  # blanc par défaut si couleur invalide
            setattr(self, f"color_{key}", color_obj)

        # Style attributes
        self.BRIGHT = Style.BRIGHT
        self.RESET = Style.RESET_ALL

    # Défauts de repli des phrases de déclenchement, par langue. N'entrent en
    # jeu que si la langue n'a pas de bloc voice_commands dans config.yaml.
    _WAKE_PHRASE_FALLBACK = {
        "en": "start dictation",
        "fr": "active dictée",
        "de": "diktat starten",
        "es": "iniciar dictado",
    }
    _STOP_PHRASE_FALLBACK = {
        "en": "stop dictation",
        "fr": "stop dictée",
        "de": "diktat stoppen",
        "es": "terminar dictado",
    }

    def set_language(self, lang_code: str):
        """
        Pose la langue active de l'application.
        """
        self.current_lang = lang_code
        lang_settings = self.language_settings.get(lang_code, {})
        voice_commands = lang_settings.get("voice_commands", {})
        # Phrases de déclenchement à deux mots. Les anciennes clés mono-mot
        # start_word / stop_word sont encore lues pour ne pas casser une
        # config utilisateur non migrée.
        default_wake = self._WAKE_PHRASE_FALLBACK.get(lang_code, "start dictation")
        default_stop = self._STOP_PHRASE_FALLBACK.get(lang_code, "stop dictation")
        self.WAKE_PHRASE = voice_commands.get(
            "wake_phrase", voice_commands.get("start_word", default_wake)
        )
        self.STOP_PHRASE = voice_commands.get(
            "stop_phrase", voice_commands.get("stop_word", default_stop)
        )

    def recognition_setting(self, key: str, default, lang_code: str = None):
        """Résout un réglage ``recognition.<key>`` avec surcharge par langue.

        ``language_settings.<lang>.<key>`` l'emporte sur ``recognition.<key>``,
        lui-même sur ``default``. Même motif que ``restricted_grammar_in_listening``
        dans ``recognition._target_mode``.
        """
        lang_code = lang_code or self.current_lang
        global_value = self.data.get("recognition", {}).get(key, default)
        return self.language_settings.get(lang_code, {}).get(key, global_value)

    def interaction_setting(self, key: str, default, lang_code: str = None):
        """Résout un réglage ``interaction.<key>`` avec surcharge par langue,
        même motif que ``recognition_setting`` pour ``confidence_threshold``
        (seuil de confiance par langue).

        ``language_settings.<lang>.<key>`` l'emporte sur ``interaction.<key>``,
        lui-même sur ``default``.
        """
        lang_code = lang_code or self.current_lang
        global_value = self.data.get("interaction", {}).get(key, default)
        return self.language_settings.get(lang_code, {}).get(key, global_value)

    @property
    def interaction_mode(self) -> str:
        """``toggle`` (défaut, inchangé) | ``maintenue`` | ``silence`` (modes de déclenchement de la dictée)."""
        return self.data.get("interaction", {}).get("mode", "toggle")

    def typography(self, lang_code: str = None) -> dict:
        """Profil typographique d'une langue.

        Piloté par les données du bloc `typography` de la langue. Les clés
        manquantes replient sur un profil neutre (pas d'espace fine,
        majuscule en début de phrase, guillemets ASCII).
        """
        lang_code = lang_code or self.current_lang
        raw = self.language_settings.get(lang_code, {}).get("typography", {})
        return {
            "thin_space": raw.get("thin_space", False),
            "space_before": list(raw.get("space_before", [])),
            "space_after": list(raw.get("space_after", [",", ".", ";", ":", "?", "!"])),
            "capitalize_sentence_start": raw.get("capitalize_sentence_start", True),
            "quote_open": raw.get("quote_open", '"'),
            "quote_close": raw.get("quote_close", '"'),
        }

    def model_search_roots(self, path_relative: str) -> list[str]:
        """Liste ordonnée des racines cherchées pour un dossier de modèle, pour les messages d'erreur."""
        nom_dossier = os.path.basename(path_relative)
        xdg_data_home = os.environ.get("XDG_DATA_HOME") or os.path.join(
            os.path.expanduser("~"), ".local", "share"
        )
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return [
            os.path.join(xdg_data_home, "vosk-models", nom_dossier),
            os.path.join("/usr/share/vosk-models", nom_dossier),
            os.path.join(project_root, path_relative),
        ]

    def get_model_path_by_name(self, model_name: str) -> str | None:
        """
        Résout le chemin complet d'un répertoire de modèle Vosk via la cascade
        multi-racines : un chemin absolu
        explicite dans config.yaml gagne d'office ; sinon le premier répertoire
        existant parmi $XDG_DATA_HOME/vosk-models/, /usr/share/vosk-models/ et
        le ./vosk-model/ de développement d'un clone git.
        """
        for model in self.data.get("vosk_models", []):
            if model["name"] != model_name:
                continue
            path_relative = model["path_relative"]
            if os.path.isabs(path_relative):
                return path_relative if os.path.isdir(path_relative) else None
            for candidat in self.model_search_roots(path_relative):
                if os.path.isdir(candidat):
                    return candidat
            return None
        return None

    def get_lang_from_model_name(self, model_name_on_disk: str) -> str | None:
        """
        Retrouve le code de langue ('fr', 'en') depuis un nom de dossier de modèle.
        """
        for model in self.data.get("vosk_models", []):
            if model["path_relative"].endswith(model_name_on_disk):
                return model["name"]
        return None

    # --- Propriétés d'accès simple aux données de configuration ---
    @property
    def default_model_setting(self) -> str | None:
        """Valeur brute de ``default_model`` dans config.yaml (None si absente)."""
        return self.data.get("default_model")

    @property
    def default_model(self) -> str:
        """Langue du modèle par défaut d'après config.yaml seul ; « system » ou
        l'absence de clé donne la langue de la session (voir startup_language)."""
        return resolve_language(
            None, {}, self.default_model_setting, self.installed_languages()
        )[0]

    def installed_models(self) -> list[dict]:
        """Modèles présents sur le disque : ceux du catalogue de
        src/model_download.py (petits et complets) trouvés dans la cascade de
        racines, puis ceux que config.yaml déclare en plus. Chaque entrée :
        folder, path, lang, size (``small`` ou ``big``)."""
        from src.model_download import known_folders

        found = {}
        for folder, (lang, size) in known_folders().items():
            for racine in self.model_search_roots(os.path.join("vosk-model", folder)):
                if os.path.isdir(racine):
                    found[folder] = {
                        "folder": folder,
                        "path": racine,
                        "lang": lang,
                        "size": size,
                    }
                    break
        for model in self.data.get("vosk_models", []):
            path = self.get_model_path_by_name(model["name"])
            folder = os.path.basename(path) if path else None
            if folder and folder not in found:
                size = "small" if "small" in folder else "big"
                found[folder] = {
                    "folder": folder,
                    "path": path,
                    "lang": model["name"],
                    "size": size,
                }
        return list(found.values())

    def installed_languages(self) -> list[str]:
        return sorted({m["lang"] for m in self.installed_models()})

    def installed_model(self, folder: str, lang: str = None) -> dict | None:
        """Entrée d'installed_models() pour ce dossier (et cette langue si donnée)."""
        for m in self.installed_models():
            if m["folder"] == folder and (lang is None or m["lang"] == lang):
                return m
        return None

    def startup_language(self, cli_lang=None):
        """(langue, origine) au lancement : ligne de commande, sélection
        mémorisée, config.yaml, puis langue de la session."""
        return resolve_language(
            cli_lang,
            load_selection(),
            self.default_model_setting,
            self.installed_languages(),
        )

    @property
    def default_model_name(self) -> str | None:
        path = self.get_model_path_by_name(self.default_model)
        return os.path.basename(path) if path else None

    @property
    def audio(self) -> dict:
        return self.data.get("audio", {})

    @property
    def hotkeys(self) -> dict:
        return self.data.get("hotkeys", {})

    @property
    def language_settings(self) -> dict:
        return self.data.get("language_settings", {})

    @property
    def sound_file(self) -> str:
        return self.data.get("sound_file", "")


# Instance unique de la configuration
config = Config()
