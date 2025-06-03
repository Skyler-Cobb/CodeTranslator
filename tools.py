# tools.py

import string
import json
import os
from collections import Counter
import re
from typing import List, Tuple

from utils import project_root  # used to find data/keyshifts.json

# ──────────────────────── Load Keyshift Data ────────────────────────
_keyshifts_path = os.path.join(project_root(), "data", "keyshifts.json")
_KEY_ROWS: List[List[str]] = []
try:
    with open(_keyshifts_path, encoding="utf-8") as _kf:
        _data = json.load(_kf)
        # Expecting something like: [ { "name": "keyboard", "rows": [ [..], [..], [..] ] } ]
        for entry in _data:
            if entry.get("name") == "keyboard":
                _KEY_ROWS = entry.get("rows", [])
                break
except FileNotFoundError:
    # If file is missing or can’t open, leave KEY_ROWS empty (no keyshift available)
    _KEY_ROWS = []

# ─────────────────────────────────────────────────────────────────────────────
def project_root() -> str:
    """
    This function is here only if you ever want it in tools.py— 
    but note: utils.project_root() is used instead.
    """
    raise NotImplementedError("project_root() is provided by utils.py")

# ─────────────────────────────────────────────────────────────────────────────
# Caesar Cipher implementation (existing)
LETTERS_LOWERCASE = string.ascii_lowercase
LETTERS_UPPERCASE = string.ascii_uppercase
ALPHABET_SIZE = 26

def caesar_translate(text: str, shift: int) -> str:
    """
    Shift every letter in `text` by `shift`. Wraps from A→Z or a→z.
    Non-letters (spaces, punctuation, digits) are unchanged.
    Example: caesar_translate("ABC", 1) -> "BCD".
    """
    result = []
    for ch in text:
        if ch.isupper():
            idx = LETTERS_UPPERCASE.index(ch)
            result.append(LETTERS_UPPERCASE[(idx + shift) % ALPHABET_SIZE])
        elif ch.islower():
            idx = LETTERS_LOWERCASE.index(ch)
            result.append(LETTERS_LOWERCASE[(idx + shift) % ALPHABET_SIZE])
        else:
            result.append(ch)
    return "".join(result)

def analyze_caesar_candidates(ciphertext: str, top_n: int = 5) -> List[Tuple[int, str, float]]:
    """
    For auto‐analysis, try all 26 shifts and score them by letter frequency + common words.
    Returns a list of (shift, plaintext, score) sorted by descending score, length = top_n.
    """
    candidates: List[Tuple[int, str, float]] = []
    for shift in range(ALPHABET_SIZE):
        plaintext = caesar_translate(ciphertext, shift)
        freq_score = _letter_freq_score(plaintext)
        word_score = _calculate_word_presence_score(plaintext)
        score = (freq_score + word_score) / 2.0
        candidates.append((shift, plaintext, score))
    candidates.sort(key=lambda x: x[2], reverse=True)
    return candidates[:top_n]

def _letter_freq_score(text: str) -> float:
    """
    Crude score comparing letter frequencies in `text` to expected English frequencies.
    Returns a float in [0, 1].
    """
    text = text.lower()
    cnt = Counter(c for c in text if c.isalpha())
    total = sum(cnt.values())
    if total == 0:
        return 0.0
    # English letter frequency ordered by most→least common
    ENGLISH_LETTER_FREQ = 'etaoinsrhdlucmfywgpbvkjxqz'
    score = 0.0
    for i, letter in enumerate(ENGLISH_LETTER_FREQ):
        expected_freq = 1.0 / (i + 1)
        actual_freq = cnt.get(letter, 0) / total
        score += 1.0 - abs(actual_freq - expected_freq)
    return min(1.0, score / ALPHABET_SIZE)

def _calculate_word_presence_score(text: str) -> float:
    """
    Score based on presence of common English words.
    Returns a float in [0, 1].
    """
    COMMON_ENGLISH_WORDS = {
        'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have', 'i',
        'it', 'for', 'not', 'on', 'with', 'he', 'as', 'you', 'do', 'at'
    }
    words = re.findall(r'\b[a-z]{2,}\b', text.lower())
    if not words:
        return 0.0
    matches = sum(1 for w in words if w in COMMON_ENGLISH_WORDS)
    return min(1.0, matches / len(words))

# ─────────────────────────────────────────────────────────────────────────────
def keyshift_translate(text: str, shift: int) -> str:
    """
    Shift each letter according to the keyboard rows defined in keyshifts.json.
    For each letter (A–Z / a–z), find its row, then move its index by `shift` within that row (wrap around).
    Non-alphabetic characters remain unchanged. Case is preserved.
    Example:
      - If shift=1: 'P' → 'Q' (since P is last in the top row, wrap to 'Q').
      - If shift=-1: 'Q' → 'P', etc.
    """
    if not _KEY_ROWS:
        # If no key rows loaded, return text unchanged
        return text

    result = []
    for ch in text:
        if ch.isalpha():
            upper_ch = ch.upper()
            new_char = ch  # fallback = original
            for row in _KEY_ROWS:
                if upper_ch in row:
                    idx = row.index(upper_ch)
                    new_idx = (idx + shift) % len(row)
                    mapped = row[new_idx]
                    # preserve case:
                    new_char = mapped.lower() if ch.islower() else mapped
                    break
            result.append(new_char)
        else:
            result.append(ch)
    return "".join(result)
