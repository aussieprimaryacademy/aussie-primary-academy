#!/usr/bin/env python3
"""One-off, narrowly scoped correction for the Year 6 modal-verbs PDF."""
from pathlib import Path
import pymupdf as fitz

PDF = Path("worksheets/year-6/english/year-6-modal-verbs-worksheet-free-printable-pdf-colour-with-answers.pdf")
OUTPUT_PREVIEW = Path("modal-verbs-page-2-review.png")


def main():
    doc = fitz.open(PDF)
    page = doc[1]
    all_text = page.get_text("text")
    if "might and could = possibility" in all_text:
        print("PDF already contains the corrected answer.")
        doc.close()
        return

    # Locate Q8 by its surrounding paragraph, then replace only the numeral.
    question_block = None
    number_rect = None
    for block in page.get_text("dict")["blocks"]:
        if "lines" not in block:
            continue
        block_text = "".join(
            "".join(span["text"] for span in line["spans"])
            for line in block["lines"]
        )
        if "Q8." in block_text and "3 modal verbs" in block_text:
            question_block = block
            for line in block["lines"]:
                for span in line["spans"]:
                    if span.get("text", "").strip() == "3":
                        number_rect = fitz.Rect(span["bbox"])
                        break
                if number_rect:
                    break
            break
    if not question_block:
        raise RuntimeError("Could not locate the Q8 modal-verbs question.")
    if number_rect:
        page.add_redact_annot(number_rect, fill=(1, 1, 1))
        page.apply_redactions(images=0, graphics=0)
        page.insert_text(
            (number_rect.x0, number_rect.y1 - 1.45),
            "4",
            fontname="helv",
            fontsize=12,
            color=(0, 0, 0),
        )
    else:
        # Fallback for PDFs where the embedded font combines the numeral
        # with adjacent characters into one span.
        question_rect = fitz.Rect(question_block["bbox"])
        page.add_redact_annot(question_rect, fill=(1, 1, 1))
        page.apply_redactions(images=0, graphics=0)
        page.insert_text(
            (question_rect.x0, question_rect.y0 + 10.5),
            "Q8. Identify the 4 modal verbs in the notice and classify each as certainty, possibility or",
            fontname="helv",
            fontsize=12,
            color=(0, 0, 0),
        )
        page.insert_text(
            (question_rect.x0, question_rect.y0 + 25.5),
            "obligation.",
            fontname="helv",
            fontsize=12,
            color=(0, 0, 0),
        )

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

    corrected_answer = "C8: must = obligation; might and could = possibility; will = certainty."
    answer_box = fitz.Rect(answer_block.x0, answer_block.y0 - 0.5, 550, 531.5)
    remaining = page.insert_textbox(
        answer_box, corrected_answer, fontname="helv", fontsize=9.6,
        color=(0, 0, 0), align=0,
    )
    if remaining < 0:
        raise RuntimeError("Corrected answer text does not fit in its existing answer panel.")

    temporary_pdf = PDF.with_name(PDF.stem + ".corrected.pdf")
    doc.save(temporary_pdf, garbage=4, deflate=True)
    doc.close()
    temporary_pdf.replace(PDF)

    check = fitz.open(PDF)
    checked_page = check[1]
    text = checked_page.get_text("text")
    spans = [
        span
        for block in checked_page.get_text("dict")["blocks"]
        for line in block.get("lines", [])
        for span in line.get("spans", [])
    ]
    q8_text = " ".join(checked_page.get_text("text").split())
    assert "Q8. Identify the 4 modal verbs" in q8_text, "Q8 count was not corrected."
    assert "might and could = possibility" in text, "C8 does not include could."
    checked_page.get_pixmap(matrix=fitz.Matrix(1.2, 1.2), alpha=False).save(OUTPUT_PREVIEW)
    check.close()
    print(f"Corrected and validated {PDF} ({PDF.stat().st_size:,} bytes).")


if __name__ == "__main__":
    main()
