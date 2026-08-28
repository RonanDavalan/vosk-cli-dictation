# Support de config_local.yaml : surcharge locale fusionnée par-dessus
# config.yaml (deep-merge), fichier ignoré par git.

import textwrap

from config.config import Config


def test_deep_merge_recurses_and_replaces_leaves():
    base = {"a": {"b": 1, "c": 2}, "keep": True, "lst": [1, 2]}
    override = {"a": {"c": 99, "d": 3}, "lst": [9]}
    merged = Config._deep_merge(base, override)
    assert merged["a"] == {"b": 1, "c": 99, "d": 3}
    assert merged["keep"] is True
    assert merged["lst"] == [9]  # une liste remplace, elle ne se concatène pas


BASE = """
    default_model: fr
    recognition:
      confidence_threshold: 0.55
    language_settings:
      fr:
        voice_commands:
          wake_phrase: "active dictée"
          stop_phrase: "stop dictée"
"""


def _fresh_config(tmp_path, monkeypatch, local_yaml=None):
    # conftest sets this to isolate the suite from a dev's real overlay; here
    # we want the overlay path exercised.
    monkeypatch.delenv("VOSK_IGNORE_LOCAL_CONFIG", raising=False)
    (tmp_path / "config.yaml").write_text(textwrap.dedent(BASE), encoding="utf-8")
    if local_yaml is not None:
        (tmp_path / "config_local.yaml").write_text(
            textwrap.dedent(local_yaml), encoding="utf-8"
        )
    monkeypatch.setenv("VOSK_CONFIG", str(tmp_path / "config.yaml"))
    return Config()


def test_no_local_file_leaves_base_untouched(tmp_path, monkeypatch):
    cfg = _fresh_config(tmp_path, monkeypatch)
    assert cfg.local_config_path is None
    assert cfg.WAKE_PHRASE == "active dictée"
    assert cfg.STOP_PHRASE == "stop dictée"


def test_local_file_overlays_only_named_leaves(tmp_path, monkeypatch):
    cfg = _fresh_config(tmp_path, monkeypatch, """
        language_settings:
          fr:
            voice_commands:
              wake_phrase: "démarre"
              stop_phrase: "zut"
    """)
    assert cfg.local_config_path == str(tmp_path / "config_local.yaml")
    assert cfg.WAKE_PHRASE == "démarre"
    assert cfg.STOP_PHRASE == "zut"
    # Les feuilles non citées survivent à la fusion.
    assert cfg.data["recognition"]["confidence_threshold"] == 0.55


def test_empty_local_file_is_ignored(tmp_path, monkeypatch):
    cfg = _fresh_config(tmp_path, monkeypatch, "\n")
    assert cfg.local_config_path is None
    assert cfg.WAKE_PHRASE == "active dictée"
