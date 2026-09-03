# Résolution du fichier de configuration : cascade XDG de _get_config_path
# (DOCUMENTATION_MULTILINGUE.md §10.2).
#
# Le repli du niveau 4 sur le config.yaml embarqué couvre l'installation
# depuis le tarball des sources : un `git archive` n'a pas de .git (le niveau
# « mode développement » ne se déclenche pas) ni de /usr/share/.../config.yaml
# (pas de .deb). Sans ce repli, `python3 src/main.py` levait
# FileNotFoundError hors clone git (constaté au round-trip du 03/09/2026,
# Debian 13).

import pytest

from config.config import Config

# Un chemin de « modèle d'usine système » qui n'existe pas, pour que les tests
# ne dépendent pas de la présence d'un .deb installé sur la machine de test.
NO_SYSTEM_TEMPLATE = "/nonexistent/vosk-cli-dictation/config.yaml"


@pytest.fixture(autouse=True)
def _isolate(tmp_path, monkeypatch):
    """HOME / XDG vierges, pas de VOSK_CONFIG hérité."""
    monkeypatch.delenv("VOSK_CONFIG", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    xdg = tmp_path / "xdg"
    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg))
    return xdg


def _tree(root, *, git: bool, bundled: bool):
    (root / "config").mkdir(parents=True)
    if bundled:
        (root / "config" / "config.yaml").write_text(
            "default_model: en\n", encoding="utf-8"
        )
    if git:
        (root / ".git").mkdir()
    return root


def test_vosk_config_env_wins(tmp_path, monkeypatch):
    target = tmp_path / "elsewhere.yaml"
    target.write_text("default_model: fr\n", encoding="utf-8")
    monkeypatch.setenv("VOSK_CONFIG", str(target))
    root = _tree(tmp_path / "tree", git=True, bundled=True)
    assert Config._get_config_path(
        project_root=str(root), system_template=NO_SYSTEM_TEMPLATE
    ) == str(target)


def test_git_checkout_uses_bundled_in_place(tmp_path):
    root = _tree(tmp_path / "tree", git=True, bundled=True)
    assert Config._get_config_path(
        project_root=str(root), system_template=NO_SYSTEM_TEMPLATE
    ) == str(root / "config" / "config.yaml")


def test_existing_xdg_file_wins_over_template(tmp_path, _isolate):
    root = _tree(tmp_path / "tree", git=False, bundled=True)
    user_cfg = _isolate / "vosk-cli-dictation" / "config.yaml"
    user_cfg.parent.mkdir(parents=True)
    user_cfg.write_text("default_model: de\n", encoding="utf-8")
    assert Config._get_config_path(
        project_root=str(root), system_template=NO_SYSTEM_TEMPLATE
    ) == str(user_cfg)


def test_source_tarball_seeds_xdg_from_bundled(tmp_path, _isolate):
    # git archive : pas de .git, pas de modèle système -> repli sur l'embarqué.
    root = _tree(tmp_path / "tree", git=False, bundled=True)
    expected = _isolate / "vosk-cli-dictation" / "config.yaml"
    resolved = Config._get_config_path(
        project_root=str(root), system_template=NO_SYSTEM_TEMPLATE
    )
    assert resolved == str(expected)
    assert expected.read_text(encoding="utf-8") == "default_model: en\n"


def test_system_template_takes_priority_over_bundled(tmp_path, _isolate):
    system_tpl = tmp_path / "usr-share" / "config.yaml"
    system_tpl.parent.mkdir(parents=True)
    system_tpl.write_text("default_model: es\n", encoding="utf-8")
    root = _tree(tmp_path / "tree", git=False, bundled=True)
    expected = _isolate / "vosk-cli-dictation" / "config.yaml"
    resolved = Config._get_config_path(
        project_root=str(root), system_template=str(system_tpl)
    )
    assert resolved == str(expected)
    # Amorcé depuis le modèle système, pas depuis l'embarqué.
    assert expected.read_text(encoding="utf-8") == "default_model: es\n"


def test_no_config_anywhere_returns_none(tmp_path, _isolate):
    root = _tree(tmp_path / "tree", git=False, bundled=False)
    assert Config._get_config_path(
        project_root=str(root), system_template=NO_SYSTEM_TEMPLATE
    ) is None
