# src/i18n.py
#
# Fonction de traduction `_` des messages de l'interface, adossée aux catalogues
# gettext de `locales/`. Pourquoi : la langue des messages change à chaud (menu
# de l'icône, `set-lang`), donc chaque module demande `_` par `get_translation()`
# au moment d'afficher, jamais à l'import.

import gettext
import os
import locale

_ = lambda s: s

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCALE_DIR = os.path.join(APP_DIR, 'locales')

def set_ui_language(lang: str = None) -> str:
    """Fixe la langue des messages de l'interface (gettext).

    Ne gère que la fonction de traduction `_` : la langue de reconnaissance
    se règle ailleurs.
    """
    global _

    determined_lang = lang
    if not determined_lang:
        try:
            env_lang = os.environ.get('LANGUAGE') or os.environ.get('LANG')
            if env_lang:
                determined_lang = env_lang.split('.')[0].split('_')[0]
        except Exception:
            pass

    if not determined_lang:
        determined_lang = 'en'

    try:
        translation_obj = gettext.translation(
            'messages',
            localedir=LOCALE_DIR,
            languages=[determined_lang],
            fallback=True
        )
        _ = translation_obj.gettext
    except FileNotFoundError:
        _ = gettext.NullTranslations().gettext

    print(f"[{_('i18n')}] {_('UI Language set to')}: '{determined_lang}'")
    return determined_lang

def get_translation():
    """Rend la fonction de traduction `_` actuellement active."""
    return _
