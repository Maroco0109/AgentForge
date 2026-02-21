"""Text cleaning and normalization."""

import html
import re
import unicodedata


class TextCleaner:
    """Clean and normalize text data."""

    def clean_html(self, text: str) -> str:
        """Remove HTML tags and decode entities."""
        # Decode HTML entities
        text = html.unescape(text)
        # Remove HTML tags
        text = re.sub(r"<[^>]+>", "", text)
        # Normalize whitespace
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def normalize(self, text: str) -> str:
        """Normalize text: whitespace, unicode, etc."""
        # Normalize unicode
        text = unicodedata.normalize("NFC", text)
        # Remove control characters (keep newlines and tabs)
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
        # Normalize whitespace (preserve single newlines)
        text = re.sub(r"[^\S\n]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def clean(self, text: str) -> str:
        """Full cleaning pipeline."""
        text = self.clean_html(text)
        text = self.normalize(text)
        return text


text_cleaner = TextCleaner()
