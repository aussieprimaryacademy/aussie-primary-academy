"""Collision-safe mapping between worksheet PDFs and their landing pages."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path


def _linked_pdf(page: Path, root: Path) -> Path | None:
    if not page.is_file():
        return None
    text = page.read_text(encoding="utf-8", errors="ignore")
    patterns = (
        r'<a\b(?=[^>]*\bdownload(?:\s|=|>))[^>]*\bhref=["\'](?:\.\./)?(worksheets/[^"\']+)["\']',
        r'href=["\'](?:\.\./)?(worksheets/[^"\']+)["\']',
    )
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            relative = match.group(1).split("#", 1)[0].split("?", 1)[0]
            candidate = (root / relative).resolve()
            if candidate.is_file():
                return candidate
    return None


def same_pdf_content(first: Path, second: Path) -> bool:
    first = Path(first)
    second = Path(second)
    if not first.is_file() or not second.is_file():
        return False
    if first.resolve() == second.resolve():
        return True
    if first.stat().st_size != second.stat().st_size:
        return False
    return hashlib.sha256(first.read_bytes()).digest() == hashlib.sha256(second.read_bytes()).digest()


def page_matches_pdf(page: Path, pdf: Path, root: Path) -> bool:
    linked = _linked_pdf(Path(page), Path(root).resolve())
    return bool(linked and same_pdf_content(linked, Path(pdf)))


def _unique_page(pdf: Path, root: Path, worksheets_root: Path, pages_root: Path) -> Path:
    relative = Path(pdf).resolve().relative_to(Path(worksheets_root).resolve()).with_suffix("").as_posix()
    slug = re.sub(r"[^a-z0-9]+", "-", relative.lower()).strip("-")
    candidate = Path(pages_root) / f"free-printable-{slug}-worksheet.html"
    if candidate.exists() and not page_matches_pdf(candidate, pdf, root):
        digest = hashlib.sha256(Path(pdf).read_bytes()).hexdigest()[:8]
        candidate = Path(pages_root) / f"free-printable-{slug}-{digest}-worksheet.html"
    if candidate.exists() and not page_matches_pdf(candidate, pdf, root):
        raise RuntimeError(f"Unique worksheet page path is already owned by another PDF: {candidate}")
    return candidate


def resolve_page_path(
    pdf: Path,
    base_page: Path,
    root: Path,
    worksheets_root: Path,
    pages_root: Path,
) -> Path:
    """Keep an existing page only when it serves this PDF (or identical PDF bytes).

    If another, different worksheet already owns the legacy title-based URL,
    give this PDF a deterministic path containing its year/subject/file path.
    """
    root = Path(root).resolve()
    pdf = Path(pdf)
    if not pdf.is_absolute():
        pdf = root / pdf
    pdf = pdf.resolve()
    worksheets_root = Path(worksheets_root)
    if not worksheets_root.is_absolute():
        worksheets_root = root / worksheets_root
    pages_root = Path(pages_root)
    if not pages_root.is_absolute():
        pages_root = root / pages_root
    base_page = Path(base_page)
    if not base_page.is_absolute():
        base_page = root / base_page

    if base_page.exists() and page_matches_pdf(base_page, pdf, root):
        return base_page
    unique_page = _unique_page(pdf, root, worksheets_root, pages_root)
    if unique_page.exists() and page_matches_pdf(unique_page, pdf, root):
        return unique_page
    if base_page.exists():
        return unique_page
    return base_page
