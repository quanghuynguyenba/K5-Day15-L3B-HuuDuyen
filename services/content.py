"""Shared readiness checks for narration sources, not a substitute for human review."""
from urllib.parse import urlparse


def is_placeholder(text):
    if not isinstance(text, str) or not text.strip():
        return True
    lowered = text.casefold()
    return any(marker in lowered for marker in ("mẫu —", "sample —", "todo", "replace with", "thay bằng"))


def has_source(value):
    try:
        url = urlparse(value)
        return url.scheme in ("http", "https") and bool(url.netloc)
    except (ValueError, TypeError):
        return False
