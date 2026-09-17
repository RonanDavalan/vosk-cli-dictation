# Les quatre gabarits config.<lang>.yaml livrés (CONFIG_PUBLIQUE_ET_LOCALISATION.md,
# Chantier 13) doivent rester structurellement identiques -- seuls les
# commentaires et default_model varient par langue -- et exempts de jargon de
# gestion de projet interne (chantier/volet/décision codée), qui n'a rien à
# faire dans un artefact livré à l'utilisateur final.

import re
from pathlib import Path

import pytest
import yaml

from config.config import Config

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"
TEMPLATES = {lang: CONFIG_DIR / f"config.{lang}.yaml" for lang in Config.SUPPORTED_CONFIG_LANGS}

JARGON_PATTERN = re.compile(r"chantier|\bvolet [a-h]\b|\bD[0-9]\b|\bR[0-9]\b", re.IGNORECASE)


def _keys(node):
    """Ensemble récursif des chemins de clés d'un arbre YAML (listes incluses
    par position), pour comparer la structure sans comparer les valeurs."""
    paths = set()
    if isinstance(node, dict):
        for key, value in node.items():
            paths.add(key)
            for sub in _keys(value):
                paths.add(f"{key}.{sub}")
    elif isinstance(node, list):
        for i, item in enumerate(node):
            for sub in _keys(item):
                paths.add(f"[{i}].{sub}")
    return paths


@pytest.mark.parametrize("lang", Config.SUPPORTED_CONFIG_LANGS)
def test_template_exists_and_parses(lang):
    assert TEMPLATES[lang].exists(), f"gabarit manquant : {TEMPLATES[lang]}"
    data = yaml.safe_load(TEMPLATES[lang].read_text(encoding="utf-8"))
    assert isinstance(data, dict)


@pytest.mark.parametrize("lang", Config.SUPPORTED_CONFIG_LANGS)
def test_template_default_model_matches_its_own_language(lang):
    data = yaml.safe_load(TEMPLATES[lang].read_text(encoding="utf-8"))
    assert data["default_model"] == lang


def test_all_templates_share_the_same_key_structure():
    reference_lang = "en"
    reference_keys = _keys(yaml.safe_load(TEMPLATES[reference_lang].read_text(encoding="utf-8")))
    for lang, path in TEMPLATES.items():
        if lang == reference_lang:
            continue
        keys = _keys(yaml.safe_load(path.read_text(encoding="utf-8")))
        assert keys == reference_keys, (
            f"config.{lang}.yaml diverge structurellement de config.{reference_lang}.yaml : "
            f"manquant={reference_keys - keys} en trop={keys - reference_keys}"
        )


@pytest.mark.parametrize("lang", Config.SUPPORTED_CONFIG_LANGS)
def test_template_has_no_internal_project_jargon(lang):
    text = TEMPLATES[lang].read_text(encoding="utf-8")
    matches = JARGON_PATTERN.findall(text)
    assert not matches, f"jargon interne trouvé dans config.{lang}.yaml : {matches}"


@pytest.mark.parametrize("lang", Config.SUPPORTED_CONFIG_LANGS)
def test_template_declares_current_config_version(lang):
    data = yaml.safe_load(TEMPLATES[lang].read_text(encoding="utf-8"))
    assert data.get("config_version") == Config.CURRENT_CONFIG_VERSION
