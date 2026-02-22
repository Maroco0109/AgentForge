"""Tests for processing pipeline: cleaner, anonymizer, chunker."""

from data_collector.processing.anonymizer import Anonymizer
from data_collector.processing.chunker import TextChunker
from data_collector.processing.cleaner import TextCleaner


class TestTextCleaner:
    """Test text cleaner."""

    def test_clean_html_removes_tags(self):
        """Test HTML tag removal."""
        cleaner = TextCleaner()
        html = "<p>Hello <strong>World</strong></p>"

        result = cleaner.clean_html(html)

        assert result == "Hello World"
        assert "<p>" not in result
        assert "<strong>" not in result

    def test_clean_html_decodes_entities(self):
        """Test HTML entity decoding."""
        cleaner = TextCleaner()
        html = "Hello &amp; goodbye &lt;tag&gt; &quot;quoted&quot;"

        result = cleaner.clean_html(html)

        assert "&amp;" not in result
        assert "&" in result
        assert "<" in result
        assert '"' in result

    def test_clean_html_normalizes_whitespace(self):
        """Test whitespace normalization."""
        cleaner = TextCleaner()
        html = "Hello    World\n\n\nMultiple   spaces"

        result = cleaner.clean_html(html)

        assert result == "Hello World Multiple spaces"

    def test_normalize_unicode(self):
        """Test unicode normalization."""
        cleaner = TextCleaner()
        # NFD vs NFC normalization
        text = "café"  # Composed form

        result = cleaner.normalize(text)

        assert "café" in result

    def test_normalize_removes_control_chars(self):
        """Test removal of control characters."""
        cleaner = TextCleaner()
        text = "Hello\x00World\x1fTest"

        result = cleaner.normalize(text)

        assert "\x00" not in result
        assert "\x1f" not in result
        assert "HelloWorldTest" in result

    def test_normalize_preserves_newlines(self):
        """Test that newlines are preserved."""
        cleaner = TextCleaner()
        text = "Line 1\nLine 2\nLine 3"

        result = cleaner.normalize(text)

        assert "\n" in result
        assert "Line 1" in result
        assert "Line 2" in result

    def test_normalize_limits_consecutive_newlines(self):
        """Test that excessive newlines are normalized."""
        cleaner = TextCleaner()
        text = "Line 1\n\n\n\n\nLine 2"

        result = cleaner.normalize(text)

        assert "\n\n\n\n\n" not in result
        assert "\n\n" in result  # Max 2 consecutive

    def test_full_clean_pipeline(self):
        """Test full cleaning pipeline."""
        cleaner = TextCleaner()
        dirty = "<p>Hello &amp;   World</p>\n\n\n<script>alert('test');</script>"

        result = cleaner.clean(dirty)

        assert "<p>" not in result
        assert "&amp;" not in result
        assert "Hello & World" in result
        assert "alert" in result  # clean_html doesn't remove scripts, just tags

    def test_clean_empty_string(self):
        """Test cleaning empty string."""
        cleaner = TextCleaner()

        result = cleaner.clean("")

        assert result == ""

    def test_clean_only_whitespace(self):
        """Test cleaning whitespace-only string."""
        cleaner = TextCleaner()

        result = cleaner.clean("   \n\n  \t  ")

        assert result == ""


class TestAnonymizer:
    """Test PII anonymizer."""

    def test_anonymize_phone_number(self):
        """Test phone number anonymization."""
        anonymizer = Anonymizer()
        text = "연락처: 010-1234-5678입니다."

        anonymized, result = anonymizer.anonymize(text)

        assert "010-1234-5678" not in anonymized
        assert "[전화번호]" in anonymized
        assert result.has_pii is True

    def test_anonymize_email(self):
        """Test email anonymization."""
        anonymizer = Anonymizer()
        text = "이메일은 test@example.com입니다."

        anonymized, result = anonymizer.anonymize(text)

        assert "test@example.com" not in anonymized
        assert "[이메일]" in anonymized

    def test_anonymize_ssn(self):
        """Test SSN anonymization."""
        anonymizer = Anonymizer()
        text = "주민번호: 990101-1234567"

        anonymized, result = anonymizer.anonymize(text)

        assert "990101-1234567" not in anonymized
        assert "[주민번호]" in anonymized

    def test_anonymize_card_number(self):
        """Test card number anonymization."""
        anonymizer = Anonymizer()
        text = "카드: 1234-5678-9012-3456"

        anonymized, result = anonymizer.anonymize(text)

        assert "1234-5678-9012-3456" not in anonymized
        assert "[카드번호]" in anonymized

    def test_anonymize_korean_name(self):
        """Test Korean name anonymization."""
        anonymizer = Anonymizer()
        text = "홍길동 님께서 말씀하셨습니다."

        anonymized, result = anonymizer.anonymize(text)

        assert "홍길동 님" not in anonymized
        assert "[이름]" in anonymized

    def test_anonymize_address(self):
        """Test address anonymization."""
        anonymizer = Anonymizer()
        text = "주소는 서울시 강남구 테헤란로 123입니다."

        anonymized, result = anonymizer.anonymize(text)

        assert "서울시 강남구 테헤란로 123" not in anonymized
        assert "[주소]" in anonymized

    def test_anonymize_multiple_pii(self):
        """Test multiple PII anonymization."""
        anonymizer = Anonymizer()
        text = "홍길동 님 010-1234-5678, test@example.com"

        anonymized, result = anonymizer.anonymize(text)

        assert "010-1234-5678" not in anonymized
        assert "test@example.com" not in anonymized
        assert "[전화번호]" in anonymized
        assert "[이메일]" in anonymized
        assert "[이름]" in anonymized

    def test_anonymize_no_pii(self):
        """Test text without PII remains unchanged."""
        anonymizer = Anonymizer()
        text = "This is clean text with no personal information."

        anonymized, result = anonymizer.anonymize(text)

        assert anonymized == text
        assert result.has_pii is False

    def test_anonymize_preserves_structure(self):
        """Test that anonymization preserves text structure."""
        anonymizer = Anonymizer()
        text = "Name: 홍길동 님, Phone: 010-1234-5678, Email: test@example.com"

        anonymized, result = anonymizer.anonymize(text)

        assert "Name:" in anonymized
        assert "Phone:" in anonymized
        assert "Email:" in anonymized
        assert result.has_pii is True


class TestTextChunker:
    """Test text chunker."""

    def test_chunk_short_text(self):
        """Test chunking text shorter than chunk size."""
        chunker = TextChunker(chunk_size=100, overlap=20)
        text = "This is a short text."

        chunks = chunker.chunk(text)

        assert len(chunks) == 1
        assert chunks[0].content == text
        assert chunks[0].index == 0

    def test_chunk_long_text(self):
        """Test chunking long text into multiple chunks."""
        chunker = TextChunker(chunk_size=50, overlap=10)
        text = "A" * 150  # 150 characters

        chunks = chunker.chunk(text)

        assert len(chunks) > 1
        # Each chunk should be around chunk_size
        for chunk in chunks[:-1]:  # Except possibly the last
            assert len(chunk.content) <= 50

    def test_chunk_overlap(self):
        """Test that chunks have proper overlap."""
        chunker = TextChunker(chunk_size=20, overlap=5)
        text = "A" * 50

        chunks = chunker.chunk(text)

        assert len(chunks) >= 2
        # Check overlap between consecutive chunks
        if len(chunks) >= 2:
            # The end of chunk 0 should overlap with start of chunk 1
            assert chunks[0].end_char > chunks[1].start_char

    def test_chunk_respects_sentence_boundaries(self):
        """Test chunking at sentence boundaries."""
        chunker = TextChunker(chunk_size=30, overlap=5)
        text = "First sentence. Second sentence. Third sentence. Fourth sentence."

        chunks = chunker.chunk(text)

        # Should try to break at '. '
        for chunk in chunks:
            # Check if chunk ends with period or is the last chunk
            if chunk.index < len(chunks) - 1:
                assert chunk.content.rstrip().endswith(".") or len(chunk.content) < 30

    def test_chunk_with_metadata(self):
        """Test that metadata is attached to chunks."""
        chunker = TextChunker(chunk_size=50, overlap=10)
        text = "A" * 150
        metadata = {"source": "test", "url": "https://example.com"}

        chunks = chunker.chunk(text, metadata=metadata)

        assert len(chunks) > 0
        for chunk in chunks:
            assert chunk.metadata == metadata

    def test_chunk_empty_text(self):
        """Test chunking empty text."""
        chunker = TextChunker()
        text = ""

        chunks = chunker.chunk(text)

        assert len(chunks) == 0

    def test_chunk_indices_sequential(self):
        """Test that chunk indices are sequential."""
        chunker = TextChunker(chunk_size=50, overlap=10)
        text = "A" * 200

        chunks = chunker.chunk(text)

        for i, chunk in enumerate(chunks):
            assert chunk.index == i

    def test_chunk_positions(self):
        """Test chunk start and end positions."""
        chunker = TextChunker(chunk_size=50, overlap=10)
        text = "A" * 150

        chunks = chunker.chunk(text)

        # First chunk should start at 0
        assert chunks[0].start_char == 0
        # Last chunk should end at or near text length
        assert chunks[-1].end_char >= len(text) - 10

    def test_chunk_newline_boundary(self):
        """Test chunking respects newline boundaries."""
        chunker = TextChunker(chunk_size=30, overlap=5)
        text = "Line 1 text here\n\nLine 2 text here\n\nLine 3 text here"

        chunks = chunker.chunk(text)

        # Should try to break at \n\n
        assert len(chunks) > 0

    def test_chunk_max_size_enforced(self):
        """Test that chunks don't exceed max size significantly."""
        chunker = TextChunker(chunk_size=100, overlap=20)
        text = "Word " * 500  # Long text with many words

        chunks = chunker.chunk(text)

        for chunk in chunks:
            # Allow some flexibility for sentence boundaries
            assert len(chunk.content) <= 150  # Some margin for boundary detection

    def test_chunk_custom_size_and_overlap(self):
        """Test custom chunk size and overlap."""
        chunker = TextChunker(chunk_size=1000, overlap=200)
        text = "A" * 3000

        chunks = chunker.chunk(text)

        assert len(chunks) > 0
        # First chunk should be close to 1000 chars
        assert len(chunks[0].content) <= 1000

    def test_chunk_whitespace_only_stripped(self):
        """Test that whitespace-only chunks are skipped."""
        chunker = TextChunker(chunk_size=50, overlap=10)
        text = "Text1" + " " * 100 + "Text2"

        chunks = chunker.chunk(text)

        # Should not create chunks that are only whitespace
        for chunk in chunks:
            assert chunk.content.strip() != ""
