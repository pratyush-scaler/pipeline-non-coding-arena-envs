"""Staged: [T1] a field name referenced INSIDE another field's definition must not end that
definition (a-032, 2026-10-02: "`uhd_elvas` — lista de `pedido` (texto) dos pedidos ..."
was read as undefined because the window stopped at `pedido`). Apply ONLY when no build runs."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
p = ROOT / "pipeline/author/validate.py"
s = p.read_text()
old = '''        nxt = next((s for s, _ in stops if s >= cursor), None)
        if nxt is not None:
            limit = min(limit, nxt)
        window = text[cursor:limit]'''
new = '''        # Another field's name ends this definition only where a NEW definition
        # starts -- a line or bullet start, or after a sentence break. A name
        # referenced mid-sentence ("a list of `pedido` values ...") is part of
        # this field's meaning (a-032, 2026-10-02).
        nxt = next((s for s, _ in stops if s >= cursor and _starts_definition(text, s)), None)
        if nxt is not None:
            limit = min(limit, nxt)
        window = text[cursor:limit]'''
assert old in s, "window"
s = s.replace(old, new, 1)
anchor = "def _definition_windows("
helper = '''def _starts_definition(text: str, start: int) -> bool:
    """Whether a backticked field name at `start` opens a new definition."""
    before = text[max(0, start - 6):start]
    stripped = text[:start].rstrip(" \\t")
    if not stripped or stripped.endswith("\\n"):
        return True
    return bool(_re.search(r"(?:^|\\n)\\s*(?:[-*\\u2022]|\\d+[.)])\\s*$", text[max(0, start - 12):start])
                or _re.search(r"[.;:!?]\\s*$", before))


'''
s = s.replace(anchor, helper + anchor, 1)
p.write_text(s)
print("applied")
