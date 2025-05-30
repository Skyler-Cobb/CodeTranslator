"""
All pure‑algorithm work: (multi‑step) encode, decode, tokenise.
Nothing here touches Tkinter or the filesystem.
"""

from itertools import product
from utils import as_list
from module_loader import (
    get_module_settings,
    get_module_mapping,
    is_case_sensitive,
)

__all__ = [
    "decode_message_with_module",
    "encode_message_with_module",
    "multi_step_decode",
    "multi_step_encode",
    "multi_step_tokenize",
    "tokenize_message_with_module",
]

# ---------------------------------------------------------------------
#  Small helpers
# ---------------------------------------------------------------------

def expand_in_mapping(token: str, mapping: dict, flawed: bool = False) -> list:
    """
    Given a token and a mapping dict, return all the mapped values as a list.
    If token is not in mapping:
      - return [token] if flawed=True
      - return []        if flawed=False
    """
    if token in mapping:
        val = mapping[token]
        return val if isinstance(val, list) else [val]
    return [token] if flawed else []


def decode_recursive(word, mapping, flawed=False):
    """Backtracking decode when no separators / fixed width exist."""
    memo = {}

    def dfs(rem):
        if rem == "":
            return [""]
        if rem in memo:
            return memo[rem]

        results = []
        matched = False
        for key in mapping:
            if rem.startswith(key):
                for head in expand_in_mapping(key, mapping, False):
                    for tail in dfs(rem[len(key) :]):
                        results.append(head + tail)
                matched = True
        if not matched and flawed:
            for tail in dfs(rem[1:]):
                results.append(rem[0] + tail)

        memo[rem] = results
        return results

    return dfs(word)


def build_inverse_mapping(mapping: dict) -> dict:
    """Value‑>list[key] inverse."""
    inv = {}
    for k, v in mapping.items():
        if isinstance(v, list):
            for ch in v:
                inv.setdefault(ch, []).append(k)
        else:
            inv.setdefault(v, []).append(k)
    return inv


# ---------------------------------------------------------------------
#  Core decode / encode
# ---------------------------------------------------------------------

def decode_message_with_module(module_data, message, flawed=False):
    settings = get_module_settings(module_data)
    mapping  = get_module_mapping(module_data)
    rev      = settings.get("reverse_direction", False)

    # input->output mapping depends on *reverse_direction*
    mapping  = build_inverse_mapping(mapping) if rev else mapping
    case     = is_case_sensitive(module_data)
    if not case:
        mapping = {k.upper(): ([x.upper() for x in v] if isinstance(v, list) else v.upper())
                   for k, v in mapping.items()}
        message = message.upper()

    chunk_size = settings.get("chunk_size", [None, None])
    padding    = settings.get("padding",     [None, None])
    if rev:
        in_size, in_pad, out_pad = chunk_size[1], padding[1], padding[0]
    else:
        in_size, in_pad, out_pad = chunk_size[0], padding[0], padding[1]

    results = []
    for ws in as_list(settings.get("word_separator", None)):
        for cs in as_list(settings.get("character_separator", None)):
            try:
                words = message.split(ws) if ws is not None else [message]
                expansions_per_word = []
                valid = True
                for w in words:
                    w = w.strip()
                    if not w:
                        continue

                    # --- choose tokenisation strategy ---
                    if in_size:                         # fixed length chunks
                        tokens = [w[i:i + in_size] for i in range(0, len(w), in_size)]
                    elif cs:                            # explicit separator
                        tokens = [t for t in w.split(cs) if t]
                    else:                              # fall back to recursive
                        tokens = None

                    # --- expand tokens ---
                    if tokens is not None:             # fixed or separated
                        per_tok = []
                        for tok in tokens:
                            if in_pad and all(c == in_pad for c in tok):
                                per_tok.append([out_pad or ""])
                            else:
                                ex = expand_in_mapping(tok, mapping, flawed)
                                if ex is None:
                                    valid = False
                                    break
                                per_tok.append(ex)
                        if not valid:
                            break
                        expansions_per_word.append(["".join(p) for p in product(*per_tok)])
                    else:                              # recursive
                        variants = decode_recursive(w, mapping, flawed)
                        if not variants:
                            valid = False
                            break
                        expansions_per_word.append(variants)

                if valid:
                    for combo in product(*expansions_per_word):
                        results.append(" ".join(combo))
            except Exception:
                continue

    # dedupe while preserving order
    seen, uniq = set(), []
    for r in results:
        if r not in seen:
            uniq.append(r)
            seen.add(r)
    return uniq


def encode_message_with_module(module_data, plaintext):
    settings = get_module_settings(module_data)
    mapping  = get_module_mapping(module_data)
    rev      = settings.get("reverse_direction", False)

    inv_map = mapping if rev else build_inverse_mapping(mapping)
    case    = is_case_sensitive(module_data)
    if not case:
        inv_map   = {k.upper(): ([v.upper() for v in vals] if isinstance(vals, list) else vals.upper())
                     for k, vals in inv_map.items()}
        plaintext = plaintext.upper()

    chunk_size = settings.get("chunk_size", [None, None])
    padding    = settings.get("padding",     [None, None])

    if rev:
        in_size, out_chunk, out_pad = chunk_size[0], chunk_size[0], padding[0]
    else:
        in_size, out_chunk, out_pad = chunk_size[1], chunk_size[1], padding[1]

    sep_candidates = (settings.get("character_separator", []) or [""])
    sep = next((c for c in sep_candidates if c is not None), "")

    ws    = (as_list(settings.get("word_separator", " ")))[0] or " "

    words = plaintext.split(" ")
    enc_per_word = []
    for w in words:
        w = w.strip()
        if not w:
            continue

        # pad + split input
        if in_size:
            rem = len(w) % in_size
            if rem and out_pad:
                w += out_pad * (in_size - rem)
            tokens = [w[i:i + in_size] for i in range(0, len(w), in_size)]
        else:
            tokens = list(w)

        variant_lists = [inv_map.get(tok, [tok]) for tok in tokens]
        encs = []
        for combo in product(*variant_lists):
            s = sep.join(combo)
            if out_chunk and out_pad:
                rem = len(s) % out_chunk
                if rem:
                    s += out_pad * (out_chunk - rem)
            encs.append(s)
        enc_per_word.append(encs)

    final = [" ".join(combo) for combo in product(*enc_per_word)]
    return list(dict.fromkeys(final))  # preserve order, drop dupes


# ---------------------------------------------------------------------
#  Tokenisation helpers
# ---------------------------------------------------------------------

def base_tokenize_message_with_module(module_data, message, flawed=False):
    settings = get_module_settings(module_data)
    mapping  = get_module_mapping(module_data)

    chunk_size = settings.get("chunk_size", [None, None])
    padding    = settings.get("padding",     [None, None])
    rev        = settings.get("reverse_direction", False)

    if rev:
        in_size, in_pad, out_pad = chunk_size[1], padding[1], padding[0]
    else:
        in_size, in_pad, out_pad = chunk_size[0], padding[0], padding[1]

    configs = []
    for ws in as_list(settings.get("word_separator", None)):
        for cs in as_list(settings.get("character_separator", None)):
            try:
                tokenised = []
                for raw in (message.split(ws) if ws is not None else [message]):
                    raw = raw.strip()
                    if not raw:
                        continue

                    # decide how to chop into tokens
                    if in_size:
                        toks = [raw[i:i + in_size] for i in range(0, len(raw), in_size)]
                        toks = [
                            out_pad if in_pad and all(c == in_pad for c in t) else t
                            for t in toks
                        ]
                    elif cs:
                        toks = [t for t in raw.split(cs) if t]
                    else:
                        toks = [raw]

                    # validation if *flawed* not allowed
                    if not flawed and any(expand_in_mapping(t, mapping, False) is None for t in toks):
                        raise ValueError
                    tokenised.append(toks)

                configs.append(tokenised)
            except ValueError:
                continue
    return configs


def tokenize_message_with_module(module_data, message, flawed=False):
    if "chain" not in module_data:
        return base_tokenize_message_with_module(module_data, message, flawed)

    steps, intermediate = module_data["chain"], [message]
    for step in steps:
        settings = get_module_settings(step)
        ws, cs   = settings.get("word_separator", " "), settings.get("character_separator", None)

        new_intermediate = []
        for txt in intermediate:
            for cfg in base_tokenize_message_with_module(step, txt, flawed):
                words_joined = [ (cs.join(t) if cs else "".join(t)) for t in cfg ]
                new_intermediate.append(ws.join(words_joined))

        intermediate = new_intermediate or []
    return intermediate


# ---------------------------------------------------------------------
#  Multi‑step wrappers
# ---------------------------------------------------------------------

def multi_step_decode(module_data, text, flawed=False):
    if "chain" not in module_data:
        return decode_message_with_module(module_data, text, flawed)
    interm = [text]
    for step in module_data["chain"]:
        interm = sum((decode_message_with_module(step, t, flawed) for t in interm), [])
        if not interm:
            break
    return interm


def multi_step_encode(module_data, text):
    if "chain" not in module_data:
        return encode_message_with_module(module_data, text)
    interm = [text]
    for step in reversed(module_data["chain"]):
        interm = sum((encode_message_with_module(step, t) for t in interm), [])
        if not interm:
            break
    return interm


def multi_step_tokenize(module_data, text, flawed=False):
    if "chain" not in module_data:
        cfgs = base_tokenize_message_with_module(module_data, text, flawed)
        return [" ".join("".join(t) for t in cfg) for cfg in cfgs]

    steps, interm = module_data["chain"], [text]
    for step in steps:
        settings = get_module_settings(step)
        ws, cs   = settings.get("word_separator", " "), settings.get("character_separator", None)

        interm2 = []
        for t in interm:
            for cfg in base_tokenize_message_with_module(step, t, flawed):
                words_joined = [ (cs.join(tok) if cs else "".join(tok)) for tok in cfg ]
                interm2.append(ws.join(words_joined))
        interm = interm2 or []
    return interm
