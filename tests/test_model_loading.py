# Chargement réel des modèles des quatre langues et construction de la
# grammaire restreinte avec le vrai vocabulaire.
#
# Ces tests exigent les modèles Vosk sur disque. Ils se sautent proprement
# quand un modèle est absent (machine sans le téléchargement), pour que
# `pytest` reste vert sur une clone nue.

import json
import os

import pytest

from config.config import config
from src.recognition import load_model, build_recognizer, MODE_LISTENING, MODE_FULL

LANGS = ["en", "fr", "de", "es"]


def _model_present(lang):
    return config.get_model_path_by_name(lang) is not None


@pytest.mark.parametrize("lang", LANGS)
def test_model_loads(lang):
    if not _model_present(lang):
        pytest.skip(f"modèle {lang} absent")
    config.set_language(lang)
    model, rec, name = load_model(lang)
    assert model is not None and rec is not None
    assert lang in name or name.startswith("vosk-model")


@pytest.mark.parametrize("lang", LANGS)
def test_restricted_grammar_words_are_in_vocabulary(lang, capfd):
    if not _model_present(lang):
        pytest.skip(f"modèle {lang} absent")
    config.set_language(lang)
    model, _rec, _name = load_model(lang)
    build_recognizer(model, MODE_LISTENING)
    # Vosk émet "Ignoring word missing in vocabulary: '<mot>'" sur stderr si un
    # mot de la phrase de réveil n'existe pas dans le modèle. La grammaire est
    # sérialisée avec ensure_ascii=False, donc les accents doivent passer.
    err = capfd.readouterr().err
    assert "missing in vocabulary" not in err, (
        f"{lang}: mot(s) de '{config.WAKE_PHRASE}' hors vocabulaire — {err}"
    )


@pytest.mark.parametrize("lang", LANGS)
def test_full_and_listening_recognizers_decode_silence(lang):
    if not _model_present(lang):
        pytest.skip(f"modèle {lang} absent")
    config.set_language(lang)
    model, _rec, _name = load_model(lang)
    silence = b"\x00\x00" * 2048
    for mode in (MODE_FULL, MODE_LISTENING):
        r = build_recognizer(model, mode)
        for _ in range(5):
            r.AcceptWaveform(silence)
        assert "text" in json.loads(r.Result())
