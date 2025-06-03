# helpers/codec/tokenizer.py

from typing import Any, List, Dict
from module_loader import get_module_settings, get_module_mapping, is_case_sensitive
from utils import as_list

# Cap on how many partial paths to generate before pruning
_MAX_PATHS = 10000


def _invert_map(orig: Dict[str, Any]) -> Dict[str, List[str]]:
    """
    Invert a forward mapping (cipher→plaintext or plaintext→cipher) so that each
    value (or each element of a list value) maps back to its key.
    """
    inv: Dict[str, List[str]] = {}
    for k, v in orig.items():
        targets = v if isinstance(v, list) else [v]
        for tgt in targets:
            inv.setdefault(tgt, []).append(k)
    return inv


def _normalize_map(orig: Dict[str, Any]) -> Dict[str, List[str]]:
    """
    Ensure each mapping value is a list of plaintext strings.
    """
    m: Dict[str, List[str]] = {}
    for k, v in orig.items():
        if isinstance(v, list):
            m[k] = v.copy()
        else:
            m[k] = [v]
    return m


def _recursive_decode(
    word: str,
    mapping: Dict[str, List[str]],
    flawed: bool,
    memo: Dict[str, List[str]] | None = None
) -> List[str]:
    """
    Recursively split `word` into tokens that match mapping keys, then
    produce all possible plaintext strings for that word. If flawed=True,
    allow single-character fallback when no key matches.
    Early exit if more than _MAX_PATHS results accumulate.
    """
    if memo is None:
        memo = {}

    if word == "":
        return [""]

    if word in memo:
        return memo[word]

    results: List[str] = []
    matched = False

    # Try every mapping key that matches the start of `word`
    for tok in mapping.keys():
        if word.startswith(tok):
            matched = True
            suffix = word[len(tok):]
            for plaintext_fragment in mapping[tok]:
                for tail in _recursive_decode(suffix, mapping, flawed, memo):
                    results.append(plaintext_fragment + tail)
                    if len(results) > _MAX_PATHS:
                        memo[word] = results
                        return results

    # If nothing matched and flawed=True, drop first character literally
    if not matched and flawed:
        first_char = word[0]
        suffix = word[1:]
        for tail in _recursive_decode(suffix, mapping, flawed, memo):
            results.append(first_char + tail)
            if len(results) > _MAX_PATHS:
                memo[word] = results
                return results

    memo[word] = results
    return results


def tokenize_message_with_module(module: dict[str, Any], cipher: str) -> List[dict]:
    """
    For a given `module` definition and raw `cipher` string, produce a list
    of tokenization configurations. Each config is:
        {
          "cfg": List[List[str]],      # lists of tokens for each word
          "char_sep_blank": bool       # True if character_separator was null/blank
        }
    Mirrors the logic in Decoder.jsx for splitting on word_separator and/or character_separator.
    """
    sets = get_module_settings(module)

    # 1) Collect raw separators from JSON
    raw_char_seps = as_list(sets.get("character_separator", None))
    char_seps: List[str] = [rc if isinstance(rc, str) else "" for rc in raw_char_seps]

    raw_word_seps = as_list(sets.get("word_separator", " "))
    word_seps: List[str] = [rw if isinstance(rw, str) else "" for rw in raw_word_seps]

    # 2) chunk_size (only applies when char_sep is blank)
    chunk_size = None
    csizes = sets.get("chunk_size", [None, None])
    if isinstance(csizes, list) and csizes[0]:
        chunk_size = csizes[0]

    # 3) Build forward mapping from cipher→plaintext, possibly inverted first
    raw_map = get_module_mapping(module)
    if sets.get("reverse_direction", False):
        raw_map = _invert_map(raw_map)

    # Handle case‐sensitivity: if not case-sensitive, uppercase everything
    case_sensitive = is_case_sensitive(module)
    if not case_sensitive:
        up_map: Dict[str, List[str]] = {}
        for k, v in raw_map.items():
            k_up = k.upper()
            if isinstance(v, list):
                up_map[k_up] = [vv.upper() for vv in v]
            else:
                up_map[k_up] = [v.upper()]
        raw_map = up_map

    # Normalize so that each mapping key→list of plaintext values
    mapping = _normalize_map(raw_map)

    # 4) Normalize the cipher text: collapse newlines→spaces; uppercase if needed
    text = cipher.replace("\r\n", " ").replace("\n", " ")
    if not case_sensitive:
        text = text.upper()

    configs: List[dict] = []

    for ws in word_seps:
        sep = ws or ""
        if sep:
            words = text.split(sep)
        else:
            words = [text]

        for cs in char_seps:
            char_sep_blank = (cs == "")
            cfg: List[List[str]] = []
            ok = True

            for raw_word in words:
                word = raw_word.strip()
                if word == "":
                    # skip empty segments
                    continue

                if cs:
                    toks = [t for t in word.split(cs) if t]
                elif chunk_size:
                    toks = [word[i : i + chunk_size] for i in range(0, len(word), chunk_size)]
                else:
                    toks = [word]

                if not toks:
                    ok = False
                    break

                cfg.append(toks)

            if ok:
                configs.append({"cfg": cfg, "char_sep_blank": char_sep_blank})

    return configs


def get_recursive_decode(
    word: str,
    module: dict[str, Any],
    flawed: bool
) -> List[str]:
    """
    Exposed helper: build a normalized mapping, then call _recursive_decode 
    on the entire `word`. Used by decoder logic.
    """
    sets = get_module_settings(module)
    raw_map = get_module_mapping(module)

    if sets.get("reverse_direction", False):
        raw_map = _invert_map(raw_map)

    case_sensitive = is_case_sensitive(module)
    if not case_sensitive:
        up_map: Dict[str, List[str]] = {}
        for k, v in raw_map.items():
            k_up = k.upper()
            if isinstance(v, list):
                up_map[k_up] = [vv.upper() for vv in v]
            else:
                up_map[k_up] = [v.upper()]
        raw_map = up_map

    mapping = _normalize_map(raw_map)
    return _recursive_decode(word, mapping, flawed, memo=None)
