"""Extract per-step habit features, fixture exposure and per-check outcomes.

Outputs (under research/scripts/out/):
  steps.jsonl      one record per (deduplicated) harness step
  checks.jsonl     one record per evaluated check attempt, with source-file exposure
  code.jsonl.gz    the agent's code/command text per step (for targeted greps)
Run:  python3 extract.py
"""
from __future__ import annotations

import gzip
import json
import os
import re
import sys
from collections import Counter
from multiprocessing import Pool

sys.path.insert(0, os.path.dirname(__file__))
from r3_common import (ART, OUT, FIX_ROOT, MODEL_SHORT, campaign_report, package_dir, task_name,
                       fixture_files, read_fixture, instruction, checks, target_sources, events, norm,
                       load_json)

F = re.IGNORECASE | re.MULTILINE
FEATS = {
    # ---- reading / listing
    "cat": r"(^|[\s;|&(])cat\s+(?!>)(?!<<)[^\s>|]",
    "cat_glob": r"(^|[\s;|&(])cat\s+[^|;\n]*\*",
    "sed_range": r"sed\s+-n\s+['\"]?\d+\s*,\s*(\d+|\$)\s*p",
    "head": r"(^|[\s;|&(])head\b",
    "tail": r"(^|[\s;|&(])tail\b",
    "nl": r"(^|[\s;|&(])nl\s",
    "grep": r"(^|[\s;|&(])(grep|egrep|fgrep)\s",
    "rg": r"(^|[\s;|&(])rg\s",
    "wc": r"(^|[\s;|&(])wc\s",
    "awk": r"(^|[\s;|&(])awk\s",
    "jq": r"(^|[\s;|&(])jq\s",
    "ls": r"(^|[\s;|&(])ls(\s|$)",
    "ls_R": r"ls\s+-[a-zA-Z]*R",
    "find": r"(^|[\s;|&(])find\s",
    "rg_files": r"rg\s+--files",
    "tree": r"(^|[\s;|&(])tree(\s|$)",
    "file_cmd": r"(^|[\s;|&(])file\s+\S",
    "py_open": r"\bopen\(",
    "py_read_text": r"read_text\(",
    "py_json_load": r"json\.loads?\(",
    "py_csv_module": r"csv\.(reader|DictReader)",
    "pd_read_csv": r"read_csv\(",
    "pd_read_csv_dtype_str": r"read_csv\([^)]*dtype\s*=\s*(str|object|['\"]string)",
    "pd_keep_default_na": r"keep_default_na",
    "pandas_any": r"\bimport pandas|\bpd\.",
    "read_excel": r"read_excel|openpyxl|xlrd|xlsx2csv",
    "bs4": r"BeautifulSoup|from bs4",
    "html_parser": r"HTMLParser|html\.parser",
    "lxml": r"\blxml\b",
    "regex_tag_strip": r"re\.sub\(\s*r?['\"]<\[\^>\]",
    "html_unescape": r"html\.unescape|unescape\(",
    "html2text_tools": r"html2text|\blynx\b|\bw3m\b|pandoc",
    "yaml_load": r"yaml\.(safe_)?load",
    "toml_load": r"tomllib|toml\.load",
    "docx": r"python-docx|from docx|import docx|word/document\.xml",
    "pdf": r"pypdf|PyPDF2|pdfplumber|pdftotext|\bfitz\b|pdfminer",
    "email_lib": r"email\.(message_from|parser|policy)|BytesParser|message_from_(string|bytes|file)",
    "ics_lib": r"icalendar|vobject|VEVENT",
    "image_lib": r"\bPIL\b|Image\.open|tesseract",
    # ---- formatting / hidden-content awareness (HTML/markdown analogues)
    "fmt_strike": r"<del\b|<s>|<s\s|<strike|line-through|text-decoration|~~",
    "fmt_hidden": r"display\s*:\s*none|aria-hidden|visibility\s*:\s*hidden|\bhidden\b",
    "fmt_html_comment": r"<!--|\bComment\b",
    "fmt_ins": r"<ins\b",
    "fmt_attr": r"\.get\(['\"](class|style|title|data-)|\[['\"](class|style|title)['\"]\]|attrs",
    # ---- numbers
    "round": r"\bround\(",
    "decimal": r"\bDecimal\b",
    "quantize": r"quantize\(",
    "half_up": r"ROUND_HALF_UP",
    "half_even": r"ROUND_HALF_EVEN",
    "round_other_mode": r"ROUND_(DOWN|UP|CEILING|FLOOR|HALF_DOWN)\b",
    "floor_ceil": r"math\.(floor|ceil)|\bfloor\(|\bceil\(",
    "int_cast": r"\bint\(",
    "float_cast": r"\bfloat\(",
    "sum": r"\bsum\(",
    "fsum": r"fsum\(",
    "fraction": r"\bFraction\b",
    "fmt_2dp": r":\s*,?\.\d+f|%\.\d+f",
    "isclose": r"isclose|abs\([^)]*\)\s*<\s*1e-",
    # ---- dates
    "strptime": r"strptime\(",
    "fromisoformat": r"fromisoformat",
    "to_datetime": r"to_datetime\(",
    "dayfirst": r"dayfirst",
    "dateutil": r"dateutil",
    "zoneinfo": r"zoneinfo|ZoneInfo",
    "pytz": r"\bpytz\b",
    "tz_ops": r"astimezone|utcoffset|tzinfo|timezone\.utc|timezone\(",
    "holidays_lib": r"import holidays|holidays\.",
    "holiday_word": r"holiday|feriado|festivo|férié|feiertag|jour f",
    "busday": r"busday|bdate_range|\bBDay\b|CustomBusinessDay|networkdays|workday",
    "weekday": r"\.weekday\(|isoweekday|%a\b|%A\b|day_name",
    "calendar_mod": r"\bcalendar\.|import calendar",
    "timedelta": r"timedelta\(",
    "relativedelta": r"relativedelta",
    "date_cmd": r"(^|[\s;|&(])date\s+(-d|--date)|(^|[\s;|&(])n?cal\s",
    # ---- matching / first-hit
    "re_search": r"re\.search\(",
    "re_match": r"re\.(full)?match\(",
    "re_findall": r"re\.(findall|finditer)\(",
    "next_call": r"\bnext\(",
    "str_find": r"\.(find|index)\(",
    "break_kw": r"\bbreak\b",
    "first_hit_shell": r"head\s+-(n\s*)?1\b|\s-m\s*1\b|--max-count",
    # ---- normalisation / dedupe
    "lower": r"\.lower\(\)|\.casefold\(\)",
    "strip": r"\.strip\(",
    "unicodedata": r"unicodedata",
    "resub_nonalnum": r"re\.sub\(\s*r?['\"](\[\^a-z0-9|\[\^\\w|\\W)",
    "resub_ws": r"re\.sub\(\s*r?['\"]\\s\+",
    "fuzzy": r"difflib|fuzz\b|rapidfuzz|SequenceMatcher|get_close_matches",
    "drop_duplicates": r"drop_duplicates",
    "set_call": r"\bset\(",
    "dict_fromkeys": r"dict\.fromkeys",
    "sort_u": r"sort\s+-u|\|\s*uniq",
    "counter": r"\bCounter\(",
    "groupby": r"groupby\(",
    # ---- verification
    "assert": r"(^|\s)assert\s",
    "sha": r"sha256|hashlib|sha1sum|md5sum",
    "json_validate": r"json\.tool|jq\s+(-e\s+)?\.\s|jsonschema",
    "diff_cmd": r"(^|[\s;|&(])(diff|cmp)\s",
    # ---- mtime / ordering
    "ls_t": r"ls\s+-[a-zA-Z]*t",
    "mtime": r"getmtime|st_mtime|\bmtime\b|(^|[\s;|&(])stat\s",
    "ls_l": r"ls\s+-[a-zA-Z]*l",
    # ---- quoted email text
    "quote_handling": r"startswith\(\s*['\"]>|\^\s*>|\^\\s\*>|Original Message|wrote:|escribi|a écrit|schrieb|Forwarded message|^>\s",
}
FEATS = {k: re.compile(v, F) for k, v in FEATS.items()}
PROSE = {
    "p_verify": re.compile(r"\b(verif|cross-check|double-check|sanity|re-?comput|recalcul|independent|confirm)", re.I),
    "p_readme": re.compile(r"\b(readme|summary|resumo|resumen|résumé|index)\b", re.I),
}
WRITE_RE = re.compile(
    r"(cat|tee)\s+>{1,2}\s*\S*deliverables|>\s*\S*/app/deliverables|deliverables[^\n]{0,200}(write_text|\.write\(|json\.dump|to_csv|open\([^)]*['\"]w)|"
    r"(write_text|json\.dump|open\()[^\n]{0,200}deliverables|\*\*\* (Add|Update) File:\s*\S*deliverables|OUT\s*=|out_path|outdir",
    re.I)
WRITE_ANY = re.compile(r"write_text\(|json\.dump\(|\.write\(|open\([^)]*['\"][wa]['\"]|(cat|tee)\s+>|>\s*\S*deliverables|to_csv\(|shutil\.copy|\bcp\s|\bmv\s", re.I)
DELIV_READ_RE = re.compile(r"(cat|head|sed|jq|less|python3?)\b[^\n]{0,200}deliverables|json\.load\([^\n]{0,120}deliverables|READ \S*deliverables", re.I)
SCRIPT_EXT = (".py", ".sh", ".js", ".mjs", ".ts")
MIN_PROBE = 24
MAX_PROBES = 300


def is_html(rel: str) -> bool:
    return rel.lower().endswith((".html", ".htm", ".xml", ".svg"))


def probes_for(pkg: str, files: tuple, instr_n: str):
    lines_by_file = {}
    count = Counter()
    for rel in files:
        txt = read_fixture(pkg, rel)
        h = is_html(rel)
        ps = []
        seen = set()
        lines = txt.splitlines()
        thr = MIN_PROBE
        if sum(1 for line in lines if len(norm(line, strip_tags=h)) >= MIN_PROBE) < 5:
            thr = 12
        for line in lines:
            n = norm(line, strip_tags=h)
            if len(n) < thr or n in seen:
                continue
            seen.add(n)
            ps.append(n)
        lines_by_file[rel] = ps
        for n in seen:
            count[n] += 1
    out = {}
    for rel, ps in lines_by_file.items():
        ps = [p for p in ps if count[p] == 1 and p not in instr_n]
        if len(ps) > MAX_PROBES:
            step = len(ps) / MAX_PROBES
            ps = [ps[int(i * step)] for i in range(MAX_PROBES)]
        out[rel] = ps
    return out


PROBE_CACHE = {}


def analyse(path: str):
    try:
        traj = json.load(open(path))
    except Exception as e:
        return None
    cdir, rest = path.split("/jobs/run/", 1)
    trial_id = rest.split("/")[0]
    step = rest.split("/steps/")[1].split("/")[0]
    rep = campaign_report(cdir)
    agent = rep.get("agent")
    if agent not in ("claude-code", "codex"):
        return None
    model = MODEL_SHORT.get(rep.get("model"), rep.get("model"))
    pkg = package_dir(cdir)
    task = task_name(pkg)
    trial = next((t for t in rep.get("trials", []) if t.get("id") == trial_id), None) or {}
    st = next((s for s in trial.get("steps", []) or [] if s.get("name") == step), None) or {}
    valid = bool(trial.get("valid")) and bool(st.get("valid", trial.get("valid")))
    chk = st.get("checks") or {}
    evaluated = {}
    for k, v in chk.items():
        cid = k.split("/", 1)[-1]
        if v.get("status") != "evaluated" or v.get("gated_out") or v.get("skipped") or v.get("error"):
            continue
        evaluated[cid] = (v.get("value") or 0) >= 1.0

    files = fixture_files(pkg)
    instr = instruction(pkg, step)
    instr_n = norm(instr, strip_tags=True)
    key = (pkg, step)
    if key not in PROBE_CACHE:
        PROBE_CACHE[key] = probes_for(pkg, files, instr_n)
    probes = PROBE_CACHE[key]

    ev = events(traj)
    calls = [e for e in ev if e["kind"] == "call"]
    code_parts = []
    first_write = None
    idx = 0
    seq = []  # (index, kind, ...)
    for i, e in enumerate(ev):
        if e["kind"] == "call":
            t = e["tool"]
            txt = e.get("text", "")
            p = e.get("path", "") or ""
            if t in ("cmd", "js", "edit", "read", "grep", "glob") or (t in ("write", "patch") and (p.endswith(SCRIPT_EXT) or re.search(r"File:\s*\S+\.(py|sh|js)\b", txt))):
                code_parts.append(txt)
            is_write = (t == "write" and "deliverables" in p) or (t == "patch" and "deliverables" in txt) or (t in ("cmd", "js") and "deliverables" in txt and WRITE_ANY.search(txt))
            if is_write and first_write is None:
                first_write = i
    code = "\n".join(code_parts)

    feats = {k: len(rx.findall(code)) for k, rx in FEATS.items()}
    prose = "\n".join(e["text"] for e in ev if e["kind"] == "text")
    for k, rx in PROSE.items():
        feats[k] = len(rx.findall(prose))
    feats["n_calls"] = len(calls)
    feats["n_read_tool"] = sum(1 for e in calls if e["tool"] == "read")
    feats["n_grep_tool"] = sum(1 for e in calls if e["tool"] in ("grep", "glob"))
    feats["n_cmd"] = sum(1 for e in calls if e["tool"] in ("cmd", "js"))
    feats["n_trunc"] = sum(1 for e in ev if e["kind"] == "obs" and e.get("truncated"))
    feats["n_persisted"] = sum(1 for e in ev if e["kind"] == "obs" and e.get("persisted"))
    feats["followed_persisted"] = int(any("tool-results/" in (e.get("text", "") + e.get("path", "")) for e in calls))
    mts = [m for e in calls for m in (e.get("maxtok") or [])]
    feats["maxtok_median"] = sorted(mts)[len(mts) // 2] if mts else None

    # read-back of deliverable after first write
    feats["first_write_idx_frac"] = None
    feats["reread_deliv_after_write"] = 0
    if first_write is not None:
        feats["first_write_idx_frac"] = round(first_write / max(1, len(ev)), 3)
        feats["reread_deliv_after_write"] = int(any(e["kind"] == "call" and DELIV_READ_RE.search(e.get("text", "")) for e in ev[first_write + 1:]))

    # exposure
    obs_all = [e for e in ev if e["kind"] == "obs"]
    blob_raw = norm("\n".join(e["text"] for e in obs_all))
    blob_tag = norm("\n".join(e["text"] for e in obs_all), strip_tags=True)
    pre = [e for j, e in enumerate(ev) if e["kind"] == "obs" and (first_write is None or j < first_write)]
    post = [e for j, e in enumerate(ev) if e["kind"] == "obs" and first_write is not None and j > first_write]
    blob_post_raw = norm("\n".join(e["text"] for e in post)) if post else ""
    blob_post_tag = norm("\n".join(e["text"] for e in post), strip_tags=True) if post else ""
    trunc_texts = [e for e in ev if e["kind"] == "obs" and (e.get("truncated") or e.get("persisted"))]
    trunc_blob = norm("\n".join(e["text"] for e in trunc_texts), strip_tags=True) if trunc_texts else ""
    code_l = code.lower()
    file_rows = {}
    for rel in files:
        ps = probes[rel]
        h = is_html(rel)
        b = blob_tag if h else blob_raw
        hits = sum(1 for p in ps if p in b)
        bp = blob_post_tag if h else blob_post_raw
        post_hits = sum(1 for p in ps if p in bp) if bp else 0
        base = os.path.basename(rel).lower()
        named = base in code_l or rel.lower() in code_l
        in_instr = base in instr.lower() or rel.lower() in instr.lower() or os.path.splitext(base)[0] in instr.lower()
        in_trunc = sum(1 for p in ps if p in trunc_blob) if trunc_blob else 0
        file_rows[rel] = {
            "n_probes": len(ps),
            "frac": round(hits / len(ps), 3) if ps else None,
            "post_frac": round(post_hits / len(ps), 3) if ps else None,
            "named": named,
            "in_instr": in_instr,
            "in_trunc_obs": in_trunc,
            "bytes": os.path.getsize(os.path.join(pkg, "environment", "files", rel)) if os.path.exists(os.path.join(pkg, "environment", "files", rel)) else 0,
        }

    # first file opened & order
    rec = {
        "path": os.path.relpath(path, ART),
        "root": os.path.relpath(path, ART).split("/")[0],
        "campaign": os.path.relpath(cdir, ART),
        "session": traj.get("session_id"),
        "agent": agent, "model": model, "task": task, "pkg": os.path.relpath(pkg, ART),
        "trial": trial_id, "step": step, "valid": valid,
        "reward": st.get("reward"),
        "n_checks": len(evaluated),
        "failed": sorted(k for k, v in evaluated.items() if not v),
        "feats": feats,
        "files": file_rows,
        "n_files": len(files),
    }
    check_rows = []
    cks = checks(pkg)
    for cid, ok in evaluated.items():
        c = cks.get(cid)
        srcs = sorted(target_sources(pkg, c)) if c else []
        fr = [file_rows[s]["frac"] for s in srcs if s in file_rows and file_rows[s]["frac"] is not None]
        check_rows.append({
            "path": rec["path"], "model": model, "task": task, "step": step, "valid": valid, "check": cid,
            "passed": ok, "sources": srcs,
            "src_min_frac": min(fr) if fr else None,
            "src_named": [file_rows[s]["named"] for s in srcs if s in file_rows],
            "src_in_trunc": [file_rows[s]["in_trunc_obs"] for s in srcs if s in file_rows],
            "trap": (c or {}).get("trap") or (c or {}).get("traps"),
            "dimension": (c or {}).get("dimension"),
        })
    return rec, check_rows, {"path": rec["path"], "code": code, "prose": prose[:20000]}


def main():
    paths = [l.strip() for l in open(os.path.join(OUT, "trajectories.txt")) if l.strip()]
    paths = [os.path.join(ART, p) for p in paths]
    seen = set()
    n = 0
    with Pool(8) as pool, open(os.path.join(OUT, "steps.jsonl"), "w") as fs, \
            open(os.path.join(OUT, "checks.jsonl"), "w") as fc, gzip.open(os.path.join(OUT, "code.jsonl.gz"), "wt") as fz:
        for res in pool.imap_unordered(analyse, paths, chunksize=8):
            if not res:
                continue
            rec, crow, code = res
            k = (rec["session"], rec["step"], rec["trial"])
            if rec["session"] and k in seen:
                continue
            seen.add(k)
            fs.write(json.dumps(rec, ensure_ascii=False) + "\n")
            for r in crow:
                fc.write(json.dumps(r, ensure_ascii=False) + "\n")
            fz.write(json.dumps(code, ensure_ascii=False) + "\n")
            n += 1
            if n % 500 == 0:
                print(n, flush=True)
    print("done", n)


if __name__ == "__main__":
    main()
