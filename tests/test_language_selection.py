# Langue du système, sélection mémorisée et priorité des valeurs.

import os

import pytest
import yaml

from config import selection as sel
from config.config import Config


@pytest.fixture
def state(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    return tmp_path


def make_config(
    tmp_path,
    monkeypatch,
    default_model=None,
    models=("fr", "en", "de", "es"),
    create=("fr", "en", "de", "es"),
):
    """Config isolée : des dossiers de modèles factices dans XDG_DATA_HOME."""
    data_home = tmp_path / "data"
    monkeypatch.setenv("XDG_DATA_HOME", str(data_home))
    names = {
        "en": "vosk-model-small-en-us-0.15",
        "fr": "vosk-model-small-fr-0.22",
        "de": "vosk-model-small-de-0.15",
        "es": "vosk-model-small-es-0.42",
    }
    for lang in create:
        (data_home / "vosk-models" / names[lang]).mkdir(parents=True, exist_ok=True)
    # Seule la racine factice compte : le ./vosk-model/ du dépôt de
    # développement ne doit pas faire apparaître un modèle absent.
    monkeypatch.setattr(
        Config,
        "model_search_roots",
        lambda self, rel: [str(data_home / "vosk-models" / os.path.basename(rel))],
    )
    cfg = tmp_path / "config.yaml"
    body = {
        "vosk_models": [
            {"name": l, "path_relative": "vosk-model/" + names[l]} for l in models
        ]
    }
    if default_model is not None:
        body["default_model"] = default_model
    cfg.write_text(yaml.safe_dump(body), encoding="utf-8")
    monkeypatch.setenv("VOSK_CONFIG", str(cfg))
    monkeypatch.setenv("VOSK_IGNORE_LOCAL_CONFIG", "1")
    return Config()


def set_session_lang(monkeypatch, lang):
    for name in ("LC_ALL", "LC_MESSAGES", "LANGUAGE"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("LANG", lang)


def test_system_language_reads_lang(monkeypatch):
    set_session_lang(monkeypatch, "de_DE.UTF-8")
    assert sel.system_language() == "de"


def test_lc_messages_wins_over_lang(monkeypatch):
    set_session_lang(monkeypatch, "de_DE.UTF-8")
    monkeypatch.setenv("LC_MESSAGES", "es_ES.UTF-8")
    assert sel.system_language() == "es"


def test_c_locale_gives_no_language(monkeypatch):
    set_session_lang(monkeypatch, "C")
    assert sel.system_language() is None


def test_german_session_with_german_model_gives_de(state, monkeypatch):
    set_session_lang(monkeypatch, "de_DE.UTF-8")
    cfg = make_config(state, monkeypatch, default_model=None)
    assert cfg.startup_language() == ("de", "system")


def test_german_session_without_german_model_gives_en(state, monkeypatch):
    set_session_lang(monkeypatch, "de_DE.UTF-8")
    cfg = make_config(
        state, monkeypatch, default_model="system", create=("fr", "en", "es")
    )
    assert cfg.startup_language() == ("en", "system")


def test_key_absent_and_value_system_behave_the_same(state, monkeypatch):
    set_session_lang(monkeypatch, "es_ES.UTF-8")
    assert make_config(state, monkeypatch, default_model=None).startup_language() == (
        "es",
        "system",
    )
    assert make_config(
        state, monkeypatch, default_model="system"
    ).startup_language() == ("es", "system")


def test_config_value_beats_the_system(state, monkeypatch):
    set_session_lang(monkeypatch, "de_DE.UTF-8")
    cfg = make_config(state, monkeypatch, default_model="en")
    assert cfg.startup_language() == ("en", "config")


def test_selection_beats_config(state, monkeypatch):
    set_session_lang(monkeypatch, "de_DE.UTF-8")
    cfg = make_config(state, monkeypatch, default_model="en")
    sel.save_selection({"lang": "fr"})
    assert cfg.startup_language() == ("fr", "selection")


def test_command_line_beats_selection(state, monkeypatch):
    cfg = make_config(state, monkeypatch, default_model="en")
    sel.save_selection({"lang": "fr"})
    assert cfg.startup_language("es") == ("es", "cli")


def test_selection_system_overrides_a_fixed_config(state, monkeypatch):
    set_session_lang(monkeypatch, "de_DE.UTF-8")
    cfg = make_config(state, monkeypatch, default_model="en")
    sel.save_selection({"lang": "system"})
    assert cfg.startup_language() == ("de", "system")


def test_clear_selection_returns_to_config(state, monkeypatch):
    cfg = make_config(state, monkeypatch, default_model="en")
    sel.save_selection({"lang": "fr", "model": "x"})
    sel.clear_selection()
    assert sel.load_selection() == {}
    assert cfg.startup_language() == ("en", "config")


def test_selection_is_written_under_xdg_state_home(state, monkeypatch):
    sel.save_selection({"lang": "fr"})
    path = state / "state" / "vosk-cli-dictation" / "selection.yaml"
    assert yaml.safe_load(path.read_text(encoding="utf-8")) == {"lang": "fr"}
    sel.save_selection({"lang": None, "model": "m"})
    assert sel.load_selection() == {"model": "m"}


def test_damaged_selection_file_is_ignored(state, monkeypatch):
    sel.save_selection({"lang": "fr"})
    sel.selection_path()
    with open(sel.selection_path(), "w", encoding="utf-8") as f:
        f.write(": : [")
    assert sel.load_selection() == {}


def test_diagnose_gives_the_origin_of_each_value(state, monkeypatch, capsys):
    from src import diagnose

    set_session_lang(monkeypatch, "de_DE.UTF-8")
    cfg = make_config(state, monkeypatch, default_model="en")
    sel.save_selection({"lang": "fr"})
    monkeypatch.setattr(diagnose, "config", cfg)
    monkeypatch.setattr("src.control_socket.instance_running", lambda: False)
    try:
        diagnose.run_diagnose("es")
    except Exception:
        pass
    out = capsys.readouterr().out
    assert "es  (cli)" in out
    assert str(sel.selection_path()) in out
