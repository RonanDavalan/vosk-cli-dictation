import re
import unicodedata
from config.config import config


def _strip_accents(s: str) -> str:
    """Minuscule sans diacritiques — pour comparer les commandes de ponctuation
    quand le modèle Vosk rend « a la ligne » au lieu de « à la ligne » (T5)."""
    return "".join(
        c for c in unicodedata.normalize("NFKD", s.lower())
        if not unicodedata.combining(c)
    )


class TextProcessor:
    def __init__(self, language_code: str):
        # Punctuation mechanics that are near-universal (bracket / quote
        # attachment). The locale-variable parts — thin space, sentence
        # capitalization, quote glyphs — come from the per-language
        # `typography` block instead (chantier 7 volet F).
        self.no_space_after = {'(', '[', '« ', '„', '¿', '¡'}
        self.no_space_before = {',', '.', ')', ']', '?', '!', ':', ';', '»', '…', '“'}
        # Add state to handle capitalization contextually.
        self.capitalize_next_word = True
        self.update_language(language_code)

    def update_language(self, language_code: str):
        """Updates the processor's settings for a new language."""
        self.lang = language_code
        self.settings = config.language_settings.get(language_code, {})
        self.typography = config.typography(language_code)
        self.space_before = set(self.typography['space_before'])
        self.thin_space = self.typography['thin_space']
        self.capitalize_sentence_start = self.typography['capitalize_sentence_start']
        # Merge all punctuation commands for easy lookup. The `mode` / `trigger`
        # keys are scalars, not command maps, so only dict sections contribute
        # (T1 : mode de saisie de la ponctuation par langue).
        self.all_punctuation_cmds = {}
        punctuation_sections = self.settings.get('punctuation', {}) or {}
        self.punctuation_mode = punctuation_sections.get('mode', 'inline')
        self.punctuation_trigger = punctuation_sections.get('trigger', 'ponctuation')
        for section in punctuation_sections.values():
            if isinstance(section, dict):
                self.all_punctuation_cmds.update(section)
        # Create a sorted list of punctuation commands for the tokenizer
        self.punctuation_keys = sorted(self.all_punctuation_cmds.keys(), key=len, reverse=True)
        # T5 : forme normalisée (sans accents) des mots de chaque clé, pour un
        # appariement tolérant aux diacritiques manquants dans la sortie Vosk.
        self._key_norm_words = {
            key: [_strip_accents(w) for w in key.split()]
            for key in self.punctuation_keys
        }
        self._trigger_norm = _strip_accents(self.punctuation_trigger)
        # Aliases, longest key first: a multi-word alias must win over any of
        # its own single words (chantier 7 volet F).
        aliases = self.settings.get('recognition_aliases', {}) or {}
        self.sorted_aliases = sorted(aliases.items(), key=lambda kv: len(kv[0]), reverse=True)

    def reset_state(self):
        """Resets the processor's state, e.g., for a new session."""
        self.capitalize_next_word = True

    def process(self, raw_text: str) -> str:
        """
        Processes a raw string of recognized text into a formatted string.
        The `is_first_word_of_sentence` flag is now managed internally.
        """
        # STEP 0: Pre-processing to clean up common spacing errors from Vosk.
        text = re.sub(r'\s+([,.?)!\];»…])', r'\1', raw_text)

        # STEP 1: Apply recognition aliases
        text = self._apply_aliases(text.lower())

        # STEP 2: Split text into words and punctuation commands
        parts = self._tokenize(text)

        # STEP 3: Format parts into a final string, managing state internally
        final_string = self._format_parts(parts)

        # STEP 4: Apply custom vocabulary for case correction
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
        """Splits the text into words and recognized punctuation commands.

        A punctuation command only matches when it occupies one or more *whole*
        tokens of the input (tokens = whitespace-separated sequences), never as
        a prefix of a longer word. Keys are tried longest-first (by number of
        words) so a multi-word command wins over its isolated words.
        """
        words = text.split()
        norm = [_strip_accents(w) for w in words]  # T5 : comparaison sans accents
        # Order keys by number of words, descending: the longest match wins.
        keys_by_len = sorted(self.punctuation_keys, key=lambda k: k.count(' ') + 1, reverse=True)

        # T1 : in `explicit` mode a punctuation command only fires when the
        # trigger word immediately precedes it; the trigger is then consumed.
        # Otherwise the words are emitted literally.
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
                            # Command not triggered: emit the words literally.
                            # A word that is also a command key is wrapped so
                            # _format_parts does not convert it (T1).
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
        """Separator placed before a symbol listed in typography.space_before."""
        return ' ' if self.thin_space else ' '

    def _format_parts(self, parts: list) -> str:
        """Assembles words and punctuation, respecting typographical rules and state."""
        output_str = ""
        for i, part in enumerate(parts):
            if part in self.all_punctuation_cmds:
                symbol = self.all_punctuation_cmds[part]

                # Remove space before punctuation that attaches to the word.
                if output_str.endswith(" ") and symbol in self.no_space_before:
                    output_str = output_str.rstrip()

                # Data-driven leading separator (French thin space, etc.).
                if symbol in self.space_before:
                    sep = self._lead_separator()
                    if output_str.endswith(' '):
                        output_str = output_str.rstrip()
                    if output_str and not output_str.endswith((' ', sep)):
                        output_str += sep

                output_str += symbol

                # Add space after punctuation that requires it
                if symbol not in self.no_space_after and not symbol.endswith('\n'):
                    output_str += " "

                # Set capitalization state if the punctuation marks the end of a sentence.
                if symbol in ['.', '!', '?', '…', '« ', '„', '\n', '\n\n']:
                    self.capitalize_next_word = True
            else:  # This is a normal word
                word = part
                # T1 : in explicit mode a literal word that collides with a
                # command key is wrapped in a one-item tuple by _tokenize.
                if isinstance(word, tuple):
                    word = word[0]
                if self.capitalize_sentence_start and self.capitalize_next_word and word:
                    # Uppercase the first character only — never lowercase the
                    # rest (keeps "McDonald", "iPhone" intact).
                    word = word[:1].upper() + word[1:]
                    self.capitalize_next_word = False

                output_str += word

                # Add a space after a word if the next part isn't punctuation that attaches to it.
                is_last_part = (i == len(parts) - 1)
                if not is_last_part:
                    next_part = parts[i + 1]
                    if next_part in self.all_punctuation_cmds:
                        next_symbol = self.all_punctuation_cmds[next_part]
                        if next_symbol not in self.no_space_before and next_symbol not in self.space_before:
                            output_str += " "
                    else:
                        output_str += " "

                # Set capitalization state if the word itself ends with sentence-ending punctuation.
                if any(word.endswith(p) for p in ['.', '!', '?']):
                    self.capitalize_next_word = True

        # Clean up potential double spaces that might be introduced
        return re.sub(r' +', ' ', output_str)
