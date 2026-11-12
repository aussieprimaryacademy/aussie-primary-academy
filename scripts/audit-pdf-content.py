#!/usr/bin/env python3
"""Read-only inventory and text/answer-structure audit for APA PDFs.

Extracts text page by page, checks file integrity and basic answer-section
structure, and emits full extracted text for human review. It does not claim
to prove semantic correctness of an answer key.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import shutil
from collections import Counter
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parent.parent
PDF_ROOTS = [ROOT / "worksheets", ROOT / "pages", ROOT / "free"]
OUTPUT_JSON = Path("pdf-content-audit.json")
OUTPUT_CSV = Path("pdf-content-audit.csv")
OUTPUT_TEXT = Path("pdf-text-extracts.jsonl")

ANSWER_HEADING = re.compile(
    r"(?im)^[ \t]*(?:answer\s+key|answers?|suggested\s+answers?|sample\s+answers?|"
    r"solutions?|teacher(?:'s)?\s+answers?)\b[^\n]*$"
)
NUMBERED_ITEM = re.compile(r"(?im)^\s*(?:q(?:uestion)?\s*)?(\d{1,2})[.)]\s+\S")
ANSWER_ITEM = re.compile(r"(?im)^\s*(?:q(?:uestion)?\s*)?(\d{1,2})[.)]\s+\S")
REVIEW_DIR = Path("pdf-review-pages")
SOURCE_REVIEW_DIR = Path("pdf-review-originals")
ANSWER_FILENAME = re.compile(r"(?:with[-_ ]answers?|answer[-_ ]key|solutions?[-_ ]guide)", re.I)
STANDALONE_ANSWER_FILE = re.compile(r"(?:answer[-_ ]guide|standalone[-_ ]answers?|solutions?[-_ ]guide)", re.I)


def normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def collect_pdfs():
    files = []
    for root in PDF_ROOTS:
        if root.exists():
            files.extend(p for p in root.rglob("*.pdf") if p.is_file())
    return sorted(set(files))


def audit_pdf(path: Path):
    rel = path.relative_to(ROOT).as_posix()
    size = path.stat().st_size
    row = {
        "path": rel,
        "size_bytes": size,
        "page_count": 0,
        "metadata_title": "",
        "total_text_chars": 0,
        "page_text_chars": "",
        "blank_text_pages": "",
        "answer_heading_pages": "",
        "numbered_question_items": 0,
        "numbered_answer_items": 0,
        "answer_section_detected": False,
        "answer_filename_signal": bool(ANSWER_FILENAME.search(path.name)),
        "standalone_answer_guide_filename": bool(STANDALONE_ANSWER_FILE.search(path.name)),
        "status": "OK",
        "flags": [],
    }
    extracted_pages = []

    if size == 0:
        row["status"] = "EMPTY_FILE"
        row["flags"].append("EMPTY_FILE")
        return row, extracted_pages

    try:
        doc = fitz.open(path)
        if doc.is_encrypted:
            row["status"] = "ENCRYPTED"
            row["flags"].append("ENCRYPTED")
            doc.close()
            return row, extracted_pages
        row["page_count"] = len(doc)
        row["metadata_title"] = (doc.metadata or {}).get("title", "") or ""
        if not len(doc):
            row["status"] = "ZERO_PAGES"
            row["flags"].append("ZERO_PAGES")
            doc.close()
            return row, extracted_pages

        texts = []
        blank_pages = []
        answer_pages = []
        question_numbers = set()
        answer_numbers = set()

        for index, page in enumerate(doc):
            text = page.get_text("text") or ""
            clean = normalise(text)
            texts.append(clean)
            extracted_pages.append({"page": index + 1, "text": text})

            if len(clean) < 20:
                blank_pages.append(index + 1)

            is_answer_page = bool(ANSWER_HEADING.search(text))
            if is_answer_page:
                answer_pages.append(index + 1)

            # Keep low-text pages and detected answer pages as visual evidence.
            # This supports review of image-only pages and answer layouts.
            if len(clean) < 20 or is_answer_page:
                REVIEW_DIR.mkdir(parents=True, exist_ok=True)
                safe_name = re.sub(r"[^A-Za-z0-9._-]+", "__", rel)
                pixmap = page.get_pixmap(matrix=fitz.Matrix(0.7, 0.7), alpha=False)
                pixmap.save(REVIEW_DIR / f"{safe_name}-page-{index + 1}.png")

            # Count simple numbered prompts on non-answer pages.
            if not ANSWER_HEADING.search(text):
                question_numbers.update(int(m.group(1)) for m in NUMBERED_ITEM.finditer(text))
            else:
                answer_numbers.update(int(m.group(1)) for m in ANSWER_ITEM.finditer(text))

        doc.close()
        row["total_text_chars"] = sum(len(t) for t in texts)
        row["page_text_chars"] = ";".join(str(len(t)) for t in texts)
        row["blank_text_pages"] = ";".join(map(str, blank_pages))
        row["answer_heading_pages"] = ";".join(map(str, answer_pages))
        row["answer_section_detected"] = bool(answer_pages)
        row["numbered_question_items"] = len(question_numbers)
        row["numbered_answer_items"] = len(answer_numbers)

        if row["total_text_chars"] == 0:
            row["flags"].append("NO_EXTRACTABLE_TEXT_REVIEW_VISUALLY")
        if blank_pages:
            row["flags"].append("LOW_OR_NO_TEXT_ON_PAGES_REVIEW_VISUALLY")
        if row["answer_filename_signal"] and not answer_pages:
            row["flags"].append("ANSWER_FILENAME_BUT_NO_TEXT_ANSWER_HEADING")
        # Numbering counts are retained as review hints only. They are not used
        # as an automatic mismatch flag because worksheet formats vary widely.
        if row["standalone_answer_guide_filename"]:
            row["flags"].append("STANDALONE_ANSWER_GUIDE_FILE_REVIEW")

        return row, extracted_pages

    except Exception as exc:
        row["status"] = "PARSE_ERROR"
        row["flags"].append(f"PARSE_ERROR: {type(exc).__name__}: {exc}")
        return row, extracted_pages


def main():
    pdfs = collect_pdfs()
    rows = []
    counts = Counter()
    with OUTPUT_TEXT.open("w", encoding="utf-8") as text_file:
        for path in pdfs:
            row, pages = audit_pdf(path)
            rows.append(row)
            counts[row["status"]] += 1
            text_file.write(json.dumps({"path": row["path"], "pages": pages}, ensure_ascii=False) + "\n")

    # Include source PDFs that need manual answer review, without copying the
    # entire library into the artifact.
    SOURCE_REVIEW_DIR.mkdir(parents=True, exist_ok=True)
    source_review_count = 0
    for row in rows:
        needs_visual_review = "NO_EXTRACTABLE_TEXT_REVIEW_VISUALLY" in row["flags"]
        if row["answer_filename_signal"] or needs_visual_review:
            source = ROOT / row["path"]
            destination = SOURCE_REVIEW_DIR / re.sub(r"[^A-Za-z0-9._-]+", "__", row["path"])
            shutil.copy2(source, destination)
            source_review_count += 1

    fields = [
        "path", "size_bytes", "page_count", "metadata_title", "total_text_chars",
        "page_text_chars", "blank_text_pages", "answer_heading_pages",
        "numbered_question_items", "numbered_answer_items", "answer_section_detected",
        "answer_filename_signal", "standalone_answer_guide_filename", "status", "flags",
    ]
    with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            out = dict(row)
            out["flags"] = "; ".join(row["flags"])
            writer.writerow(out)

    flagged = [row for row in rows if row["flags"]]
    summary = {
        "pdf_files_checked": len(rows),
        "status_counts": dict(counts),
        "flagged_files": len(flagged),
        "parse_errors": sum(row["status"] == "PARSE_ERROR" for row in rows),
        "empty_files": sum(row["status"] == "EMPTY_FILE" for row in rows),
        "zero_page_files": sum(row["status"] == "ZERO_PAGES" for row in rows),
        "no_extractable_text": sum("NO_EXTRACTABLE_TEXT_REVIEW_VISUALLY" in row["flags"] for row in rows),
        "answer_section_files": sum(row["answer_section_detected"] for row in rows),
        "answer_section_pages": sum(len([x for x in row["answer_heading_pages"].split(";") if x]) for row in rows),
        "answer_filename_without_detected_heading": sum("ANSWER_FILENAME_BUT_NO_TEXT_ANSWER_HEADING" in row["flags"] for row in rows),
        "visual_review_images": len(list(REVIEW_DIR.glob("*.png"))) if REVIEW_DIR.exists() else 0,
        "source_pdfs_for_manual_review": source_review_count,
        "standalone_answer_guide_files": sum(row["standalone_answer_guide_filename"] for row in rows),
        "limitations": [
            "Text extraction does not inspect image-only content; pages with little/no extracted text require visual review.",
            "Answer headings and numbered-item comparisons are heuristics and may produce false positives or miss visual answer keys.",
            "This audit cannot prove that each answer is semantically correct; flagged and representative PDFs need human content review.",
        ],
        "files": rows,
    }
    OUTPUT_JSON.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    lines = [
        "# APA PDF content audit",
        "",
        f"- PDFs checked: **{len(rows):,}**",
        f"- Parse errors: **{summary['parse_errors']:,}**",
        f"- Empty files: **{summary['empty_files']:,}**",
        f"- Zero-page files: **{summary['zero_page_files']:,}**",
        f"- No extractable text (visual review needed): **{summary['no_extractable_text']:,}**",
        f"- PDFs with a detected answer section: **{summary['answer_section_files']:,}**",
        f"- Detected answer-section pages: **{summary['answer_section_pages']:,}**",
        f"- Answer-named PDFs without detected answer heading: **{summary['answer_filename_without_detected_heading']:,}**",
        f"- Visual review page images generated: **{summary['visual_review_images']:,}**",
        f"- Original PDFs included for manual review: **{summary['source_pdfs_for_manual_review']:,}**",
        f"- Standalone answer-guide filename matches: **{summary['standalone_answer_guide_files']:,}**",
        f"- Files with one or more review flags: **{len(flagged):,}**",
        "",
        "## Review flags",
    ]
    for row in flagged:
        lines.append(f"- **{row['path']}** — {'; '.join(row['flags'])}")
    lines += [
        "",
        "Full per-file evidence: pdf-content-audit.csv and pdf-content-audit.json.",
        "Extracted page text for human review: pdf-text-extracts.jsonl.",
        "Rendered answer pages and low-text pages for visual review: pdf-review-pages/.",
        "Selected original PDFs for manual review: pdf-review-originals/.",
        "",
        "This is a structural/content-extraction audit, not proof of semantic answer correctness.",
    ]
    text = "\n".join(lines) + "\n"
    print(text)
    import os
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as handle:
            handle.write(text)

    if summary["parse_errors"] or summary["empty_files"] or summary["zero_page_files"]:
        raise SystemExit("PDF integrity errors found; see the audit artifact.")


if __name__ == "__main__":
    main()
