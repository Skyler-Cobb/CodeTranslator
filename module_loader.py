import os
import json
from utils import project_root

# ---------------------------------------------------------------------
#  Loading & basic inspection of module JSON files
# ---------------------------------------------------------------------

def load_modules() -> dict[str, dict]:
    """Read every *.json* inside *modules/* and return a {name: data} dict."""
    modules: dict[str, dict] = {}
    mod_dir = os.path.join(project_root(), "modules")
    if not os.path.isdir(mod_dir):
        return modules

    for fname in os.listdir(mod_dir):
        if not fname.endswith(".json"):
            continue
        try:
            with open(os.path.join(mod_dir, fname), encoding="utf‑8") as f:
                modules[fname[:-5]] = json.load(f)
        except Exception as exc:
            print(f"[modules] failed to load {fname}: {exc}")
    return modules


def get_module_mapping(data: dict) -> dict:
    """Return the *encoding* (or *morse*) map, stripping empty keys."""
    mapping = data.get("encoding") or data.get("morse") or {}
    return {k: v for k, v in mapping.items() if k != ""}


def get_module_settings(data: dict) -> dict:
    """Return the *settings* (or legacy *usage*) section."""
    return data.get("settings") or data.get("usage") or {}


def is_case_sensitive(data: dict) -> bool:
    """
    Heuristic: if any key/value is not identical to its upper‑case form,
    treat the mapping as case‑sensitive.
    """
    mapping = get_module_mapping(data)
    for k, v in mapping.items():
        if k != k.upper():
            return True
        if isinstance(v, str) and v != v.upper():
            return True
        if isinstance(v, list) and any(item != item.upper() for item in v):
            return True
    return False
