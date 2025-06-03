# helpers/codec/decoder.py

from typing import Any, List, Set, Dict, Optional, Callable
from itertools import product

from module_loader import get_module_settings, get_module_mapping
from .tokenizer import (
    tokenize_message_with_module,
    get_recursive_decode,
    _normalize_map,
    _invert_map,
    _MAX_PATHS,
)

# Type alias for our progress callback:
#   stage: "PermutationsPhase"
#   module_index: int (ignored inside _attempt_decode, actual module_index is passed by GUI)
#   total_modules: int
#   percent: float (0.0–100.0)
#   module_name: str
ProgressCallback = Callable[[str, int, int, float, str], None]


def decode_message_with_module(
    module: dict[str, Any],
    message: str,
    flawed: bool = False,
    # min_accuracy is ignored here; GUI does its own filtering
    min_accuracy: float = 0.0,
    progress_callback: Optional[ProgressCallback] = None,
    skip_flag: Optional[Any] = None
) -> List[str]:
    """
    Decode `message` using `module`. First try a perfect decode (flawed=False).
    If any perfect outputs exist, return them all immediately (no filtering).
    Otherwise, if flawed=True, do a flawed pass and return all flawed outputs.
    progress_callback(stage, module_idx, total_modules, percent, module_name) is
    invoked for each permutation. If skip_flag.skip == True at any time, we abort
    this module and return []. (No auto‐abort for pruning.)
    """
    sets = get_module_settings(module)

    # Build forward mapping (cipher→plaintext). Invert if needed.
    raw_map = get_module_mapping(module)
    if sets.get("reverse_direction", False):
        raw_map = _invert_map(raw_map)
    mapping: Dict[str, List[str]] = _normalize_map(raw_map)

    # ---------- Perfect‐decode pass ----------
    perfect_set = _attempt_decode(
        module,
        message,
        mapping,
        flawed=False,
        progress_callback=progress_callback,
        skip_flag=skip_flag,
    )
    # If skip was triggered, _attempt_decode returns empty, but skip_flag.skip is True.
    if skip_flag and getattr(skip_flag, "skip", False):
        return []

    if perfect_set:
        return list(perfect_set)

    # ---------- Flawed‐decode pass (if allowed) ----------
    if flawed:
        flawed_set = _attempt_decode(
            module,
            message,
            mapping,
            flawed=True,
            progress_callback=progress_callback,
            skip_flag=skip_flag,
        )
        return list(flawed_set)

    return []


def _attempt_decode(
    module: dict[str, Any],
    message: str,
    mapping: Dict[str, List[str]],
    flawed: bool,
    progress_callback: Optional[ProgressCallback],
    skip_flag: Optional[Any]
) -> Set[str]:
    """
    Internal helper: iterate through each token‐config for `module` → decode.
    If skip_flag.skip becomes True, abort immediately and return empty set.
    We still prune branches > _MAX_PATHS, but do NOT auto‐abort beyond skip.
    We call progress_callback("PermutationsPhase", module_index, total_modules, percent, module_name)
    for each config. (module_index/total_modules are passed in by the GUI's wrapper.)
    """
    sets = get_module_settings(module)
    configs = tokenize_message_with_module(module, message)

    total_cfgs = len(configs)
    module_name = sets.get("name", "Unknown Module")

    outputs_set: Set[str] = set()

    for cfg_index, conf in enumerate(configs):
        # If user hit “Skip Step,” abort this module’s decoding.
        if skip_flag and getattr(skip_flag, "skip", False):
            return set()

        # Report permutation‐phase progress to GUI (percent done within this module)
        if progress_callback:
            percent = (cfg_index / total_cfgs) * 100.0
            # We pass module_index and total_modules as 0 here; GUI lambda remaps them.
            progress_callback("PermutationsPhase", 0, 0, percent, module_name)

        cfg = conf["cfg"]
        char_sep_blank = conf["char_sep_blank"]

        paths: List[str] = [""]
        pruned = False

        for toks in cfg:
            if skip_flag and getattr(skip_flag, "skip", False):
                return set()

            new_paths: List[str] = []

            if char_sep_blank and len(toks) == 1:
                # Entire word token → recursive decode
                variants = get_recursive_decode(toks[0], module, flawed)
            else:
                lists_of_choices: List[List[str]] = []
                for t in toks:
                    if t in mapping:
                        lists_of_choices.append(mapping[t])
                    else:
                        if flawed:
                            lists_of_choices.append([t])
                        else:
                            lists_of_choices = []
                            break

                if not lists_of_choices:
                    variants = []
                else:
                    variants = lists_of_choices[0].copy()
                    for choices in lists_of_choices[1:]:
                        next_variants: List[str] = []
                        for prefix in variants:
                            for c in choices:
                                next_variants.append(prefix + c)
                                if len(next_variants) > _MAX_PATHS:
                                    break
                            if len(next_variants) > _MAX_PATHS:
                                break
                        variants = next_variants
                        if len(variants) > _MAX_PATHS:
                            break

            if not variants:
                paths = []
                break

            # Prune if combining paths × variants > _MAX_PATHS
            if len(paths) * len(variants) > _MAX_PATHS:
                pruned = True
                break

            for prefix in paths:
                for v in variants:
                    if prefix:
                        new_paths.append(prefix + " " + v)
                    else:
                        new_paths.append(v)

                    if len(new_paths) > _MAX_PATHS:
                        pruned = True
                        break
                if pruned:
                    break

            if pruned:
                paths = []
                break

            paths = new_paths
            if not paths:
                break

        if pruned:
            continue

        for p in paths:
            outputs_set.add(p.strip())

    return outputs_set
