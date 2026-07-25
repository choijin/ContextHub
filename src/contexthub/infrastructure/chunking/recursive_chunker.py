"""Deterministic recursive character chunker."""

from dataclasses import dataclass
from hashlib import sha256
from uuid import NAMESPACE_URL, uuid5

from contexthub.domain.exceptions import ChunkingError
from contexthub.domain.models.chunk import Chunk, ChunkingConfig
from contexthub.domain.models.document import NormalizedDocument

SEPARATORS = ["\n\n", "\n", ". ", " ", ""]


@dataclass(frozen=True)
class _TextSegment:
    text: str
    page_number: int


class RecursiveChunker:
    """Split normalized documents into deterministic page-aware chunks."""

    def chunk(self, document: NormalizedDocument, config: ChunkingConfig) -> list[Chunk]:
        try:
            segments = self._segments_for_document(document, config.chunk_size)
            return self._merge_segments(document, segments, config)
        except ChunkingError:
            raise
        except Exception as exc:
            raise ChunkingError("Failed to chunk document.") from exc

    def _segments_for_document(
        self,
        document: NormalizedDocument,
        chunk_size: int,
    ) -> list[_TextSegment]:
        segments: list[_TextSegment] = []
        for page in sorted(document.pages, key=lambda item: item.page_number):
            text = page.text.strip()
            if not text:
                continue
            for segment in self._split_text(text, chunk_size):
                normalized = segment.strip()
                if normalized:
                    segments.append(_TextSegment(text=normalized, page_number=page.page_number))
        return segments

    def _split_text(self, text: str, chunk_size: int) -> list[str]:
        if len(text) <= chunk_size:
            return [text]
        separator = self._best_separator(text, chunk_size)
        if separator == "":
            return [text[index : index + chunk_size] for index in range(0, len(text), chunk_size)]

        pieces = text.split(separator)
        split_segments: list[str] = []
        for piece in pieces:
            if not piece:
                continue
            candidate = piece if separator.isspace() else piece + separator
            if len(candidate) > chunk_size:
                split_segments.extend(self._split_text(candidate, chunk_size))
            else:
                split_segments.append(candidate)
        return split_segments

    @staticmethod
    def _best_separator(text: str, chunk_size: int) -> str:
        for separator in SEPARATORS:
            if separator == "":
                return separator
            longest_piece = max(len(piece) for piece in text.split(separator))
            if separator in text and longest_piece <= chunk_size:
                return separator
        return ""

    def _merge_segments(
        self,
        document: NormalizedDocument,
        segments: list[_TextSegment],
        config: ChunkingConfig,
    ) -> list[Chunk]:
        chunks: list[Chunk] = []
        current: list[_TextSegment] = []
        current_length = 0

        for segment in segments:
            separator_length = 1 if current else 0
            next_length = current_length + separator_length + len(segment.text)
            if current and next_length > config.chunk_size:
                chunk = self._make_chunk(document, current, len(chunks), config)
                chunks.append(chunk)
                current = self._overlap_segments(current, config.chunk_overlap)
                while (
                    current
                    and self._segments_length(current) + 1 + len(segment.text) > config.chunk_size
                ):
                    current.pop(0)
                current_length = self._segments_length(current)

            current.append(segment)
            current_length = self._segments_length(current)

        if current:
            chunks.append(self._make_chunk(document, current, len(chunks), config))

        return chunks

    @staticmethod
    def _segments_length(segments: list[_TextSegment]) -> int:
        if not segments:
            return 0
        return sum(len(segment.text) for segment in segments) + len(segments) - 1

    @staticmethod
    def _overlap_segments(segments: list[_TextSegment], overlap: int) -> list[_TextSegment]:
        if overlap <= 0:
            return []
        selected: list[_TextSegment] = []
        total = 0
        for segment in reversed(segments):
            next_total = total + len(segment.text) + (1 if selected else 0)
            if selected and next_total > overlap:
                break
            selected.append(segment)
            total = next_total
            if total >= overlap:
                break
        return list(reversed(selected))

    def _make_chunk(
        self,
        document: NormalizedDocument,
        segments: list[_TextSegment],
        chunk_index: int,
        config: ChunkingConfig,
    ) -> Chunk:
        text = " ".join(segment.text for segment in segments).strip()
        if not text:
            raise ChunkingError("Chunk text must not be empty.")
        content_hash = sha256(text.encode("utf-8")).hexdigest()
        page_numbers = [segment.page_number for segment in segments]
        page_start = min(page_numbers)
        page_end = max(page_numbers)
        id_input = (
            f"{document.document_id}:{chunk_index}:{page_start}:{page_end}:"
            f"{content_hash}:{config.chunk_size}:{config.chunk_overlap}"
        )
        return Chunk(
            id=str(uuid5(NAMESPACE_URL, id_input)),
            document_id=document.document_id,
            text=text,
            chunk_index=chunk_index,
            page_start=page_start,
            page_end=page_end,
            content_hash=content_hash,
        )
