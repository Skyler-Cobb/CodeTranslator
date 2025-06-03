# helpers/codec/encoder.py

from typing import Any, List, Dict
from itertools import product

from module_loader import get_module_settings, get_module_mapping, is_case_sensitive
from utils import as_list
from .tokenizer import _invert_map, _normalize_map


def encode_message_with_module(
    module: dict[str, Any],
    plaintext: str,
    ignore_case: bool = False
) -> List[str]:
    """
    Encode `plaintext` using `module` settings. Returns all possible
    cipher outputs (accounting for multiple cipher‐tokens per plaintext char).
    Supports chained modules recursively.
    """
    sets = get_module_settings(module)

    # 1) If it’s a “chain” module, encode step by step
    if "chain" in module:
        results: List[str] = [plaintext]
        for step in module["chain"]:
            next_results: List[str] = []
            for txt in results:
                next_results.extend(
                    encode_message_with_module(step, txt, ignore_case)
                )
            results = next_results
        return results

    # 2) Build inverted mapping (plaintext→[cipher tokens])
    raw_map = get_module_mapping(module)
    if sets.get("reverse_direction", False):
        inv_map: Dict[str, List[str]] = _normalize_map(raw_map)  # values are already lists
    else:
        inv_map = _invert_map(raw_map)  # may produce List[Any], so clean next

    # 2a) ➤ Clean up inv_map: ensure each value list contains only str
    clean_inv: Dict[str, List[str]] = {}
    for key, val_list in inv_map.items():
        # keep only actual str entries
        filtered = [tok for tok in val_list if isinstance(tok, str)]
        if filtered:
            clean_inv[key] = filtered
    inv_map = clean_inv  # now inv_map[str] → List[str]

    # 3) Handle case sensitivity
    case_sensitive = is_case_sensitive(module)
    if not case_sensitive:
        upper_inv: Dict[str, List[str]] = {}
        for k, vlist in inv_map.items():
            upper_inv[k.upper()] = vlist.copy()
        inv_map = upper_inv
        plaintext = plaintext.upper()

    # 4) Determine separators
    raw_char_seps = as_list(sets.get("character_separator", None))
    char_sep = raw_char_seps[0] if isinstance(raw_char_seps, list) else None
    if char_sep is None:
        char_sep = ""

    # Fetch word_separator; ensure it's always a str
    raw_word_seps = as_list(sets.get("word_separator", " "))
    if isinstance(raw_word_seps, list) and raw_word_seps:
        sep0 = raw_word_seps[0]
    else:
        sep0 = raw_word_seps if isinstance(raw_word_seps, str) else None

    # If sep0 is not a non-empty string, default to a single space
    word_sep: str = sep0 if isinstance(sep0, str) and sep0 != "" else " "

    # 5) Build choices for each character
    choices_per_char: List[List[str]] = []
    for ch in plaintext:
        if ch.isspace():
            # If whitespace in plaintext, map to word_sep (always a str)
            choices_per_char.append([word_sep])
        else:
            if ch in inv_map:
                # inv_map[ch] is List[str]
                choices_per_char.append(inv_map[ch])
            else:
                if ignore_case:
                    alt = ch.lower() if case_sensitive else ch.upper()
                    if alt in inv_map:
                        choices_per_char.append(inv_map[alt])
                        continue
                # Cannot encode this character
                return []

    # 6) Cartesian product → produce full cipher strings
    encoded_results: List[str] = []
    for tup in product(*choices_per_char):
        s = ""
        for i, token in enumerate(tup):
            if i > 0:
                # If either this token or the previous is a word separator, skip char_sep
                if token == word_sep or tup[i - 1] == word_sep:
                    s += token
                else:
                    s += char_sep + token
            else:
                s += token
        encoded_results.append(s)

    return encoded_results
