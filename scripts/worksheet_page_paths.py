"""Collision-safe mapping between worksheet PDFs and their landing pages."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from urllib.parse import urlparse


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


def _canonical_page(page: Path, root: Path) -> Path | None:
    if not page.is_file():
        return None
    text = page.read_text(encoding="utf-8", errors="ignore")
    tag = re.search(r'<link\\b(?=[^>]*\\brel=["\\']canonical["\\'])[^>]*>', text, re.IGNORECASE)
    if not tag:
        return None
    href = re.search(r'\\bhref=["\\']([^"\\']+)["\\']', tag.group(0), re.IGNORECASE)
    if not href:
        return None
    parsed = urlparse(href.group(1))
    if parsed.netloc and parsed.netloc.lower() != "aussieprimaryacademy.github.io":
        return None
    path = parsed.path
    marker = "/aussie-primary-academy/"
    if marker in path:
        relative = path.split(marker, 1)[1]
    elif path.startswith("/"):
        relative = path.lstrip("/")
    else:
        try:
            relative = (page.parent / path).resolve().relative_to(Path(root).resolve()).as_posix()
        except ValueError:
            return None
    candidate = (Path(root).resolve() / relative).resolve()
    return candidate if candidate.is_file() else None


def page_is_indexable(page: Path, root: Path) -> bool:
    page = Path(page)
    if not page.is_file():
        return False
    text = page.read_text(encoding="utf-8", errors="ignore")
    robots = re.search(
        r'<meta\\b(?=[^>]*\\bname=["\\']robots["\\'])[^>]*\\bcontent=["\\']([^"\\']+)["\\']',
        text,
        re.IGNORECASE,
    )
    if robots and "noindex" in robots.group(1).lower():
        return False
    canonical = _canonical_page(page, Path(root).resolve())
    return canonical is None or canonical.resolve() == page.resolve()


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

    if base_page.exists():
        canonical = _canonical_page(base_page, root)
        if canonical and page_matches_pdf(canonical, pdf, root) and page_is_indexable(canonical, root):
            return canonical
        if page_matches_pdf(base_page, pdf, root) and page_is_indexable(base_page, root):
            return base_page

    unique_page = _unique_page(pdf, root, worksheets_root, pages_root)
    if unique_page.exists():
        canonical = _canonical_page(unique_page, root)
        if canonical and page_matches_pdf(canonical, pdf, root) and page_is_indexable(canonical, root):
            return canonical
        if page_matches_pdf(unique_page, pdf, root) and page_is_indexable(unique_page, root):
            return unique_page
    if base_page.exists():
        return unique_page
    return base_page
