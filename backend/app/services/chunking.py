from __future__ import annotations

import re
from app.models.domain import Chunk, Document
from app.services.embedding import EmbeddingService
from app.services.text_utils import HEADING_RE, normalize_space


class HierarchicalChunker:
    def __init__(self, embedder: EmbeddingService, target_chars: int = 1100) -> None:
        self.embedder = embedder
        self.target_chars = target_chars

    def chunk(self, document: Document) -> list[Chunk]:
        blocks = self._blocks_with_paths(document.content)
        chunks: list[Chunk] = []
        order = 0
        for section_path, text in blocks:
            for piece in self._split_semantic(text):
                normalized = normalize_space(piece)
                if not normalized:
                    continue
                chunk = Chunk(
                    document_id=document.id,
                    text=normalized,
                    section_path=section_path or [document.title],
                    order_index=order,
                    tags=document.tags,
                )
                chunk.embedding = self.embedder.embed(
                    " > ".join(chunk.section_path) + "\n" + chunk.text
                )
                chunks.append(chunk)
                order += 1
        return chunks

    def _blocks_with_paths(self, content: str) -> list[tuple[list[str], str]]:
        path: list[str] = []
        current_lines: list[str] = []
        current_path: list[str] = []
        blocks: list[tuple[list[str], str]] = []

        def flush() -> None:
            if current_lines:
                blocks.append((current_path.copy(), "\n".join(current_lines).strip()))
                current_lines.clear()

        for line in content.splitlines():
            match = HEADING_RE.match(line)
            if match:
                flush()
                level = len(match.group(1))
                heading = match.group(2).strip()
                path[:] = path[: level - 1]
                path.append(heading)
                current_path[:] = path
                continue
            current_lines.append(line)
        flush()
        return blocks or [([], content)]

    def _split_semantic(self, text: str) -> list[str]:
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
        pieces: list[str] = []
        current = ""
        for paragraph in paragraphs:
            if len(current) + len(paragraph) + 2 <= self.target_chars:
                current = f"{current}\n\n{paragraph}".strip()
                continue
            if current:
                pieces.append(current)
            if len(paragraph) <= self.target_chars:
                current = paragraph
            else:
                pieces.extend(self._split_long_paragraph(paragraph))
                current = ""
        if current:
            pieces.append(current)
        return pieces

    def _split_long_paragraph(self, paragraph: str) -> list[str]:
        sentences = re.split(r"(?<=[.!?。！？])\s+", paragraph)
        pieces: list[str] = []
        current = ""
        for sentence in sentences:
            if len(current) + len(sentence) + 1 <= self.target_chars:
                current = f"{current} {sentence}".strip()
            else:
                if current:
                    pieces.append(current)
                current = sentence
        if current:
            pieces.append(current)
        return pieces
