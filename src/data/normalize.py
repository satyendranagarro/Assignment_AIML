"""Normalize raw crawl dumps into citation-preserving processed documents."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup

from src.data.models import NormalizedDocument, Source

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RAW = REPO_ROOT / "data" / "raw"
DEFAULT_PROCESSED = REPO_ROOT / "data" / "processed"

_WS_RE = re.compile(r"[ \t]+")
_BLANK_RE = re.compile(r"\n{3,}")


def _slug(text: str, *, max_len: int = 48) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")
    return (cleaned or "doc")[:max_len]


def make_doc_id(source_id: str, url: str, title: str) -> str:
    digest = hashlib.sha1(f"{source_id}|{url}|{title}".encode()).hexdigest()[:10]
    return f"{source_id}__{_slug(title)}__{digest}"


def html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript", "svg", "iframe"]):
        tag.decompose()
    text = soup.get_text("\n")
    return clean_text(text)


def clean_text(text: str) -> str:
    lines = [_WS_RE.sub(" ", line).strip() for line in text.splitlines()]
    joined = "\n".join(line for line in lines if line)
    return _BLANK_RE.sub("\n\n", joined).strip()


def normalize_raw_payload(
    *,
    source: Source,
    text: str | None = None,
    html: str | None = None,
    title: str | None = None,
    url: str | None = None,
    topics: list[str] | None = None,
    extra: dict[str, Any] | None = None,
) -> NormalizedDocument:
    if text is None and html is None:
        raise ValueError("Provide text or html to normalize")
    body = clean_text(text) if text is not None else html_to_text(html or "")
    if not body:
        raise ValueError("Normalized body is empty")
    doc_title = (title or source.citation.title).strip()
    doc_url = (url or source.citation.url).strip()
    return NormalizedDocument(
        doc_id=make_doc_id(source.id, doc_url, doc_title),
        source_id=source.id,
        title=doc_title,
        url=doc_url,
        text=body,
        topics=list(topics if topics is not None else source.topics),
        extra=dict(extra or {}),
    )


def write_normalized_document(
    doc: NormalizedDocument, processed_dir: Path | str = DEFAULT_PROCESSED
) -> Path:
    out_root = Path(processed_dir) / doc.source_id
    out_root.mkdir(parents=True, exist_ok=True)
    out_path = out_root / f"{doc.doc_id}.json"
    with out_path.open("w", encoding="utf-8") as fh:
        json.dump(doc.to_dict(), fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    return out_path


def load_sidecar_meta(path: Path) -> dict[str, Any]:
    meta_path = path.with_suffix(path.suffix + ".meta.json")
    if not meta_path.is_file():
        # also accept sibling .meta.json for .html/.md/.txt
        alt = path.parent / f"{path.name}.meta.json"
        meta_path = alt if alt.is_file() else meta_path
    if not meta_path.is_file():
        return {}
    with meta_path.open(encoding="utf-8") as fh:
        data = json.load(fh)
    return data if isinstance(data, dict) else {}


def normalize_raw_file(
    path: Path,
    source: Source,
    *,
    processed_dir: Path | str = DEFAULT_PROCESSED,
) -> NormalizedDocument:
    raw = path.read_text(encoding="utf-8", errors="replace")
    meta = load_sidecar_meta(path)
    title = str(meta.get("title") or source.citation.title)
    url = str(meta.get("url") or source.citation.url)
    topics = meta.get("topics")
    suffix = path.suffix.lower()
    if suffix in {".html", ".htm"}:
        doc = normalize_raw_payload(
            source=source, html=raw, title=title, url=url, topics=topics, extra={"raw_path": str(path)}
        )
    else:
        doc = normalize_raw_payload(
            source=source, text=raw, title=title, url=url, topics=topics, extra={"raw_path": str(path)}
        )
    write_normalized_document(doc, processed_dir=processed_dir)
    return doc


def iter_raw_files(raw_dir: Path | str = DEFAULT_RAW) -> list[Path]:
    root = Path(raw_dir)
    if not root.is_dir():
        return []
    files: list[Path] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if path.name.endswith(".meta.json"):
            continue
        if path.name == ".gitkeep":
            continue
        if path.suffix.lower() in {".html", ".htm", ".md", ".txt", ".markdown"}:
            files.append(path)
    return files


def normalize_all_raw(
    sources: list[Source],
    *,
    raw_dir: Path | str = DEFAULT_RAW,
    processed_dir: Path | str = DEFAULT_PROCESSED,
) -> list[NormalizedDocument]:
    by_id = {s.id: s for s in sources}
    docs: list[NormalizedDocument] = []
    for path in iter_raw_files(raw_dir):
        # Expect data/raw/<source_id>/...
        try:
            rel = path.relative_to(Path(raw_dir))
            source_id = rel.parts[0] if rel.parts else ""
        except ValueError:
            source_id = ""
        source = by_id.get(source_id)
        if source is None:
            continue
        docs.append(normalize_raw_file(path, source, processed_dir=processed_dir))
    return docs
