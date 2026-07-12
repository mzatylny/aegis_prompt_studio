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


def decode_candidates(text: str, limit: int = 12) -> list[str]:
    """Extract plausible decoded payloads without executing or interpreting them."""
    found: list[str] = []

    def add(value: str) -> None:
        value = normalize_text(value).strip()
        if _is_plausible(value) and value not in found:
            found.append(value[:4000])

    for match in BASE64_TOKEN.finditer(text):
        token = match.group(1)
        try:
            padded = token + "=" * (-len(token) % 4)
            add(base64.b64decode(padded, validate=True).decode("utf-8", errors="strict"))
        except (binascii.Error, UnicodeDecodeError, ValueError):
            continue
        if len(found) >= limit:
            return found

    for match in HEX_TOKEN.finditer(text):
        try:
            add(bytes.fromhex(match.group(1)).decode("utf-8", errors="strict"))
        except (ValueError, UnicodeDecodeError):
            continue
        if len(found) >= limit:
            return found

    for match in URL_ENCODED.finditer(text):
        try:
            add(unquote(match.group(0)))
        except ValueError:
            continue
        if len(found) >= limit:
            return found

    # ROT13 is cheap to inspect and catches a common CTF-style evasion pattern.
    if re.search(r"\b(vtaber|flfgrz|cebzcg|vafgehpgvbaf)\b", text, re.I):
        add(codecs.decode(text, "rot_13"))

    return found[:limit]
