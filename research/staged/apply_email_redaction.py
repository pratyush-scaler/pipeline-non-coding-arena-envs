"""Staged: an `email` redaction kind (2026-10-02). Four seeds (a-001 OSM exports, a-004 a
scraped job page, a-036 a vendored README, a-056 two markdown files) died at the privacy
check because email addresses had no supported repair. Each address becomes a deterministic
placeholder on the reserved example domain, consistent within a file. Apply ONLY when no
build runs."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
p = ROOT / "pipeline/ledger/redaction.py"
s = p.read_text()
old = '''         "meeting-link", "hospital-stay-disclosure"}'''
new = '''         "meeting-link", "hospital-stay-disclosure", "email"}


def email_changes(content: str) -> list[dict]:
    """Replace every real email address with `contact-N@example.com`, the same N for
    the same address within one file, so cross-references inside the file survive."""
    from ..privacy import PATTERNS, _not_an_address
    seen: dict[str, int] = {}
    changes = []
    for match in PATTERNS["email"].finditer(content):
        if _not_an_address(match.group(1)):
            continue
        address = match.group(0).lower()
        number = seen.setdefault(address, len(seen) + 1)
        changes.append({"start": match.start(), "end": match.end(),
                        "line": content.count("\\n", 0, match.start()) + 1,
                        "kind": "email", "replacement": f"contact-{number}@example.com"})
    return changes'''
assert old in s, "KINDS"
s = s.replace(old, new, 1)
old = '''    if "hospital-stay-disclosure" in kinds:
        changes.extend(hospital_stay_changes(content))'''
new = '''    if "hospital-stay-disclosure" in kinds:
        changes.extend(hospital_stay_changes(content))
    if "email" in kinds:
        changes.extend(email_changes(content))'''
assert old in s, "transform"
s = s.replace(old, new, 1)
p.write_text(s)
print("applied")
