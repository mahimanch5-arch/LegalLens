"""
Document Chunking for LegalLens

Splits documents into semantic chunks for embedding and retrieval.
Preserves clause/sentence boundaries and legal document structure.
"""

import logging
from dataclasses import dataclass
from typing import Any

from tiktoken import get_encoding

logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    """Represents a document chunk"""
    id: str  # e.g., "doc_abc123~chunk_001"
    document_id: str
    chunk_number: int
    text: str
    token_count: int
    character_start: int  # Position in original document
    character_end: int
    metadata: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if self.metadata is None:
            self.metadata = {}


class DocumentChunker:
    """
    Chunk documents using recursive character splitting.

    This strategy:
    - Respects semantic boundaries (paragraphs > sentences > words)
    - Maintains context with overlap
    - Preserves legal clause structure
    - Suitable for embedding and retrieval
    """

    # Configuration
    CHUNK_SIZE_TOKENS = 512          # Target chunk size
    CHUNK_OVERLAP_PERCENT = 0.20     # 20% overlap
    ENCODING = "cl100k_base"         # OpenAI tokenizer

    # Separators (in order of preference)
    SEPARATORS = [
        "\n\n",                      # Paragraph breaks (strongest)
        "\n",                        # Line breaks
        ". ",                        # Sentences
        " ",                         # Words
        ""                           # Characters (fallback)
    ]

    def __init__(self,
                 chunk_size_tokens: int = CHUNK_SIZE_TOKENS,
                 chunk_overlap_percent: float = CHUNK_OVERLAP_PERCENT):
        """
        Initialize chunker.

        Args:
            chunk_size_tokens: Target chunk size in tokens
            chunk_overlap_percent: Overlap percentage (0.0-1.0)
        """
        self.chunk_size_tokens = chunk_size_tokens
        self.chunk_overlap_percent = chunk_overlap_percent
        self.chunk_overlap_tokens = int(chunk_size_tokens * chunk_overlap_percent)

        try:
            self.encoding = get_encoding(self.ENCODING)
        except Exception:
            logger.warning(f"Could not load {self.ENCODING} encoding, using fallback")
            self.encoding = None

    def chunk_document(self,
                      document_id: str,
                      text: str,
                      metadata: dict[str, Any] | None = None) -> list[Chunk]:
        """
        Split document into chunks.

        Args:
            document_id: Unique document identifier
            text: Full document text
            metadata: Additional metadata to include in chunks

        Returns:
            List of Chunk objects
        """
        chunks = []

        # Split text recursively
        split_texts = self._recursive_split(text)

        # Group splits into chunks of target size
        current_chunk = ""
        current_start = 0
        chunk_num = 1

        for split in split_texts:
            # Count tokens in potential combined chunk
            potential_chunk = current_chunk + split
            token_count = self._count_tokens(potential_chunk)

            if token_count > self.chunk_size_tokens and current_chunk:
                # Current chunk is full, save it
                chunk_tokens = self._count_tokens(current_chunk)
                chunks.append(Chunk(
                    id=f"{document_id}~chunk_{chunk_num:03d}",
                    document_id=document_id,
                    chunk_number=chunk_num,
                    text=current_chunk.strip(),
                    token_count=chunk_tokens,
                    character_start=current_start,
                    character_end=current_start + len(current_chunk),
                    metadata=metadata or {}
                ))

                # Start new chunk with overlap
                if self.chunk_overlap_tokens > 0:
                    # Include last N tokens for context
                    overlap_text = self._get_last_n_tokens(current_chunk, self.chunk_overlap_tokens)
                    current_chunk = overlap_text + split
                    current_start = current_start + len(current_chunk) - len(overlap_text) - len(split)
                else:
                    current_chunk = split
                    current_start = current_start + len(current_chunk)

                chunk_num += 1
            else:
                # Add to current chunk
                current_chunk = potential_chunk

        # Add final chunk if not empty
        if current_chunk.strip():
            chunk_tokens = self._count_tokens(current_chunk)
            chunks.append(Chunk(
                id=f"{document_id}~chunk_{chunk_num:03d}",
                document_id=document_id,
                chunk_number=chunk_num,
                text=current_chunk.strip(),
                token_count=chunk_tokens,
                character_start=current_start,
                character_end=current_start + len(current_chunk),
                metadata=metadata or {}
            ))

        logger.info(f"Chunked document {document_id} into {len(chunks)} chunks")
        return chunks

    def _recursive_split(self, text: str, separators: list[str] | None = None) -> list[str]:
        """
        Recursively split text using separators in order.
        Tries to keep splits together until size limit, then moves to next separator.
        """
        if separators is None:
            separators = self.SEPARATORS

        good_splits = []
        separator = separators[-1]

        for i, _separator in enumerate(separators):
            if _separator == "":
                splits = list(text)
                break

            if _separator in text:
                if i == 0:
                    splits = text.split(_separator)
                else:
                    _good_splits = text.split(_separator)
                    good_splits = [s for s in _good_splits if len(s) > 0]

                separator = _separator
                break

        # Now go recursively through good_splits
        _good_splits = []
        for s in (good_splits or splits):
            if len(s) > 0:
                if self._count_tokens(s) < self.chunk_size_tokens:
                    _good_splits.append(s)
                else:
                    # Recursively split this part
                    if _good_splits:
                        merged_text = separator.join(_good_splits)
                        _good_splits = [merged_text]

                    other_splits = self._recursive_split(s, separators[separators.index(separator) + 1:])
                    _good_splits.extend(other_splits)

        return _good_splits

    def _count_tokens(self, text: str) -> int:
        """Count tokens in text"""
        if self.encoding:
            try:
                return len(self.encoding.encode(text))
            except Exception:
                pass

        # Fallback: rough estimate (1 token ≈ 4 characters)
        return len(text) // 4

    def _get_last_n_tokens(self, text: str, n: int) -> str:
        """Get last n tokens from text (for overlap)"""
        if self.encoding:
            try:
                tokens = self.encoding.encode(text)
                if len(tokens) <= n:
                    return text

                # Take last n tokens
                last_tokens = tokens[-n:]
                return str(self.encoding.decode(last_tokens))
            except Exception:
                pass

        # Fallback: rough estimate
        chars_per_token = 4
        char_count = n * chars_per_token
        return text[-char_count:]


# Convenience function
def chunk_document(document_id: str,
                  text: str,
                  chunk_size_tokens: int = DocumentChunker.CHUNK_SIZE_TOKENS,
                  overlap_percent: float = DocumentChunker.CHUNK_OVERLAP_PERCENT,
                  metadata: dict[str, Any] | None = None) -> list[Chunk]:
    """
    Simple function to chunk a document.

    Args:
        document_id: Unique document ID
        text: Document text
        chunk_size_tokens: Chunk size in tokens (default 512)
        overlap_percent: Overlap percentage (default 0.20 = 20%)
        metadata: Additional metadata

    Returns:
        List of Chunk objects
    """
    chunker = DocumentChunker(chunk_size_tokens, overlap_percent)
    return chunker.chunk_document(document_id, text, metadata)


if __name__ == "__main__":
    # Test

    logging.basicConfig(level=logging.INFO)

    # Sample legal text
    sample_text = """
    Section 5. Termination. Either party may terminate this agreement with
    thirty (30) days written notice to the other party. Termination is effective
    upon written receipt by the other party. Upon termination, all obligations
    under this agreement shall cease, except those that by their nature are
    intended to survive termination.

    Section 6. Confidentiality. Each party agrees to maintain the confidentiality
    of any proprietary information received from the other party. Confidential
    information shall not be disclosed to third parties without prior written consent.
    """

    chunker = DocumentChunker(chunk_size_tokens=100)  # Small for demo
    chunks = chunker.chunk_document("test_doc_001", sample_text)

    print(f"\nChunked into {len(chunks)} chunks:\n")
    for chunk in chunks:
        print(f"Chunk {chunk.chunk_number}:")
        print(f"  Tokens: {chunk.token_count}")
        print(f"  Text: {chunk.text[:80]}...")
        print()
