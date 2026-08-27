# Chantier 7 volet E/H — détection tokenisée des phrases de déclenchement.

import pytest

from src.voice_commands import (
    normalize_tokens, phrase_tokens, find_phrase, ends_with_phrase,
    is_doubled, strip_one_repetition, remove_phrase_and_after, mean_confidence,
)

STOP = phrase_tokens("stop dictée")
WAKE = phrase_tokens("active dictée")


# --- correspondance sur phrase entière, plus de sous-chaîne ------------------

def test_isolated_words_do_not_trigger():
    # "stop" seul, "dictée" seul, séparés : aucune correspondance.
    assert find_phrase(normalize_tokens("je fais un stop puis je reprends la dictée"), STOP) == -1


def test_full_phrase_triggers():
    tokens = normalize_tokens("voilà le texte stop dictée")
    assert find_phrase(tokens, STOP) == 3


def test_phrase_must_be_contiguous_and_ordered():
    assert find_phrase(normalize_tokens("dictée stop"), STOP) == -1
    assert find_phrase(normalize_tokens("stop la dictée"), STOP) == -1


def test_punctuation_between_words_is_ignored():
    assert find_phrase(normalize_tokens("texte. Stop, dictée !"), STOP) == 1


def test_substring_word_does_not_match():
    # "antistop" ne contient pas le token "stop".
    assert find_phrase(normalize_tokens("antistop dictée"), STOP) == -1


# --- réveil sur les partiels (fin de suite de tokens) -----------------------

def test_ends_with_phrase_true_only_at_the_tail():
    assert ends_with_phrase(normalize_tokens("bla bla active dictée"), WAKE)
    assert not ends_with_phrase(normalize_tokens("active dictée bla"), WAKE)


# --- échappatoire littérale : phrase dite deux fois -------------------------

def test_doubling_is_detected():
    assert is_doubled(normalize_tokens("stop dictée stop dictée"), STOP)
    assert not is_doubled(normalize_tokens("stop dictée maintenant"), STOP)


def test_doubling_keeps_one_literal_occurrence():
    assert strip_one_repetition("stop dictée stop dictée", STOP) == "stop dictée"


def test_doubling_with_leading_text():
    txt = "il a dit stop dictée stop dictée"
    assert strip_one_repetition(txt, STOP) == "il a dit stop dictée"


# --- retrait de la phrase-clé du texte tapé --------------------------------

def test_text_before_phrase_is_kept_rest_dropped():
    assert remove_phrase_and_after("bonjour tout le monde stop dictée et voilà", STOP) == "bonjour tout le monde"


def test_no_phrase_returns_text_unchanged():
    assert remove_phrase_and_after("bonjour tout le monde", STOP) == "bonjour tout le monde"


# --- garde de confiance ---------------------------------------------------

def _words(*pairs):
    return [{"word": w, "conf": c} for w, c in pairs]


def test_mean_confidence_over_the_key_phrase_span():
    words = _words(("bonjour", 0.99), ("stop", 0.40), ("dictée", 0.50))
    assert mean_confidence(words, 1, 2) == pytest.approx(0.45)


def test_mean_confidence_defaults_to_one_without_data():
    assert mean_confidence([], 0, 2) == 1.0
    assert mean_confidence([{"word": "stop"}, {"word": "dictée"}], 0, 2) == 1.0


def test_low_confidence_is_below_default_threshold():
    words = _words(("stop", 0.40), ("dictée", 0.50))
    assert mean_confidence(words, 0, 2) < 0.85


def test_high_confidence_passes_default_threshold():
    words = _words(("stop", 0.97), ("dictée", 0.95))
    assert mean_confidence(words, 0, 2) >= 0.85


# --- empty phrase is inert ----------------------------------------------

def test_empty_needle_never_matches():
    assert find_phrase(normalize_tokens("anything at all"), []) == -1
    assert not is_doubled(normalize_tokens("anything"), [])
