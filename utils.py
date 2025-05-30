import os

# ---------------------------------------------------------------------
#  Generic helpers
# ---------------------------------------------------------------------

def project_root() -> str:
    """Absolute path of the project root (directory that holds this file)."""
    return os.path.dirname(os.path.abspath(__file__))

def load_dictionary() -> set[str]:
    """Load data/dictionary.txt into a set of words (upper‑ and lowercase)."""
    dict_path = os.path.join(project_root(), "data", "dictionary.txt")
    words: set[str] = set()
    if os.path.exists(dict_path):
        with open(dict_path, encoding="utf‑8") as f:
            words.update(w.strip() for w in f if w.strip())
    return words

def compute_accuracy(text: str, dictionary: set[str]) -> float:
    """% of whitespace‑separated words that are found in *dictionary*."""
    if not text.strip():
        return 0.0
    tokens = text.split()
    valid = sum(1 for t in tokens if t in dictionary)
    return (valid / len(tokens)) * 100.0

def has_vowel(word: str) -> bool:
    """Crude vowel check (AEIOUY, case‑insensitive)."""
    return any(c in "AEIOUYaeiouy" for c in word)

def as_list(x):
    """Ensure *x* is a list, preserving *None*."""
    if x is None:
        return [None]
    return x if isinstance(x, list) else [x]
