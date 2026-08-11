"""SQLite document and chunk metadata repository."""

import json
import sqlite3
from pathlib import Path
from threading import RLock
from uuid import UUID

from contexthub.domain.exceptions import RepositoryError
from contexthub.domain.models.chunk import Chunk
from contexthub.domain.models.document import Document


class SQLiteDocumentRepository:
    """Persist document metadata and FAISS-position mappings in SQLite."""

    def __init__(self, database_path: Path, read_only: bool = False) -> None:
        self._database_path = database_path
        self._read_only = read_only
        self._lock = RLock()
        self._connection = self._connect(database_path, read_only)
        self._connection.execute("PRAGMA foreign_keys = ON")

    def reopen(self, database_path: Path) -> None:
        if self._read_only:
            raise RepositoryError("Cannot reopen read-only repository for writing.")
        with self._lock:
            self._connection.close()
            self._database_path = database_path
            self._connection = self._connect(database_path, read_only=False)
            self._connection.execute("PRAGMA foreign_keys = ON")

    def initialize_schema(self) -> None:
        if self._read_only:
            raise RepositoryError("Cannot initialize schema in read-only mode.")
        try:
            with self._lock:
                self._connection.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS documents (
                        id TEXT PRIMARY KEY,
                        filename TEXT NOT NULL,
                        title TEXT,
                        checksum_sha256 TEXT NOT NULL,
                        page_count INTEGER NOT NULL,
                        metadata_json TEXT NOT NULL DEFAULT '{}'
                    );

                    CREATE TABLE IF NOT EXISTS chunks (
                        id TEXT PRIMARY KEY,
                        document_id TEXT NOT NULL,
                        chunk_index INTEGER NOT NULL,
                        text TEXT NOT NULL,
                        page_start INTEGER NOT NULL,
                        page_end INTEGER NOT NULL,
                        content_hash TEXT NOT NULL,
                        faiss_position INTEGER NOT NULL UNIQUE,
                        FOREIGN KEY (document_id) REFERENCES documents(id)
                    );

                    CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON chunks(document_id);
                    """
                )
                self._connection.commit()
        except sqlite3.Error as exc:
            raise RepositoryError("Failed to initialize SQLite schema.") from exc

    def replace_all(
        self,
        documents: list[Document],
        chunks: list[Chunk],
        faiss_positions: dict[str, int],
    ) -> None:
        if self._read_only:
            raise RepositoryError("Cannot write in read-only mode.")
        if len(faiss_positions) != len(chunks):
            raise RepositoryError("Every chunk must have one FAISS position.")
        if sorted(faiss_positions.values()) != list(range(len(chunks))):
            raise RepositoryError("FAISS positions must be contiguous and zero-based.")

        try:
            with self._lock, self._connection:
                self._connection.execute("DELETE FROM chunks")
                self._connection.execute("DELETE FROM documents")
                self._connection.executemany(
                    """
                        INSERT INTO documents (
                            id, filename, title, checksum_sha256, page_count, metadata_json
                        ) VALUES (?, ?, ?, ?, ?, ?)
                        """,
                    [
                        (
                            str(document.id),
                            document.filename,
                            document.title,
                            document.checksum_sha256,
                            document.page_count,
                            json.dumps(document.metadata, sort_keys=True),
                        )
                        for document in documents
                    ],
                )
                self._connection.executemany(
                    """
                        INSERT INTO chunks (
                            id, document_id, chunk_index, text, page_start, page_end,
                            content_hash, faiss_position
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                    [
                        (
                            chunk.id,
                            str(chunk.document_id),
                            chunk.chunk_index,
                            chunk.text,
                            chunk.page_start,
                            chunk.page_end,
                            chunk.content_hash,
                            faiss_positions[chunk.id],
                        )
                        for chunk in chunks
                    ],
                )
        except sqlite3.Error as exc:
            raise RepositoryError("Failed to replace SQLite metadata.") from exc
        except KeyError as exc:
            raise RepositoryError("Missing FAISS position for chunk.") from exc

    def get_chunks_by_positions(self, positions: list[int]) -> list[Chunk]:
        if not positions:
            return []
        placeholders = ",".join("?" for _ in positions)
        try:
            with self._lock:
                rows = self._connection.execute(
                    f"""
                    SELECT id, document_id, chunk_index, text, page_start, page_end,
                           content_hash, faiss_position
                    FROM chunks
                    WHERE faiss_position IN ({placeholders})
                    """,
                    positions,
                ).fetchall()
        except sqlite3.Error as exc:
            raise RepositoryError("Failed to load chunks by FAISS positions.") from exc

        by_position = {int(row["faiss_position"]): row for row in rows}
        missing = [position for position in positions if position not in by_position]
        if missing:
            raise RepositoryError("Missing chunk metadata for FAISS position.")
        return [self._row_to_chunk(by_position[position]) for position in positions]

    def get_document_filenames(self, document_ids: list[UUID]) -> dict[UUID, str]:
        if not document_ids:
            return {}
        unique_ids = list(dict.fromkeys(document_ids))
        placeholders = ",".join("?" for _ in unique_ids)
        try:
            with self._lock:
                rows = self._connection.execute(
                    f"""
                    SELECT id, filename
                    FROM documents
                    WHERE id IN ({placeholders})
                    """,
                    [str(document_id) for document_id in unique_ids],
                ).fetchall()
        except sqlite3.Error as exc:
            raise RepositoryError("Failed to load document filenames.") from exc

        filenames = {UUID(str(row["id"])): str(row["filename"]) for row in rows}
        missing = [document_id for document_id in unique_ids if document_id not in filenames]
        if missing:
            raise RepositoryError("Missing document metadata for retrieved chunk.")
        return filenames

    def chunk_count(self) -> int:
        try:
            with self._lock:
                row = self._connection.execute("SELECT COUNT(*) AS count FROM chunks").fetchone()
        except sqlite3.Error as exc:
            raise RepositoryError("Failed to count chunks.") from exc
        return int(row["count"])

    def faiss_positions(self) -> list[int]:
        try:
            with self._lock:
                rows = self._connection.execute(
                    "SELECT faiss_position FROM chunks ORDER BY faiss_position"
                ).fetchall()
        except sqlite3.Error as exc:
            raise RepositoryError("Failed to load FAISS positions.") from exc
        return [int(row["faiss_position"]) for row in rows]

    def validate_faiss_positions(self, expected_count: int) -> None:
        positions = self.faiss_positions()
        if positions != list(range(expected_count)):
            raise RepositoryError("FAISS positions are not contiguous and zero-based.")

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    @staticmethod
    def _connect(database_path: Path, read_only: bool) -> sqlite3.Connection:
        try:
            if read_only:
                uri = f"file:{database_path}?mode=ro"
                connection = sqlite3.connect(uri, uri=True, check_same_thread=False)
            else:
                database_path.parent.mkdir(parents=True, exist_ok=True)
                connection = sqlite3.connect(database_path, check_same_thread=False)
            connection.row_factory = sqlite3.Row
            return connection
        except sqlite3.Error as exc:
            raise RepositoryError("Failed to open SQLite metadata database.") from exc

    @staticmethod
    def _row_to_chunk(row: sqlite3.Row) -> Chunk:
        return Chunk(
            id=str(row["id"]),
            document_id=UUID(str(row["document_id"])),
            chunk_index=int(row["chunk_index"]),
            text=str(row["text"]),
            page_start=int(row["page_start"]),
            page_end=int(row["page_end"]),
            content_hash=str(row["content_hash"]),
        )
