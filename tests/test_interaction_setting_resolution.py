# Chantier 11 — résolution de interaction.mode et interaction.silence_timeout_ms
# via Config.interaction_mode / Config.interaction_setting (même motif que
# recognition_setting pour confidence_threshold, correctif 7 bis).

from config.config import config


def test_shipped_default_mode_is_toggle():
    assert config.data.get("interaction", {}).get("mode", "toggle") == "toggle"
    assert config.interaction_mode == "toggle"


def test_shipped_default_silence_timeout_is_700ms():
    assert config.data["interaction"]["silence_timeout_ms"] == 700


def test_interaction_mode_reads_config_data(monkeypatch):
    monkeypatch.setitem(config.data.setdefault("interaction", {}), "mode", "silence")
    assert config.interaction_mode == "silence"


def test_global_value_used_without_per_language_override(monkeypatch):
    monkeypatch.setitem(config.data["interaction"], "silence_timeout_ms", 500)
    monkeypatch.delitem(config.language_settings["fr"], "silence_timeout_ms", raising=False)
    assert config.interaction_setting("silence_timeout_ms", 999, "fr") == 500


def test_per_language_overrides_global(monkeypatch):
    monkeypatch.setitem(config.data["interaction"], "silence_timeout_ms", 500)
    monkeypatch.setitem(config.language_settings["es"], "silence_timeout_ms", 900)
    assert config.interaction_setting("silence_timeout_ms", 999, "es") == 900
    assert config.interaction_setting("silence_timeout_ms", 999, "fr") == 500


def test_default_when_key_absent_everywhere(monkeypatch):
    monkeypatch.delitem(config.data["interaction"], "silence_timeout_ms", raising=False)
    monkeypatch.delitem(config.language_settings["fr"], "silence_timeout_ms", raising=False)
    assert config.interaction_setting("silence_timeout_ms", 700, "fr") == 700


def test_uses_current_language_when_lang_code_omitted(monkeypatch):
    monkeypatch.setitem(config.data["interaction"], "silence_timeout_ms", 500)
    monkeypatch.setitem(config.language_settings["es"], "silence_timeout_ms", 900)
    config.set_language("es")
    try:
        assert config.interaction_setting("silence_timeout_ms", 999) == 900
    finally:
        config.set_language("fr")
