"""Survey every session of the 9/29 dump: category, model, correction signals, file bytes."""
import ast, json, sys, collections
from pathlib import Path

root = Path(sys.argv[1])
inv = json.loads((root / "inventory.json").read_text())
sizes = collections.defaultdict(int); counts = collections.defaultdict(int)
for item in inv["inventory"]:
    if isinstance(item, dict):
        path, size = item.get("path") or item.get("name"), item.get("size") or item.get("bytes") or 0
    else:
        path, size = item, 0
    parts = str(path).split("/")
    if "sessions" in parts and "files" in parts:
        sid = parts[parts.index("sessions") + 1]
        sizes[sid] += int(size or 0); counts[sid] += 1
rows = []
for sdir in sorted((root / "sessions").iterdir()):
    d = json.loads((sdir / "data.json").read_text())
    t = d["traces"][0]
    md = t.get("metadata")
    if isinstance(md, str):
        try: md = ast.literal_eval(md)
        except Exception: md = {}
    o = json.loads((sdir / "outcomes.json").read_text())
    sig = collections.Counter((x["signal_name"], x["outcome"]) for x in o["outcomes"])
    st = t.get("stats", {})
    first = ""
    for m in t["messages"]:
        if m["role"] == "user":
            c = m["content"]
            if isinstance(c, str):
                try: c = ast.literal_eval(c)
                except Exception: c = [{"type": "text", "text": c}]
            first = " ".join(x.get("text", "") for x in c if isinstance(x, dict))[:160].replace("\n", " ")
            break
    rows.append({
        "sid": sdir.name, "model": t.get("model_name"), "cats": md.get("categories"),
        "slices": md.get("slice_categories"), "user_msgs": st.get("user_msg_count"),
        "tools": st.get("tool_call_count"), "edits": st.get("edits"), "disapproves": st.get("disapproves"),
        "steer_fail": sig[("steerability", "failure")], "complaint": sig[("praise_complaint", "failure")],
        "task_fail": sig[("task_outcome_explicit", "failure")],
        "files": len(json.loads((sdir / "manifest.json").read_text())["files"]),
        "title": (t.get("title") or "")[:120], "first": first,
    })
out = root.parent / "survey.json"
out.write_text(json.dumps(rows, indent=1))
cat = collections.Counter(c for r in rows for c in (r["cats"] or ["?"]))
print("categories:", cat.most_common(40))
print("slices:", collections.Counter(c for r in rows for c in (r["slices"] or ["?"])).most_common(20))
