"""Taille en octets des archives de modèles, pour afficher « à télécharger » avec
sa taille. Les valeurs sont celles de `src/model_download.py` (un test du projet
les compare) : le programme de l'icône n'importe pas la dictée."""

ARCHIVE_BYTES = {
    ("en", "small"): 41205931,
    ("fr", "small"): 42233323,
    ("de", "small"): 46499967,
    ("es", "small"): 39817833,
    ("en", "big"): 1913365522,
    ("fr", "big"): 1523026348,
    ("de", "big"): 2031717803,
    ("es", "big"): 1484681703,
}


# Mémoire vive en Mo après chargement, mesurée sur ada (banc des moteurs,
# `VAL_mesurer-moteurs.md`). Le complet anglais ne tient pas dans 8 Go : le banc a
# arrêté la mesure après plus de 5 Go consommés.
MEMORY_MB = {
    ("fr", "small"): 171, ("en", "small"): 178, ("de", "small"): 225, ("es", "small"): 156,
    ("fr", "big"): 3251, ("de", "big"): 4434, ("es", "big"): 3409,
}
MEMORY_OVER_MB = {("en", "big"): 5000}

_DECIMAL_COMMA = ("fr", "de", "es")
_UNITS = {"fr": ("Mo", "Go")}


def format_size(size_bytes: int, lang: str = "en") -> str:
    """« 41 MB » sous le gigaoctet, « 1.5 GB » au-delà (unités décimales) ; en français
    « 41 Mo » et « 1,5 Go », en allemand et en espagnol la virgule décimale."""
    mega, giga = _UNITS.get(lang, ("MB", "GB"))
    if size_bytes >= 1_000_000_000:
        text = "{:.1f} {}".format(size_bytes / 1_000_000_000, giga)
    else:
        text = "{:.0f} {}".format(size_bytes / 1_000_000, mega)
    return text.replace(".", ",") if lang in _DECIMAL_COMMA else text
