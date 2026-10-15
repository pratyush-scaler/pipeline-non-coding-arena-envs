"""Rank non-coding seeds for classification (v2 batch, 2026-10-02).

Arena's own session categories exclude code sessions (whose file bodies were not
extracted); the score orders the rest by how much a hard, dense task can draw
on: replay readiness, user corrections, retained files, turns, and whether the
trace model is one of the two calibration families (its real failures seed
traps aimed at exactly the models we screen).
"""
import json, sys
from collections import Counter
from pathlib import Path

CODE = {"code_writing", "code_debugging", "code_explanation"}
WEAK = {"image_video_generation", "chitchat_meta", "translation", "writing_creative"}
STRONG = {"data_analysis", "research_lookup", "document_creation", "planning_brainstorm",
          "writing_professional", "workflow_automation", "education_tutoring", "media_analysis"}

src, out, limit = Path(sys.argv[1]), Path(sys.argv[2]), int(sys.argv[3])
doc = json.loads(src.read_text())
rows = [r for r in doc["rows"] if not (set(r.get("categories") or []) & CODE)]

def score(r):
    cats = set(r.get("categories") or [])
    s = float(r.get("replay_readiness") or 0) * 2
    s += 0.6 * min(int(r.get("corrections") or 0), 4)
    s += min(int(r.get("files_retained") or 0), 20) / 20
    s += 0.3 if int(r.get("n_turns") or 0) >= 4 else 0
    model = str(r.get("model") or "")
    s += 1.0 if ("fable-5.1" in model or "gpt-6-astra" in model) else 0
    s += 0.4 * len(cats & STRONG) - 0.8 * len(cats & WEAK)
    if cats and cats <= WEAK:
        s -= 2
    return s

rows.sort(key=lambda r: (r.get("tier", 4), -score(r)))
per_session, chosen = Counter(), []
for r in sorted(rows, key=lambda r: -score(r)):
    if per_session[r["session_id"]] >= 2:
        continue
    per_session[r["session_id"]] += 1
    chosen.append({**r, "v2_shortlist_score": round(score(r), 3)})
    if len(chosen) >= limit:
        break
chosen.sort(key=lambda r: (r.get("tier", 4), -r["v2_shortlist_score"]))
out.write_text(json.dumps({**doc, "rows": chosen, "v2_shortlist": {
    "from": str(src), "noncode_rows": len(rows), "kept": len(chosen)}}))
print(f"non-code seeds {len(rows)}; shortlisted {len(chosen)} from {len(per_session)} sessions")
print("models:", Counter(r.get("model") for r in chosen).most_common(8))
print("tiers:", Counter(r.get("tier") for r in chosen))
