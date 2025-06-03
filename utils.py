import os

# ─────────────────────────────────────────────────────────────────────────────
def project_root() -> str:
    """
    Absolute path of the project root (directory that holds this file).
    """
    return os.path.dirname(os.path.abspath(__file__))


def load_dictionary() -> set[str]:
    path = os.path.join(project_root(), "data", "dictionary.txt")
    out: set[str] = set()
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            out = {ln.strip().upper() for ln in f if ln.strip()}
    return out



"""
Compute “accuracy” as the fraction of tokens in `text` (split on spaces)
that exist in `dictionary`.  Returned as a percentage [0.0–100.0].
"""
def compute_accuracy(txt: str, dictionary: set[str]) -> float:
    if not (txt := txt.strip()):
        return 0.0
    words = txt.split()
    good  = sum(1 for w in words if w.upper() in dictionary)
    return (good / len(words)) * 100.0


def has_vowel(word: str) -> bool:
    """
    Crude vowel check (AEIOUY, case-insensitive).
    """
    return any(c in "AEIOUYaeiouy" for c in word)


def as_list(x):
    """
    Ensure *x* is a list, preserving *None*.
    """
    if x is None:
        return [None]
    return x if isinstance(x, list) else [x]
