"""Fail deployment when a critical collection page looks overwritten or truncated."""

from pathlib import Path


CHECKS = {
    "year-3.html": {
        "minimum_bytes": 30_000,
        "required_text": (
            "Year 3 Maths Worksheets",
            "Year 3 English Worksheets",
            "Year 3 Science Worksheets",
            'class="wcard"',
            "</html>",
        ),
        "minimum_cards": 30,
    },
}

PLACEHOLDERS = ("SEE_FILE", "PLACEHOLDER_CONTENT", "TODO_RESTORE")


def validate(path_string: str, rules: dict) -> list[str]:
    path = Path(path_string)
    if not path.is_file():
        return [f"{path_string} is missing"]

    content = path.read_text(encoding="utf-8", errors="replace")
    errors: list[str] = []
    if path.stat().st_size < rules["minimum_bytes"]:
        errors.append(
            f"{path_string} is only {path.stat().st_size:,} bytes; possible overwrite"
        )
    for required in rules["required_text"]:
        if required not in content:
            errors.append(f"{path_string} is missing required content: {required}")
    card_count = content.count('class="wcard"')
    if card_count < rules["minimum_cards"]:
        errors.append(
            f"{path_string} has only {card_count} worksheet cards; "
            f"expected at least {rules['minimum_cards']}"
        )
    for placeholder in PLACEHOLDERS:
        if placeholder in content:
            errors.append(f"{path_string} contains placeholder text: {placeholder}")
    return errors


all_errors = [
    error
    for path, rules in CHECKS.items()
    for error in validate(path, rules)
]
if all_errors:
    raise SystemExit("Critical page validation failed:\n- " + "\n- ".join(all_errors))

print("Critical collection pages passed overwrite protection checks.")
