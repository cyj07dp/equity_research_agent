import re


SECTION_PATTERNS = [
    ("risk_factors", re.compile(r"item\s+1a\.?\s+risk\s+factors", re.I)),
    ("business", re.compile(r"item\s+1\.?\s+business", re.I)),
    ("mda", re.compile(r"item\s+7\.?\s+management", re.I)),
]


def split_sec_text(text: str, *, max_chars: int = 1200) -> list[tuple[str, str]]:
    section = "unknown"
    chunks: list[tuple[str, str]] = []
    current = ""
    for paragraph in [line.strip() for line in text.splitlines() if line.strip()]:
        is_section_heading = False
        for name, pattern in SECTION_PATTERNS:
            if pattern.search(paragraph):
                section = name
                is_section_heading = True
        if len(paragraph) < 60 and not is_section_heading:
            continue
        if len(current) + len(paragraph) + 1 > max_chars and current:
            chunks.append((section, current))
            current = paragraph
        else:
            current = f"{current}\n{paragraph}".strip()
    if current:
        chunks.append((section, current))
    return chunks
