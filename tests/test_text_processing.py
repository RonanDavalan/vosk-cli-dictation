# Chantier 7 volet F/H — golden tests du TextProcessor, quatre langues.
#
# Chaque cas est (langue, sortie Vosk brute) -> texte formaté attendu. On teste
# la ponctuation, la capitalisation de début de phrase, l'espace fine française,
# les guillemets „ “ allemands, les ouvrants ¿ ¡ espagnols par commande
# explicite, et l'absence d'espace avant ? ! en de / es.

import pytest

from config.config import config
from src.text_processing import TextProcessor

NNBSP = " "  # narrow no-break space (espace fine insécable)


def fmt(lang, raw):
    config.set_language(lang)
    return TextProcessor(lang).process(raw)


# --------------------------------------------------------------------------- #
# Français : espace fine, guillemets « », alias, vocabulaire                    #
# --------------------------------------------------------------------------- #

FR_CASES = [
    ("bonjour virgule comment allez-vous point d'interrogation",
     f"Bonjour, comment allez-vous{NNBSP}? "),
    ("il fait beau point il pleuvra demain",
     "Il fait beau. Il pleuvra demain"),
    ("attention deux points c'est important",
     f"Attention{NNBSP}: c'est important"),
    ("un point-virgule ici point-virgule et là",
     f"Un{NNBSP}; ici{NNBSP}; et là"),
    ("il dit ouvrez les guillemets salut fermez les guillemets point",
     f"Il dit « Salut{NNBSP}». "),
    # alias d'usine : "fermer la parenthèse" -> "fermez la parenthèse" -> ')'
    ("le texte fermer la parenthèse suite",
     "Le texte) suite"),
    # custom_vocabulary : casse fixe
    ("vosk et gemini virgule c'est de l'ia",
     "Vosk et Gemini, c'est de l'IA"),
]


@pytest.mark.parametrize("raw,expected", FR_CASES)
def test_french(raw, expected):
    assert fmt("fr", raw) == expected


def test_french_thin_space_is_narrow_nobreak():
    out = fmt("fr", "quoi point d'interrogation")
    assert NNBSP + "?" in out
    assert " ?" not in out  # jamais d'espace ordinaire avant ?


# --------------------------------------------------------------------------- #
# Anglais : minimal, guillemets ASCII, pas d'espace fine                       #
# --------------------------------------------------------------------------- #

EN_CASES = [
    ("hello comma how are you question mark",
     "Hello, how are you? "),
    ("first sentence period second sentence",
     "First sentence. Second sentence"),
    # `!` ends the sentence, so the next word is capitalized.
    ("wait exclamation mark now",
     "Wait! Now"),
]

# English straight quotes (" ") use the same glyph for open and close, so the
# engine cannot decide spacing per occurrence without stateful quote tracking —
# out of scope for volet F (data-driven typography). Languages with distinct
# opening/closing glyphs (fr « », de „ “) are covered above.


@pytest.mark.parametrize("raw,expected", EN_CASES)
def test_english(raw, expected):
    assert fmt("en", raw) == expected


def test_english_has_no_thin_space():
    assert NNBSP not in fmt("en", "really question mark")


# --------------------------------------------------------------------------- #
# Allemand : guillemets „ “, capitalisation début de phrase seulement,         #
# pas d'espace avant ? ! :                                                     #
# --------------------------------------------------------------------------- #

DE_CASES = [
    ("hallo komma wie geht es dir fragezeichen",
     "Hallo, wie geht es dir? "),
    ("erster satz punkt zweiter satz",
     "Erster satz. Zweiter satz"),
    ("er sagte anführungszeichen auf hallo anführungszeichen zu punkt",
     "Er sagte „Hallo“. "),
    ("das haus doppelpunkt es ist gross",
     "Das haus: es ist gross"),
]


@pytest.mark.parametrize("raw,expected", DE_CASES)
def test_german(raw, expected):
    assert fmt("de", raw) == expected


def test_german_only_capitalizes_sentence_start():
    # "haus" (nom commun) n'est pas capitalisé en milieu de phrase : décision
    # n°5 de la spec (pas d'analyseur morphologique).
    assert fmt("de", "das haus ist gross") == "Das haus ist gross"


def test_german_no_space_before_question_mark():
    assert " ?" not in fmt("de", "wirklich fragezeichen")
    assert NNBSP not in fmt("de", "wirklich fragezeichen")


# --------------------------------------------------------------------------- #
# Espagnol : ouvrants ¿ ¡ par commande explicite, pas d'insertion auto         #
# --------------------------------------------------------------------------- #

ES_CASES = [
    ("abrir interrogación cómo estás interrogación",
     "¿Cómo estás? "),
    ("dice abrir exclamación qué bien exclamación",
     "Dice ¡qué bien! "),
    ("primera frase punto segunda frase",
     "Primera frase. Segunda frase"),
    ("hola coma cómo estás",
     "Hola, cómo estás"),
]


@pytest.mark.parametrize("raw,expected", ES_CASES)
def test_spanish(raw, expected):
    assert fmt("es", raw) == expected


def test_spanish_no_automatic_opening_mark():
    # sans "abrir interrogación", aucun ¿ n'est ajouté.
    assert "¿" not in fmt("es", "cómo estás interrogación")


def test_spanish_no_space_before_marks():
    assert " ?" not in fmt("es", "qué interrogación")
    assert " !" not in fmt("es", "vamos exclamación")


# --------------------------------------------------------------------------- #
# Correction de capitalize : ne jamais minusculiser la fin du mot              #
# --------------------------------------------------------------------------- #

def test_capitalize_does_not_lowercase_rest_of_word():
    # entrée déjà capitalisée (cas custom_vocabulary en début de phrase)
    tp = TextProcessor("en")
    tp.capitalize_next_word = True
    assert tp._format_parts(["iPhone", "works"]).startswith("IPhone")
    # et surtout : pas "Iphone"
    assert "Iphone" not in tp._format_parts(["iPhone"])


# --------------------------------------------------------------------------- #
# Tokeniseur : une commande de ponctuation n'est reconnue que sur des jetons   #
# COMPLETS (jamais comme préfixe d'un mot plus long)                           #
# --------------------------------------------------------------------------- #

def test_point_inside_longer_word_is_not_a_command():
    # "points" = mot ordinaire (préfixe "point" ne doit pas être reconnu).
    out = TextProcessor("fr").process("mettre les points sur les i")
    assert "." not in out
    assert "points" in out


def test_point_inside_other_words_is_not_a_command():
    out = TextProcessor("fr").process("pointu et appointer")
    assert "." not in out


def test_multi_word_command_still_recognized():
    # "à la ligne" (trois mots consécutifs) reste reconnue comme une commande.
    out = TextProcessor("fr").process("à la ligne")
    assert "\n" in out


def test_final_point_recognized_as_command():
    out = TextProcessor("fr").process("texte fin point")
    assert "fin." in out


def test_isolated_point_recognized_as_command():
    out = TextProcessor("fr").process("fin de phrase point")
    assert out.lower().startswith("fin de phrase.")


# --------------------------------------------------------------------------- #
# T1 : mode de saisie de la ponctuation par langue (inline | explicit)         #
# --------------------------------------------------------------------------- #

def _set_fr_punctuation_mode(monkeypatch, mode, trigger=None):
    """Force the fr punctuation mode / trigger for a single test."""
    punct = config.language_settings["fr"]["punctuation"]
    monkeypatch.setitem(punct, "mode", mode)
    if trigger is not None:
        monkeypatch.setitem(punct, "trigger", trigger)


def test_inline_mode_converts_command_without_trigger(monkeypatch):
    _set_fr_punctuation_mode(monkeypatch, "inline")
    assert ", " in fmt("fr", "phrase virgule suite")


def test_explicit_keeps_command_without_trigger(monkeypatch):
    _set_fr_punctuation_mode(monkeypatch, "explicit", trigger="ponctuation")
    out = fmt("fr", "phrase virgule suite")
    assert "virgule" in out
    assert "," not in out


def test_explicit_converts_command_after_trigger(monkeypatch):
    _set_fr_punctuation_mode(monkeypatch, "explicit", trigger="ponctuation")
    out = fmt("fr", "phrase ponctuation virgule suite")
    assert "," in out
    assert "ponctuation" not in out


def test_explicit_converts_multiword_command_after_trigger(monkeypatch):
    _set_fr_punctuation_mode(monkeypatch, "explicit", trigger="ponctuation")
    out = fmt("fr", "ponctuation à la ligne")
    assert "\n" in out
    assert "ponctuation" not in out


def test_explicit_keeps_trigger_when_not_followed_by_command(monkeypatch):
    _set_fr_punctuation_mode(monkeypatch, "explicit", trigger="ponctuation")
    out = fmt("fr", "dire ponctuation bonjour")
    assert "ponctuation" in out
    assert "bonjour" in out


def test_explicit_no_dot_inside_plain_words(monkeypatch):
    _set_fr_punctuation_mode(monkeypatch, "explicit", trigger="ponctuation")
    assert "." not in fmt("fr", "mettre les points sur les i")


# --------------------------------------------------------------------------- #
# T5 : appariement des commandes de ponctuation insensible aux accents        #
# (le modèle Vosk rend parfois "a la ligne" pour "à la ligne")                #
# --------------------------------------------------------------------------- #

def test_command_matches_without_accents():
    out = TextProcessor("fr").process("va a la ligne puis ecris")
    assert "\n" in out


def test_accent_insensitive_does_not_overmatch():
    # "tire" (sans accent) ne doit pas être pris pour "tiret".
    out = TextProcessor("fr").process("il a tire au sort")
    assert "–" not in out


def test_dash_homophone_aliases_ship_by_default():
    # R2 (28/08 soir, arbitrage option 1) : les homophones de « tiret »
    # réellement transcrits par le modèle fr (matrice Piper : « tirer »,
    # « tirés », « tirait », « tirez ») sont livrés par défaut.
    for form in ("tirez", "tirés", "tirer", "tirait"):
        out = TextProcessor("fr").process("voici {} le texte".format(form))
        assert "–" in out, form
    # « trait » reste un mot ordinaire (refus R2) : aucun tiret parasite.
    out = TextProcessor("fr").process("un trait de génie")
    assert "–" not in out
