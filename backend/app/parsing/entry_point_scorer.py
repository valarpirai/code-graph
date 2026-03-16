from .base import FunctionDef

ENTRY_NAMES = {"main", "run", "start", "handle", "handler", "execute"}
ENTRY_FILES = {"main", "index", "app", "server", "entrypoint"}


def score_entry_point(fn: FunctionDef, file_stem: str, has_incoming_calls: bool) -> float:
    score = 0.0
    if fn.name.lower() in ENTRY_NAMES:
        score += 0.3
    if not has_incoming_calls:
        score += 0.2
    if fn.is_exported:
        score += 0.1
    if fn.framework_role == "rest_endpoint":
        score += 0.3
    if file_stem.lower() in ENTRY_FILES:
        score += 0.1
    return min(score, 1.0)
