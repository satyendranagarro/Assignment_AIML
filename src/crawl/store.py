"""Persist raw crawl / manual dumps with citation sidecars."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RAW = REPO_ROOT / "data" / "raw"
DEFAULT_MANUAL = REPO_ROOT / "data" / "manual"

_SLUG_RE = re.compile(r"[^a-zA-Z0-9]+")


def url_slug(url: str, *, max_len: int = 64) -> str:
    parsed = urlparse(url)
    path = parsed.path.strip("/") or "index"
    slug = _SLUG_RE.sub("-", path).strip("-").lower() or "page"
    return slug[:max_len]


def raw_path_for(
    source_id: str,
    url: str,
    *,
    raw_dir: Path | str = DEFAULT_RAW,
    extension: str = ".html",
) -> Path:
    return Path(raw_dir) / source_id / f"{url_slug(url)}{extension}"


def write_sidecar(path: Path, meta: dict[str, Any]) -> Path:
    meta_path = path.parent / f"{path.name}.meta.json"
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    with meta_path.open("w", encoding="utf-8") as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    return meta_path


def save_raw_document(
    *,
    source_id: str,
    url: str,
    title: str,
    body: str,
    topics: list[str] | None = None,
    extension: str = ".html",
    fetch_mode: str = "crawl",
    status_code: int | None = 200,
    content_type: str | None = None,
    extra: dict[str, Any] | None = None,
    raw_dir: Path | str = DEFAULT_RAW,
) -> Path:
    """Write body + sidecar under data/raw/<source_id>/."""
    out = raw_path_for(source_id, url, raw_dir=raw_dir, extension=extension)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(body, encoding="utf-8")
    meta: dict[str, Any] = {
        "title": title,
        "url": url,
        "topics": list(topics or []),
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "fetch_mode": fetch_mode,
        "status_code": status_code,
        "content_type": content_type,
        "chars": len(body),
    }
    if extra:
        meta["extra"] = dict(extra)
    write_sidecar(out, meta)
    return out


def copy_manual_dumps(
    source_id: str,
    *,
    manual_dir: Path | str = DEFAULT_MANUAL,
    raw_dir: Path | str = DEFAULT_RAW,
    clear_existing: bool = True,
) -> list[Path]:
    """Copy committed manual dumps for a source into data/raw/."""
    src_root = Path(manual_dir) / source_id
    if not src_root.is_dir():
        return []
    dest_root = Path(raw_dir) / source_id
    if clear_existing and dest_root.is_dir():
        for old in dest_root.iterdir():
            if old.is_file():
                old.unlink()
    dest_root.mkdir(parents=True, exist_ok=True)
    copied: list[Path] = []
    for path in sorted(src_root.iterdir()):
        if not path.is_file():
            continue
        if path.name.endswith(".meta.json"):
            continue
        if path.suffix.lower() not in {".html", ".htm", ".md", ".txt", ".markdown"}:
            continue
        dest = dest_root / path.name
        dest.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
        meta_src = path.parent / f"{path.name}.meta.json"
        if meta_src.is_file():
            meta_dest = dest_root / f"{path.name}.meta.json"
            meta_dest.write_text(meta_src.read_text(encoding="utf-8"), encoding="utf-8")
        copied.append(dest)
    return copied


def list_manual_sources(manual_dir: Path | str = DEFAULT_MANUAL) -> list[str]:
    root = Path(manual_dir)
    if not root.is_dir():
        return []
    return sorted(p.name for p in root.iterdir() if p.is_dir())
