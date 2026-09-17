# src/voice_commands.py
#
# Détection tokenisée des phrases de déclenchement.
#
# Remplace l'ancien test de sous-chaîne `config.STOP_WORD in raw_text_lower`
# (src/ui.py) par une correspondance sur la suite de tokens : la phrase-clé ne
# se déclenche que si ses mots apparaissent, dans l'ordre, comme une sous-suite
# contiguë du texte reconnu. Fonctions pures, sans dépendance au reste de
# l'application — testables directement.

import re


def normalize_tokens(text: str) -> list:
    """Découpe en tokens comparables : minuscules, ponctuation ASCII retirée."""
    text = (text or "").lower()
    text = re.sub(r"[.,;:!?()\[\]«»\"„“…]", " ", text)
    return text.split()


def phrase_tokens(phrase: str) -> list:
    return normalize_tokens(phrase)


def find_phrase(tokens: list, needle: list) -> int:
    """Index du premier token de la première occurrence contiguë de `needle`
    dans `tokens`, ou -1. `needle` vide -> -1."""
    if not needle or len(needle) > len(tokens):
        return -1
    last = len(tokens) - len(needle)
    for i in range(last + 1):
        if tokens[i:i + len(needle)] == needle:
            return i
    return -1


def ends_with_phrase(tokens: list, needle: list) -> bool:
    """La phrase-clé est-elle exactement la fin de la suite de tokens ?
    Utilisé sur les résultats partiels en ÉCOUTE (réveil à faible latence)."""
    if not needle or len(needle) > len(tokens):
        return False
    return tokens[-len(needle):] == needle


def is_doubled(tokens: list, needle: list) -> bool:
    """Échappatoire littérale : la phrase-clé est dite deux fois de suite
    (« stop dictée stop dictée ») -> on la tape une fois au lieu de déclencher."""
    n = len(needle)
    if n == 0 or len(tokens) < 2 * n:
        return False
    idx = find_phrase(tokens, needle + needle)
    return idx != -1


def strip_one_repetition(text: str, needle: list) -> str:
    """Pour l'échappatoire littérale : retire *une* des deux répétitions
    consécutives de la phrase-clé dans `text`, en préservant la casse et la
    ponctuation d'origine autant que possible."""
    n = len(needle)
    if n == 0:
        return text
    words = text.split()
    low = [w.lower().strip(".,;:!?()[]«»\"„“…") for w in words]
    idx = find_phrase(low, needle + needle)
    if idx == -1:
        return text
    del words[idx:idx + n]
    return " ".join(words)


def remove_phrase_and_after(text: str, needle: list) -> str:
    """Texte situé *avant* la phrase-clé (le reste est jeté, comme le faisait
    l'ancien `raw_text.split(STOP_WORD, 1)[0]`)."""
    n = len(needle)
    if n == 0:
        return text.strip()
    words = text.split()
    low = [w.lower().strip(".,;:!?()[]«»\"„“…") for w in words]
    idx = find_phrase(low, needle)
    if idx == -1:
        return text.strip()
    return " ".join(words[:idx]).strip()


def mean_confidence(words: list, start_index: int, length: int) -> float:
    """Confiance moyenne des `length` mots de `words` à partir de `start_index`.

    `words` est la liste `result` d'un résultat final Vosk avec SetWords(True) :
    [{"word": "...", "conf": 0.97, "start": ..., "end": ...}, ...].
    Retourne 1.0 si l'information de confiance est absente (résultat partiel,
    ou binding sans SetWords) — le garde de confiance ne doit pas bloquer par
    manque de données, seulement sur une confiance réellement basse.
    """
    if not words:
        return 1.0
    span = words[start_index:start_index + length]
    confs = [w.get("conf") for w in span if isinstance(w, dict) and "conf" in w]
    confs = [c for c in confs if isinstance(c, (int, float))]
    if not confs:
        return 1.0
    return sum(confs) / len(confs)
