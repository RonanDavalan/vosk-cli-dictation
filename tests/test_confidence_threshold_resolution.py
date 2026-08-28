# Chantier 7 bis — résolution par langue des réglages recognition.* via
# Config.recognition_setting (surcharge language_settings.<lang>.<clé>).

from config.config import config


def test_global_value_used_without_per_language_override(monkeypatch):
    monkeypatch.setitem(config.data["recognition"], "confidence_threshold", 0.5)
    monkeypatch.delitem(config.language_settings["fr"], "confidence_threshold",
                        raising=False)
    assert config.recognition_setting("confidence_threshold", 0.99, "fr") == 0.5


def test_per_language_overrides_global(monkeypatch):
    monkeypatch.setitem(config.data["recognition"], "confidence_threshold", 0.5)
    monkeypatch.setitem(config.language_settings["es"], "confidence_threshold", 0.8)
    assert config.recognition_setting("confidence_threshold", 0.99, "es") == 0.8
    assert config.recognition_setting("confidence_threshold", 0.99, "fr") == 0.5


def test_default_when_key_absent_everywhere(monkeypatch):
    monkeypatch.delitem(config.data["recognition"], "confidence_threshold",
                        raising=False)
    monkeypatch.delitem(config.language_settings["fr"], "confidence_threshold",
                        raising=False)
    assert config.recognition_setting("confidence_threshold", 0.42, "fr") == 0.42


def test_uses_current_language_when_lang_code_omitted(monkeypatch):
    monkeypatch.setitem(config.data["recognition"], "confidence_threshold", 0.5)
    monkeypatch.setitem(config.language_settings["es"], "confidence_threshold", 0.8)
    config.set_language("es")
    try:
        assert config.recognition_setting("confidence_threshold", 0.99) == 0.8
    finally:
        config.set_language("fr")


def test_shipped_defaults():
    # Les valeurs livrées par config.yaml après le chantier 7 bis.
    assert config.data["recognition"]["confidence_threshold"] == 0.55
    assert config.data["recognition"]["restricted_stop_in_dictation"] is True


def test_restricted_stop_shipped_on_for_all_languages():
    # Chantier 7 bis : true partout. La validation (clips Piper fr, Pi 4) a
    # montré que le plein vocabulaire ne reconnaît pas « stop dictée » isolé —
    # le recognizer restreint est le seul chemin d'arrêt fiable, y compris pour
    # fr (coût Pi 4 : RTF 0,90, reste < 1,0).
    for lang in ("en", "fr", "de", "es"):
        assert config.recognition_setting("restricted_stop_in_dictation", None, lang) is True
