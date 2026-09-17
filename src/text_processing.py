import re
import unicodedata
from config.config import config


def _strip_accents(s: str) -> str:
    """Minuscule sans diacritiques — pour comparer les commandes de ponctuation
    quand le modèle Vosk rend « a la ligne » au lieu de « à la ligne »
    (comparaison sans accents)."""
    return "".join(
        c for c in unicodedata.normalize("NFKD", s.lower())
        if not unicodedata.combining(c)
    )


class TextProcessor:
    def __init__(self, language_code: str):
        # Mécanique de ponctuation quasi universelle (collement des
        # parenthèses et guillemets). Les parties variables par locale —
        # espace fine, majuscule de début de phrase, glyphes de guillemets —
        # viennent du bloc `typography` par langue.
        self.no_space_after = {'(', '[', '« ', '„', '¿', '¡'}
        self.no_space_before = {',', '.', ')', ']', '?', '!', ':', ';', '»', '…', '“'}
        # Add state to handle capitalization contextually.
        self.capitalize_next_word = True
        self.update_language(language_code)

    def update_language(self, language_code: str):
        """Met à jour les réglages du processeur pour une nouvelle langue."""
        self.lang = language_code
        self.settings = config.language_settings.get(language_code, {})
        self.typography = config.typography(language_code)
        self.space_before = set(self.typography['space_before'])
        self.thin_space = self.typography['thin_space']
        self.capitalize_sentence_start = self.typography['capitalize_sentence_start']
        # Fusionne toutes les commandes de ponctuation pour une recherche
        # simple. Les clés `mode` / `trigger` sont des scalaires, pas des
        # tables de commandes : seules les sections dict contribuent (mode de
        # saisie de la ponctuation par langue).
        self.all_punctuation_cmds = {}
        punctuation_sections = self.settings.get('punctuation', {}) or {}
        self.punctuation_mode = punctuation_sections.get('mode', 'inline')
        self.punctuation_trigger = punctuation_sections.get('trigger', 'ponctuation')
        for section in punctuation_sections.values():
            if isinstance(section, dict):
                self.all_punctuation_cmds.update(section)
        # Trie les commandes de ponctuation pour le tokeniseur (plus longue d'abord).
        self.punctuation_keys = sorted(self.all_punctuation_cmds.keys(), key=len, reverse=True)
        # Forme normalisée (sans accents) des mots de chaque clé, pour un
        # appariement tolérant aux diacritiques manquants dans la sortie Vosk.
        self._key_norm_words = {
            key: [_strip_accents(w) for w in key.split()]
            for key in self.punctuation_keys
        }
        self._trigger_norm = _strip_accents(self.punctuation_trigger)
        # Alias, clé la plus longue d'abord : un alias multi-mots doit gagner
        # contre chacun de ses mots isolés.
        aliases = self.settings.get('recognition_aliases', {}) or {}
        self.sorted_aliases = sorted(aliases.items(), key=lambda kv: len(kv[0]), reverse=True)

    def reset_state(self):
        """Réinitialise l'état du processeur, p. ex. pour une nouvelle session."""
        self.capitalize_next_word = True

    def process(self, raw_text: str) -> str:
        """
        Met en forme une chaîne brute reconnue.
        Le drapeau `is_first_word_of_sentence` est désormais géré en interne.
        """
        # ÉTAPE 0 : prétraitement des erreurs d'espacement courantes de Vosk.
        text = re.sub(r'\s+([,.?)!\];»…])', r'\1', raw_text)

        # ÉTAPE 1 : appliquer les alias de reconnaissance
        text = self._apply_aliases(text.lower())

        # ÉTAPE 2 : découper le texte en mots et commandes de ponctuation
        parts = self._tokenize(text)

        # ÉTAPE 3 : assembler les parties en chaîne finale, état géré en interne
        final_string = self._format_parts(parts)

        # ÉTAPE 4 : appliquer le vocabulaire personnalisé pour la casse
        final_string = self._apply_custom_vocabulary(final_string)

        return final_string

    def _apply_aliases(self, text: str) -> str:
        for alias, correction in self.sorted_aliases:
            text = re.sub(r'\b' + re.escape(alias) + r'\b', correction, text)
        return text

    def _apply_custom_vocabulary(self, text: str) -> str:
        vocab = self.settings.get('custom_vocabulary', {})
        for original, replacement in vocab.items():
            pattern = r'\b' + re.escape(original) + r'\b'
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        return text

    def _tokenize(self, text: str) -> list:
        """Découpe le texte en mots et commandes de ponctuation reconnues.

        Une commande de ponctuation ne correspond que si elle occupe un ou
        plusieurs tokens *entiers* de l'entrée (un token = une suite séparée
        par des blancs), jamais comme préfixe d'un mot plus long. Les clés
        sont essayées de la plus longue à la plus courte (en nombre de mots)
        pour qu'une commande multi-mots gagne contre ses mots isolés.
        """
        words = text.split()
        norm = [_strip_accents(w) for w in words]  # comparaison sans accents
        # Ordonner les clés par nombre de mots, décroissant : le plus long gagne.
        keys_by_len = sorted(self.punctuation_keys, key=lambda k: k.count(' ') + 1, reverse=True)

        # En mode `explicit`, une commande de ponctuation ne se déclenche que
        # si le mot déclencheur la précède immédiatement ; le déclencheur est
        # alors consommé. Sinon les mots sont émis littéralement.
        explicit = self.punctuation_mode == 'explicit'
        trigger = self.punctuation_trigger

        tokens = []
        i = 0
        while i < len(words):
            matched = False
            for key in keys_by_len:
                key_norm = self._key_norm_words[key]
                n = len(key_norm)
                if norm[i:i + n] == key_norm:
                    key_words = key.split()
                    if explicit:
                        if tokens and _strip_accents(str(tokens[-1])) == self._trigger_norm \
                                and not isinstance(tokens[-1], tuple):
                            tokens[-1] = key
                        else:
                            # Commande non déclenchée : émettre les mots littéralement.
                            # Un mot qui est aussi une clé de commande est enveloppé
                            # pour que _format_parts ne le convertisse pas (mode explicite).
                            for w in key_words:
                                tokens.append((w,) if w in self.all_punctuation_cmds else w)
                    else:
                        tokens.append(key)
                    i += len(key_words)
                    matched = True
                    break
            if not matched:
                tokens.append(words[i])
                i += 1
        return tokens

    def _lead_separator(self) -> str:
        """Séparateur placé avant un symbole listé dans typography.space_before."""
        return ' ' if self.thin_space else ' '

    def _format_parts(self, parts: list) -> str:
        """Assemble mots et ponctuation selon les règles typographiques et l'état."""
        output_str = ""
        for i, part in enumerate(parts):
            if part in self.all_punctuation_cmds:
                symbol = self.all_punctuation_cmds[part]

                # Retirer l'espace devant une ponctuation collée au mot.
                if output_str.endswith(" ") and symbol in self.no_space_before:
                    output_str = output_str.rstrip()

                # Séparateur d'attaque piloté par les données (espace fine française, etc.).
                if symbol in self.space_before:
                    sep = self._lead_separator()
                    if output_str.endswith(' '):
                        output_str = output_str.rstrip()
                    if output_str and not output_str.endswith((' ', sep)):
                        output_str += sep

                output_str += symbol

                # Ajouter une espace après une ponctuation qui l'exige.
                if symbol not in self.no_space_after and not symbol.endswith('\n'):
                    output_str += " "

                # Passer en majuscule si la ponctuation finit une phrase.
                if symbol in ['.', '!', '?', '…', '« ', '„', '\n', '\n\n']:
                    self.capitalize_next_word = True
            else:  # Un mot normal
                word = part
                # En mode explicite, un mot littéral qui collide avec une clé
                # de commande est enveloppé dans un tuple à un élément par _tokenize.
                if isinstance(word, tuple):
                    word = word[0]
                if self.capitalize_sentence_start and self.capitalize_next_word and word:
                    # Ne mettre en majuscule que le premier caractère — jamais
                    # le reste en minuscule (préserve "McDonald", "iPhone").
                    word = word[:1].upper() + word[1:]
                    self.capitalize_next_word = False

                output_str += word

                # Ajouter une espace après un mot sauf si la partie suivante est
                # une ponctuation collée.
                is_last_part = (i == len(parts) - 1)
                if not is_last_part:
                    next_part = parts[i + 1]
                    if next_part in self.all_punctuation_cmds:
                        next_symbol = self.all_punctuation_cmds[next_part]
                        if next_symbol not in self.no_space_before and next_symbol not in self.space_before:
                            output_str += " "
                    else:
                        output_str += " "

                # Passer en majuscule si le mot finit lui-même par une ponctuation de fin de phrase.
                if any(word.endswith(p) for p in ['.', '!', '?']):
                    self.capitalize_next_word = True

        # Éliminer les doubles espaces éventuellement introduites.
        return re.sub(r' +', ' ', output_str)
