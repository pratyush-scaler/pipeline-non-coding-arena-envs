"""Per-model habit tables from out/steps.jsonl (+ checks.jsonl).

Prints markdown tables; writes out/habits.json. Valid steps only unless noted.
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter, defaultdict
from statistics import median

sys.path.insert(0, os.path.dirname(__file__))
from r3_common import OUT

MODELS = ("fable", "astra")


def load():
    rows = [json.loads(l) for l in open(os.path.join(OUT, "steps.jsonl"))]
    return rows


def pct(n, d):
    return f"{n}/{d} ({100*n/d:.1f}%)" if d else "0/0"


def share(rows, pred):
    out = {}
    for m in MODELS:
        rs = [r for r in rows if r["model"] == m]
        out[m] = (sum(1 for r in rs if pred(r)), len(rs))
    return out


def table(title, rows, items):
    print(f"\n### {title}\n")
    print("| habit | Fable | Astra |")
    print("|---|---|---|")
    res = {}
    for name, pred in items:
        s = share(rows, pred)
        res[name] = s
        print(f"| {name} | {pct(*s['fable'])} | {pct(*s['astra'])} |")
    return res


def f(k, n=1):
    return lambda r: (r["feats"].get(k) or 0) >= n


def main():
    allrows = load()
    rows = [r for r in allrows if r["valid"]]
    out = {}
    # inventory
    print("## Inventory\n")
    inv = defaultdict(Counter)
    for r in allrows:
        inv[(r["root"], r["model"])]["steps"] += 1
        inv[(r["root"], r["model"])]["valid"] += int(r["valid"])
        inv[(r["root"], r["model"])]["fail"] += int(r["valid"] and bool(r["failed"]))
    print("| root | model | steps | valid | valid steps with >=1 failed check |")
    print("|---|---|---|---|---|")
    for (root, m), c in sorted(inv.items()):
        print(f"| {root} | {m} | {c['steps']} | {c['valid']} | {c['fail']} |")
    tasks = {m: len({r['task'] for r in rows if r['model'] == m}) for m in MODELS}
    print(f"\nvalid steps: fable {sum(1 for r in rows if r['model']=='fable')}, astra {sum(1 for r in rows if r['model']=='astra')}; task labels {tasks}")

    out["reading"] = table("Q1 reading tools (share of valid steps using it at least once)", rows, [
        ("Bash `cat` of a file", f("cat")),
        ("`cat` with a glob (`cat dir/*`)", f("cat_glob")),
        ("`sed -n 'a,bp'` range reads", f("sed_range")),
        ("`head`", f("head")),
        ("`tail`", f("tail")),
        ("`grep`/`egrep`", f("grep")),
        ("`rg`", f("rg")),
        ("grep or rg", lambda r: r["feats"]["grep"] + r["feats"]["rg"] > 0),
        ("`wc`", f("wc")),
        ("`awk`", f("awk")),
        ("`jq`", f("jq")),
        ("Claude Code Read tool", f("n_read_tool")),
        ("Claude Code Grep/Glob tool", f("n_grep_tool")),
        ("python `open(`", f("py_open")),
        ("python `read_text(`", f("py_read_text")),
        ("`json.load(s)`", f("py_json_load")),
        ("`csv.reader/DictReader`", f("py_csv_module")),
        ("pandas `read_csv`", f("pd_read_csv")),
        ("pandas `read_csv(dtype=str)`", f("pd_read_csv_dtype_str")),
        ("pandas imported/used at all", f("pandas_any")),
        ("BeautifulSoup", f("bs4")),
        ("`html.parser`/HTMLParser", f("html_parser")),
        ("regex tag strip `re.sub(r'<[^>]+>'…)`", f("regex_tag_strip")),
        ("`html.unescape`", f("html_unescape")),
        ("html2text/lynx/w3m/pandoc", f("html2text_tools")),
        ("`yaml.safe_load`", f("yaml_load")),
        ("read_excel/openpyxl/xlrd", f("read_excel")),
        ("python-docx / word/document.xml", f("docx")),
        ("pypdf/pdfplumber/pdftotext/fitz", f("pdf")),
        ("email module (message_from_*, BytesParser)", f("email_lib")),
        ("icalendar/VEVENT parsing", f("ics_lib")),
        ("PIL/tesseract", f("image_lib")),
    ])
    out["listing"] = table("Q1 listing before reading", rows, [
        ("`ls`", f("ls")),
        ("`ls -R`", f("ls_R")),
        ("`find`", f("find")),
        ("`rg --files`", f("rg_files")),
        ("`tree`", f("tree")),
        ("any listing (ls/find/rg --files/tree/Glob)", lambda r: any(r["feats"][k] for k in ("ls", "find", "rg_files", "tree", "n_grep_tool"))),
        ("`file` command (type sniffing)", f("file_cmd")),
    ])
    out["formatting"] = table("Q1 formatting / hidden-content awareness in code", rows, [
        ("struck-through text (`<del>`, `<s>`, line-through, `~~`)", f("fmt_strike")),
        ("hidden content (display:none, hidden, aria-hidden)", f("fmt_hidden")),
        ("HTML comments (`<!--`)", f("fmt_html_comment")),
        ("`<ins>`", f("fmt_ins")),
        ("tag attributes (class/style/title)", f("fmt_attr")),
    ])
    out["numbers"] = table("Q2 numbers", rows, [
        ("`round(`", f("round")),
        ("`Decimal`", f("decimal")),
        ("`.quantize(`", f("quantize")),
        ("`ROUND_HALF_UP`", f("half_up")),
        ("`ROUND_HALF_EVEN`", f("half_even")),
        ("other ROUND_* modes", f("round_other_mode")),
        ("round() without any Decimal", lambda r: r["feats"]["round"] > 0 and r["feats"]["decimal"] == 0),
        ("math.floor/ceil", f("floor_ceil")),
        ("`int(`", f("int_cast")),
        ("`float(`", f("float_cast")),
        ("`sum(`", f("sum")),
        ("`math.fsum`", f("fsum")),
        ("`Fraction`", f("fraction")),
        ("fixed-decimals format (`:.2f`)", f("fmt_2dp")),
        ("tolerance compare (isclose / abs()<1e-)", f("isclose")),
    ])
    out["dates"] = table("Q2 dates and calendars", rows, [
        ("`strptime`", f("strptime")),
        ("`fromisoformat`", f("fromisoformat")),
        ("`pd.to_datetime`", f("to_datetime")),
        ("`dayfirst`", f("dayfirst")),
        ("dateutil", f("dateutil")),
        ("zoneinfo", f("zoneinfo")),
        ("pytz", f("pytz")),
        ("tz ops (astimezone/utcoffset/tzinfo)", f("tz_ops")),
        ("`holidays` library", f("holidays_lib")),
        ("word 'holiday'/feriado/férié in code", f("holiday_word")),
        ("business-day helpers (busday/BDay/networkdays)", f("busday")),
        ("weekday()/isoweekday/%a", f("weekday")),
        ("calendar module", f("calendar_mod")),
        ("timedelta", f("timedelta")),
        ("relativedelta", f("relativedelta")),
        ("shell `date -d` / `cal`", f("date_cmd")),
    ])
    out["matching"] = table("Q6 matching / normalisation / dedupe idioms", rows, [
        ("`re.search` (first match)", f("re_search")),
        ("`re.match`", f("re_match")),
        ("`re.findall/finditer`", f("re_findall")),
        ("`next(`", f("next_call")),
        ("`.find(`/`.index(`", f("str_find")),
        ("`break`", f("break_kw")),
        ("shell first-hit (`head -1`, `-m1`)", f("first_hit_shell")),
        ("`.lower()`/`.casefold()`", f("lower")),
        ("`.strip(`", f("strip")),
        ("unicodedata", f("unicodedata")),
        ("strip non-alnum via re.sub", f("resub_nonalnum")),
        ("collapse whitespace via re.sub", f("resub_ws")),
        ("fuzzy match (difflib/rapidfuzz)", f("fuzzy")),
        ("`drop_duplicates`", f("drop_duplicates")),
        ("`set(`", f("set_call")),
        ("`sort -u`/`uniq`", f("sort_u")),
        ("`Counter(`", f("counter")),
        ("`groupby(`", f("groupby")),
        ("`ls -t` / mtime", lambda r: r["feats"]["ls_t"] + r["feats"]["mtime"] > 0),
        ("`ls -l` (sees mtimes)", f("ls_l")),
        ("quoted-reply handling (`^>`, 'wrote:')", f("quote_handling")),
    ])
    out["verify"] = table("Q4 verification", rows, [
        ("`assert`", f("assert")),
        ("sha256/hash of sources", f("sha")),
        ("JSON validation (json.tool/jq ./jsonschema)", f("json_validate")),
        ("diff/cmp", f("diff_cmd")),
        ("re-reads deliverable after first write", f("reread_deliv_after_write")),
        ("re-displays any fixture line after first write", lambda r: any((v.get("post_frac") or 0) > 0 for v in r["files"].values())),
        ("verification words in visible prose", f("p_verify")),
        ("deliverable write detected", lambda r: r["feats"].get("first_write_idx_frac") is not None),
    ])
    # tool-call stats
    print("\n### Tool-call counts per valid step (median)\n")
    for m in MODELS:
        rs = [r for r in rows if r["model"] == m]
        print(f"- {m}: calls {median(r['feats']['n_calls'] for r in rs)}, read-tool calls total {sum(r['feats']['n_read_tool'] for r in rs)}, steps {len(rs)}")
    json.dump(out, open(os.path.join(OUT, "habits.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
