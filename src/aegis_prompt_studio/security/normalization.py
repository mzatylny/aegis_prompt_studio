from __future__ import annotations

import base64
import binascii
import codecs
import html
import re
import unicodedata
from urllib.parse import unquote

ZERO_WIDTH = re.compile(r"[\u200B-\u200D\u2060\uFEFF]")
BASE64_TOKEN = re.compile(r"(?<![A-Za-z0-9+/=])([A-Za-z0-9+/]{24,}={0,2})(?![A-Za-z0-9+/=])")
HEX_TOKEN = re.compile(r"(?<![0-9A-Fa-f])((?:[0-9A-Fa-f]{2}){12,})(?![0-9A-Fa-f])")
URL_ENCODED = re.compile(r"(?:%[0-9A-Fa-f]{2}){4,}")
URL_ESCAPE = re.compile(r"%[0-9A-Fa-f]{2}")


def normalize_text(text: str) -> str:
    """Normalize Unicode and remove invisible control characters used for evasion."""
    text = html.unescape(text)
    text = unicodedata.normalize("NFKC", text)
    text = ZERO_WIDTH.sub("", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text


def _is_plausible(decoded: str) -> bool:
    if len(decoded) < 8:
        return False
    printable = sum(ch.isprintable() or ch in "\n\t" for ch in decoded)
    ratio = printable / max(len(decoded), 1)
    alpha = sum(ch.isalpha() for ch in decoded)
    return ratio > 0.88 and alpha >= 4


def _decode_once(text: str) -> list[str]:
    decoded: list[str] = []

    def append(value: str) -> None:
        value = normalize_text(value).strip()
        if _is_plausible(value) and value not in decoded:
            decoded.append(value[:4000])

    for match in BASE64_TOKEN.finditer(text):
        token = match.group(1)
        try:
            padded = token + "=" * (-len(token) % 4)
            append(base64.b64decode(padded, validate=True).decode("utf-8", errors="strict"))
        except (binascii.Error, UnicodeDecodeError, ValueError):
            continue

    for match in HEX_TOKEN.finditer(text):
        try:
            append(bytes.fromhex(match.group(1)).decode("utf-8", errors="strict"))
        except (ValueError, UnicodeDecodeError):
            continue

    for match in URL_ENCODED.finditer(text):
        append(unquote(match.group(0)))

    # Standard URL encoding often leaves letters unchanged and only encodes spaces
    # and punctuation, so inspect the complete input when it has several escapes.
    if len(URL_ESCAPE.findall(text)) >= 4:
        append(unquote(text))

    if re.search(r"\b(vtaber|flfgrz|cebzcg|vafgehpgvbaf)\b", text, re.I):
        append(codecs.decode(text, "rot_13"))
    return decoded


def decode_candidates(text: str, limit: int = 12, max_depth: int = 3) -> list[str]:
    """Extract bounded, multi-layer decoded payloads without executing them."""
    found: list[str] = []
    seen = {normalize_text(text).strip()[:4000]}
    frontier = list(seen)
    for _ in range(max(1, min(max_depth, 5))):
        next_frontier: list[str] = []
        for value in frontier:
            for candidate in _decode_once(value):
                if candidate in seen:
                    continue
                seen.add(candidate)
                found.append(candidate)
                next_frontier.append(candidate)
                if len(found) >= limit:
                    return found
        if not next_frontier:
            break
        frontier = next_frontier
    return found[:limit]
