# src/i18n.py

import gettext
import os
import locale

_ = lambda s: s

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCALE_DIR = os.path.join(APP_DIR, 'locales')

def set_ui_language(lang: str = None) -> str:
    """
    Initializes or updates the UI language for gettext.
    This function ONLY handles the UI translation function '_'.
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
    """Returns the currently active translation function (_)."""
    return _
