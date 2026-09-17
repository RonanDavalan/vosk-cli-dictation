# Notice de schéma de config obsolète (CONFIG_PUBLIQUE_ET_LOCALISATION.md §2.4) :
# Config.config_is_outdated ne vaut True que pour le fichier
# utilisateur XDG réel, et seulement s'il est en retard sur
# Config.CURRENT_CONFIG_VERSION. Un fichier de développement (chargé en
# place) ou une surcharge VOSK_CONFIG vers un chemin distinct du fichier XDG
# canonique n'est jamais concerné, même sans config_version.

import pytest

from config.config import Config


@pytest.fixture(autouse=True)
def _isolate(tmp_path, monkeypatch):
    monkeypatch.delenv("LANGUAGE", raising=False)
    monkeypatch.setenv("LANG", "en_US.UTF-8")
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    xdg = tmp_path / "xdg"
    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg))
    return xdg


def _canonical_user_path(xdg):
    path = xdg / "vosk-cli-dictation" / "config.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def test_outdated_notice_fires_for_stale_user_config(tmp_path, monkeypatch, _isolate):
    user_cfg = _canonical_user_path(_isolate)
    user_cfg.write_text("default_model: en\n", encoding="utf-8")  # pas de config_version
    monkeypatch.setenv("VOSK_CONFIG", str(user_cfg))
    cfg = Config()
    assert cfg.config_is_outdated is True


def test_no_notice_when_user_config_is_current(tmp_path, monkeypatch, _isolate):
    user_cfg = _canonical_user_path(_isolate)
    user_cfg.write_text(
        f"config_version: {Config.CURRENT_CONFIG_VERSION}\ndefault_model: en\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("VOSK_CONFIG", str(user_cfg))
    cfg = Config()
    assert cfg.config_is_outdated is False


def test_no_notice_for_a_config_path_outside_the_xdg_user_file(tmp_path, monkeypatch, _isolate):
    other = tmp_path / "elsewhere.yaml"
    other.write_text("default_model: en\n", encoding="utf-8")  # pas de config_version non plus
    monkeypatch.setenv("VOSK_CONFIG", str(other))
    cfg = Config()
    assert cfg.config_is_outdated is False
