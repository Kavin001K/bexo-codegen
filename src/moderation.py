import re

BLOCKED_PATTERNS = [
    r"\b(child\s*porn|cp\b)",
    r"\b(terrorist|bomb\s*making)\b",
    r"<script[^>]*src=[\"']https?://(?!fonts\.googleapis)",
]

MAX_SPEC_CHARS = int(__import__("os").environ.get("MAX_SPEC_CHARS", "50000"))


def moderate_text(text: str, label: str = "content") -> list[str]:
    issues = []
    if len(text) > MAX_SPEC_CHARS:
        issues.append(f"{label} exceeds {MAX_SPEC_CHARS} characters")
    lower = text.lower()
    for pat in BLOCKED_PATTERNS:
        if re.search(pat, lower, re.IGNORECASE):
            issues.append(f"{label} failed safety check")
            break
    return issues
