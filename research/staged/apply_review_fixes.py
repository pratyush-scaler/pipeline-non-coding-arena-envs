"""Staged review fixes (a-051, 2026-10-02). Apply ONLY when no build runs.

1. A review that requests revision is a semantic rejection -- the task goes to repair --
   even when some of the reviewer's own citations are malformed. Before, the mix made the
   task `unverified` with no repair (R4: holding a task on reviewer receipt defects is not
   required).
2. Failing reviewer summary rows about the optional construction plan / tool baselines
   (advisory in v2) do not block.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
p = ROOT / "pipeline/review.py"
s = p.read_text()
old = '''        or (revised and (problem in _SHAPE_ONLY
                        or problem.endswith(": review summary row did not pass")))
        for problem in problems)'''
new = '''        or (revised and (problem in _SHAPE_ONLY
                        or problem.endswith(": review summary row did not pass")
                        # v2: the reviewer asked for revision; a malformed quote
                        # in its own receipt does not make the rejection unverifiable.
                        or problem.startswith(("invalid solver autonomy citation", "invalid review citation"))))
        for problem in problems)'''
assert old in s, "semantic_rejection"
s = s.replace(old, new, 1)
old = '''    errors += [f"{row.get('id')}: review summary row did not pass" for row in rows
               if row.get("id") not in expected and row.get("verdict") != "pass"]'''
new = '''    # v2 (2026-10-02): the construction plan and tool baselines are optional
    # guidance whose findings are advisories; a reviewer row auditing them
    # cannot block the task.
    advisory = ("capability_plan", "tool_baseline", "difficulty_case", "fragility")
    errors += [f"{row.get('id')}: review summary row did not pass" for row in rows
               if row.get("id") not in expected and row.get("verdict") != "pass"
               and not any(token in str(row.get("id")) for token in advisory)]'''
assert old in s, "_check_rows"
s = s.replace(old, new, 1)
p.write_text(s)
print("applied")

# 3. The review prompt: construction aids are optional in v2.
s = p.read_text()
old = "Review quality.capability_plan when present: each shortcut's counterexample"
new = ("V2 (2026-10-02): quality.capability_plan, its tool_baselines and the labels in "
       "quality.difficulty_case / quality.fragility_budget are OPTIONAL authoring aids. A "
       "mislabelled or incomplete plan, baseline or misreading label is a difficulty_advisory, "
       "never a validity defect; source cases and counterexamples remain validity evidence "
       "only insofar as their executed answers must be coherent with the files.\n"
       "Review quality.capability_plan when present: each shortcut's counterexample")
assert old in s, "prompt"
p.write_text(s.replace(old, new, 1))
print("prompt updated")
