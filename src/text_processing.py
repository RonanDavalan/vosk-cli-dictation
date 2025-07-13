# src/text_processing.py

import re
from config.config import config

class TextProcessor:
    def __init__(self, language_code: str):
        self.update_language(language_code)
        # Define punctuation types for smarter spacing
        self.no_space_after = {'(', '[', '« '}
        self.no_space_before = {',', '.', ')', ']', '?', '!', ':', ';', '»', '…'}
        # Add state to handle capitalization contextually.
        self.capitalize_next_word = True

    def update_language(self, language_code: str):
        """Updates the processor's settings for a new language."""
        self.lang = language_code
        self.settings = config.language_settings.get(language_code, {})
        # Merge all punctuation commands for easy lookup
        self.all_punctuation_cmds = {}
        punctuation_sections = self.settings.get('punctuation', {})
        if punctuation_sections:
            for section in punctuation_sections.values():
                self.all_punctuation_cmds.update(section)
        # Create a sorted list of punctuation commands for the tokenizer
        self.punctuation_keys = sorted(self.all_punctuation_cmds.keys(), key=len, reverse=True)

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
        aliases = self.settings.get('recognition_aliases', {})
        for alias, correction in aliases.items():
            text = re.sub(r'\b' + re.escape(alias) + r'\b', correction, text)
        return text

    def _apply_custom_vocabulary(self, text: str) -> str:
        vocab = self.settings.get('custom_vocabulary', {})
        for original, replacement in vocab.items():
            pattern = r'\b' + re.escape(original) + r'\b'
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        return text

    def _tokenize(self, text: str) -> list:
        """Splits the text into words and recognized punctuation commands."""
        tokens = []
        # Use a regex that preserves punctuation commands as whole tokens
        # It creates a pattern like: (tiret|point virgule|...|word1|word2)
        punctuation_pattern = '|'.join(re.escape(key) for key in self.punctuation_keys)
        # Tokenize by finding punctuation commands or sequences of non-space characters
        pattern = re.compile(f"({punctuation_pattern}|\\S+)")
        words_and_cmds = pattern.findall(text)

        i = 0
        while i < len(words_and_cmds):
            # Check for multi-word punctuation commands first
            matched = False
            for key in self.punctuation_keys:
                key_words = key.split()
                if ' ' in key and words_and_cmds[i:i + len(key_words)] == key_words:
                    tokens.append(key)
                    i += len(key_words)
                    matched = True
                    break
            if not matched:
                tokens.append(words_and_cmds[i])
                i += 1
        return tokens

    def _format_parts(self, parts: list) -> str:
        """Assembles words and punctuation, respecting typographical rules and state."""
        output_str = ""
        for i, part in enumerate(parts):
            if part in self.all_punctuation_cmds:
                symbol = self.all_punctuation_cmds[part]

                # Remove space before punctuation that requires it
                if output_str.endswith(" ") and symbol in self.no_space_before:
                    output_str = output_str.rstrip()

                # Add non-breaking space for French double punctuation
                if self.lang == 'fr' and symbol in ['?', '!', ':', ';', '»']:
                    if not output_str.endswith(('\u202f', ' ')):
                         output_str += '\u202f'  # Narrow no-break space
                    elif output_str.endswith(' '):
                         output_str = output_str.rstrip() + '\u202f'

                output_str += symbol

                # Add space after punctuation that requires it
                if symbol not in self.no_space_after and not symbol.endswith('\n'):
                    output_str += " "

                # --- MODIFICATION CLÉ ---
                # Set capitalization state if the punctuation marks the end of a sentence.
                if symbol in ['.', '!', '?', '…', '« ', '\n', '\n\n']:
                    self.capitalize_next_word = True
            else: # This is a normal word
                word = part
                if self.capitalize_next_word and word:
                    word = word.capitalize()
                    self.capitalize_next_word = False

                output_str += word

                # Add a space after a word if the next part isn't punctuation that attaches to it.
                is_last_part = (i == len(parts) - 1)
                if not is_last_part:
                    next_part = parts[i+1]
                    if next_part in self.all_punctuation_cmds:
                        next_symbol = self.all_punctuation_cmds[next_part]
                        if next_symbol not in self.no_space_before:
                            output_str += " "
                    else:
                        output_str += " "

                # Set capitalization state if the word itself ends with sentence-ending punctuation.
                if any(word.endswith(p) for p in ['.', '!', '?']):
                    self.capitalize_next_word = True

        # Clean up potential double spaces that might be introduced
        return re.sub(r' +', ' ', output_str)
