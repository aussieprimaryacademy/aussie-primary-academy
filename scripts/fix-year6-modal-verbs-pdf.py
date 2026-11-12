#!/usr/bin/env python3
"""One-off, narrowly scoped correction for the Year 6 modal-verbs PDF."""
from pathlib import Path
import pymupdf as fitz

PDF = Path("worksheets/year-6/english/year-6-modal-verbs-worksheet-free-printable-pdf-colour-with-answers.pdf")
OUTPUT_PREVIEW = Path("modal-verbs-page-2-review.png")
CORRECTED_ANSWER = "C8: must = obligation; might and could = possibility; will = certainty."


def page_spans(page):
    return [
        span
        for block in page.get_text("dict")["blocks"]
        for line in block.get("lines", [])
        for span in line.get("spans", [])
    ]


def main():
    doc = fitz.open(PDF)
    page = doc[1]
    text = page.get_text("text")
    spans = page_spans(page)

    # Idempotent: a second run only creates the preview.
    if any(span.get("text", "").strip() == "4 modal verbs" for span in spans) and CORRECTED_ANSWER in text:
        page.get_pixmap(matrix=fitz.Matrix(1.2, 1.2), alpha=False).save(OUTPUT_PREVIEW)
        doc.close()
        print("PDF already contains both verified corrections.")
        return

    # The worksheet layout is fixed. Replace the full phrase, not just the
    # numeral, so a visible space is retained on both sides of the new text.
    question_phrase = fitz.Rect(116.5, 168.5, 197.0, 183.0)
    page.add_redact_annot(question_phrase, fill=(1, 1, 1))
    page.apply_redactions(images=0, graphics=0)
    page.insert_text(
        (117.0, 180.0),
        "4 modal verbs",
        fontname="helv",
        fontsize=12,
        color=(0, 0, 0),
    )

    # C8: add the fourth modal verb to the existing answer panel.
    current_text = page.get_text("text")
    if CORRECTED_ANSWER not in current_text:
        answer_block = None
        for block in page.get_text("dict")["blocks"]:
            if "lines" not in block:
                continue
            block_text = "".join(
                "".join(span["text"] for span in line["spans"])
                for line in block["lines"]
            )
            if block_text.startswith("C8:"):
                answer_block = fitz.Rect(block["bbox"])
                break
        if not answer_block:
            raise RuntimeError("Could not locate the C8 answer line.")

        pix = page.get_pixmap(matrix=fitz.Matrix(1, 1), alpha=False)
        sample_x = 350
        sample_y = int((answer_block.y0 + answer_block.y1) / 2)
        offset = (sample_y * pix.width + sample_x) * pix.n
        fill = tuple(value / 255 for value in pix.samples[offset:offset + 3])

        redaction = fitz.Rect(
            answer_block.x0 - 1, answer_block.y0 - 1,
            answer_block.x1 + 1, answer_block.y1 + 1,
        )
        page.add_redact_annot(redaction, fill=fill)
        page.apply_redactions(images=0, graphics=0)

        answer_box = fitz.Rect(answer_block.x0, answer_block.y0 - 0.5, 550, 531.5)
        remaining = page.insert_textbox(
            answer_box,
            CORRECTED_ANSWER,
            fontname="helv",
            fontsize=9.6,
            color=(0, 0, 0),
            align=0,
        )
        if remaining < 0:
            raise RuntimeError("Corrected answer text does not fit in its existing answer panel.")

    temporary_pdf = PDF.with_name(PDF.stem + ".corrected.pdf")
    doc.save(temporary_pdf, garbage=4, deflate=True)
    doc.close()
    temporary_pdf.replace(PDF)

    check = fitz.open(PDF)
    checked_page = check[1]
    checked_spans = page_spans(checked_page)
    checked_text = checked_page.get_text("text")
    assert any(span.get("text", "").strip() == "4 modal verbs" for span in checked_spans), "Q8 phrase was not corrected."
    assert CORRECTED_ANSWER in checked_text, "C8 answer does not include could."
    checked_page.get_pixmap(matrix=fitz.Matrix(1.2, 1.2), alpha=False).save(OUTPUT_PREVIEW)
    check.close()
    print(f"Corrected and validated {PDF} ({PDF.stat().st_size:,} bytes).")


if __name__ == "__main__":
    main()
