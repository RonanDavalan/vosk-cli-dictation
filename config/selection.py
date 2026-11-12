# config/selection.py
#
# Choix mémorisés (langue, modèle) et langue du système. Les choix faits au
# menu ou par la socket s'écrivent dans selection.yaml sous $XDG_STATE_HOME ;
# config.yaml reste le fichier de l'utilisateur et n'est jamais réécrit.
# Priorité d'une valeur : ligne de commande, puis sélection, puis config.yaml.

import os
import tempfile

import yaml

SYSTEM = "system"
SUPPORTED_LANGS = ("en", "fr", "de", "es")
SELECTION_KEYS = ("lang", "model")


def state_dir() -> str:
    base = os.environ.get("XDG_STATE_HOME") or os.path.join(
        os.path.expanduser("~"), ".local", "state"
    )
    return os.path.join(base, "vosk-cli-dictation")


def selection_path() -> str:
    return os.path.join(state_dir(), "selection.yaml")


def load_selection() -> dict:
    """Sélection mémorisée ; vide si le fichier manque ou n'est pas lisible
    (un fichier abîmé ne doit jamais empêcher la dictée de démarrer)."""
    try:
        with open(selection_path(), "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except (OSError, yaml.YAMLError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {k: v for k, v in data.items() if k in SELECTION_KEYS and isinstance(v, str) and v}


def save_selection(updates: dict) -> None:
    """Fusionne `updates` dans la sélection ; une valeur None retire la clé.
    Écriture atomique (fichier voisin puis renommage)."""
    current = load_selection()
    for key, value in updates.items():
        if value is None:
            current.pop(key, None)
        else:
            current[key] = value
    os.makedirs(state_dir(), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=state_dir(), suffix=".part")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            yaml.safe_dump(current, f, allow_unicode=True, sort_keys=True)
        os.replace(tmp, selection_path())
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def clear_selection() -> None:
    """« Revenir à la configuration » : vide la sélection."""
    try:
        os.remove(selection_path())
    except FileNotFoundError:
        pass


def system_language(env=None) -> str | None:
    """Code de langue (deux lettres) de la session : première variable non
    vide parmi LC_ALL, LC_MESSAGES, LANG (priorité POSIX). None si la locale
    est « C », « POSIX » ou illisible."""
    env = os.environ if env is None else env
    for name in ("LC_ALL", "LC_MESSAGES", "LANG"):
        value = (env.get(name) or "").strip()
        if value:
            code = value.split(".")[0].split("@")[0].split("_")[0].lower()
            return code if code.isalpha() and code not in ("c", "posix") else None
    return None


def resolve_language(cli_lang, selection: dict, configured, installed_langs, env=None):
    """Langue de démarrage et son origine : (lang, source) avec source dans
    cli | selection | config | system.

    `configured` est la valeur de default_model dans config.yaml (None si la
    clé manque). « system » ou l'absence de clé suit la langue de la session
    si un modèle de cette langue est installé, sinon l'anglais."""
    if cli_lang:
        return cli_lang, "cli"
    chosen = selection.get("lang")
    if chosen and chosen != SYSTEM:
        return chosen, "selection"
    if chosen is None and configured not in (None, SYSTEM):
        return configured, "config"
    lang = system_language(env)
    return (lang if lang in installed_langs else "en"), "system"
