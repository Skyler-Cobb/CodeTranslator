import os, json
from utils import project_root

# ─────────────────────────────────────────────────────────────────────────────

def load_modules() -> dict:
    modules = {}
    mdir = os.path.join(project_root(), "modules")
    if not os.path.isdir(mdir):
        return modules
    for fn in os.listdir(mdir):
        if fn.lower().endswith(".json"):
            try:
                with open(os.path.join(mdir, fn), encoding="utf-8") as f:
                    data = json.load(f)
                modules[fn[:-5]] = data
            except Exception:
                continue
    return modules

# ───quick helpers─────────────────────────────────────────────────────────────
def get_module_settings(d: dict): return d.get("settings", d.get("usage", {}))
def get_module_mapping (d: dict): return d.get("encoding", d.get("mapping", {}))

def is_case_sensitive(d: dict) -> bool:
    """
    Heuristic: if any key/value is not identical to its upper-case form,
    treat the mapping as case-sensitive.
    """
    m = get_module_mapping(d)
    for k, v in m.items():
        if k != k.upper():
            return True
        vv = v if isinstance(v, list) else [v]
        if any(x != x.upper() for x in vv):
            return True
    return False
