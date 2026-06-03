from __future__ import annotations

import re
import httpx
from bs4 import BeautifulSoup
from app.core.config import Settings
from app.models.domain import Document
from app.services.chunking import HierarchicalChunker
from app.services.guardrails import PromptInjectionScanner
from app.services.security import validate_public_http_url, validate_upload
from app.services.storage import KnowledgeStore
from app.services.text_utils import extract_tags, normalize_space, summarize
from app.services.vector_store import VectorIndex


class IngestionService:
    def __init__(
        self,
        store: KnowledgeStore,
        chunker: HierarchicalChunker,
        settings: Settings,
        vector_index: VectorIndex,
    ) -> None:
        self.store = store
        self.chunker = chunker
        self.settings = settings
        self.vector_index = vector_index
        self.prompt_scanner = PromptInjectionScanner()

    def ingest_text(
        self,
        title: str,
        content: str,
        source_type: str,
        source_uri: str | None = None,
        tags: list[str] | None = None,
    ) -> Document:
        tags = [*(tags or []), *extract_tags(title, content)]
        prompt_report = self.prompt_scanner.scan(content)
        if prompt_report.is_risky:
            tags.extend(["security-risk", "prompt-injection-risk"])
        tags = list(dict.fromkeys(tags))
        document = Document(
            title=title.strip(),
            content=content,
            source_type=source_type,
            source_uri=source_uri,
            tags=tags,
            summary=summarize(content),
        )
        chunks = self.chunker.chunk(document)
        stored = self.store.add_document(document, chunks)
        if stored.id == document.id:
            self.vector_index.upsert_chunks(document, chunks)
        return stored

    async def ingest_url(self, url: str, tags: list[str] | None = None) -> Document:
        validate_public_http_url(url, self.settings)
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        for node in soup(["script", "style", "noscript"]):
            node.decompose()
        title = soup.title.string.strip() if soup.title and soup.title.string else url
        headings = []
        for heading in soup.find_all(re.compile("^h[1-6]$")):
            level = int(heading.name[1])
            headings.append(f"{'#' * level} {normalize_space(heading.get_text(' '))}")
        body = normalize_space(soup.get_text(" "))
        content = "\n\n".join([*headings[:20], body])
        return self.ingest_text(title, content, "web", url, tags)

    def ingest_upload(self, filename: str, raw: bytes, tags: list[str] | None = None) -> Document:
        validate_upload(filename, raw, self.settings)
        suffix = filename.lower().rsplit(".", 1)[-1] if "." in filename else "txt"
        if suffix == "pdf":
            content = self._extract_pdf(raw)
        else:
            content = raw.decode("utf-8", errors="ignore")
        source_type = "pdf" if suffix == "pdf" else ("markdown" if suffix in {"md", "markdown"} else "file")
        return self.ingest_text(filename, content, source_type, filename, tags)

    def _extract_pdf(self, raw: bytes) -> str:
        try:
            import fitz  # type: ignore
        except ImportError as exc:
            raise RuntimeError("PDF support requires installing the optional 'pdf' extras.") from exc
        doc = fitz.open(stream=raw, filetype="pdf")
        pages = [f"# Page {page.number + 1}\n\n{page.get_text()}" for page in doc]
        return "\n\n".join(pages)
