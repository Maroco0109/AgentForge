"""Text chunking for LLM processing."""

from dataclasses import dataclass, field


@dataclass
class TextChunk:
    """A chunk of text."""

    content: str
    index: int
    start_char: int
    end_char: int
    metadata: dict = field(default_factory=dict)


class TextChunker:
    """Split text into chunks suitable for LLM processing."""

    def __init__(self, chunk_size: int = 1000, overlap: int = 200):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, text: str, metadata: dict | None = None) -> list[TextChunk]:
        """Split text into overlapping chunks."""
        if not text:
            return []

        chunks = []
        start = 0
        index = 0

        while start < len(text):
            end = start + self.chunk_size

            # Try to break at sentence boundary
            if end < len(text):
                # Look for sentence-ending punctuation near the end
                for sep in [".\n", ". ", "? ", "! ", "\n\n", "\n"]:
                    boundary = text.rfind(sep, start + self.chunk_size // 2, end)
                    if boundary != -1:
                        end = boundary + len(sep)
                        break

            chunk_text = text[start:end].strip()
            if chunk_text:
                chunks.append(
                    TextChunk(
                        content=chunk_text,
                        index=index,
                        start_char=start,
                        end_char=end,
                        metadata=metadata or {},
                    )
                )
                index += 1

            # Move start with overlap
            start = end - self.overlap if end < len(text) else end

        return chunks


text_chunker = TextChunker()
