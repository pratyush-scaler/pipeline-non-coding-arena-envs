"""Validation harness (batch-6 brief section 7). Works only on copies under the scratch root given as argv[2].

usage: python3.11 -I -B validate.py <abs task dir> <scratch dir>
"""
import copy
import csv
import io
import filecmp
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

TASK = Path(sys.argv[1]).resolve()
SCR = Path(sys.argv[2]).resolve()
PY = os.environ.get("ARENA_PY311") or sys.executable  # b6ctl validate runs this file under the verifier python3.11
OUTF = "cover_matrix_check.json"
FAILS = []
MATRIX = "subcategory_covers/matritsa_chekhly_zapusk.csv"
PASSPORT = "subcategory_covers/pasport_subkategorii_chekhly.md"
HR = "hr_and_guides/kartochka_stazhera.md"
LAST = "category_assortment/aktivnyy_assortiment_2026-10-09.csv"
KOV = "subcategory_covers/pismo_kovertek_2026-10-06.md"
LIC = "licensing/litsenzii_na_risunki_2026-10-01.md"
PROTOCOL = "subcategory_covers/protokol_soglasovaniya_2026-09-21.md"
MEMO = "category_assortment/pamyatka_razdely_saita.md"
BSH = "subcategory_covers/pismo_bagazhnyy_shchit_2026-09-10.md"
DECK = "defence/zashchita_slaydy_v5.md"


def fresh(name):
    d = SCR / name
    if d.exists():
        shutil.rmtree(d)
    shutil.copytree(TASK, d, ignore=shutil.ignore_patterns("__pycache__"))
    return d


def run(args, **kw):
    return subprocess.run([PY, "-I", "-B", *map(str, args)], check=True, capture_output=True, text=True, **kw)


def solve(task, misread=""):
    out = task / "_out"
    if out.exists():
        shutil.rmtree(out)
    env = dict(os.environ, ARENA_SOURCE=str(task / "environment/files"), ARENA_OUT=str(out), ARENA_MISREAD=misread)
    run([task / "steps/01-task/solution/solve.py"], env=env)
    return json.loads((out / OUTF).read_text())


def grade(task, answer=None, raw=None, extra=None, fifo=False):
    sub = task / "_sub"
    if sub.exists():
        shutil.rmtree(sub)
    sub.mkdir()
    if raw is not None:
        (sub / OUTF).write_bytes(raw if isinstance(raw, bytes) else raw.encode())
    elif answer is not None:
        (sub / OUTF).write_text(json.dumps(answer, ensure_ascii=False))
    for k, v in (extra or {}).items():
        (sub / k).write_text(v)
    if fifo:
        os.mkfifo(sub / "pipe")
    rew = task / "_reward.json"
    env = dict(os.environ, ARENA_SOURCE=str(task / "environment/files"), ARENA_SUBMITTED=str(sub),
               ARENA_STEP="01-task", ARENA_REWARD=str(rew))
    p = subprocess.run([PY, "-I", "-B", str(task / "tests/criteria.py")], env=env, capture_output=True, text=True, timeout=300)
    if p.returncode != 0:
        return None, {"error": p.stderr[-800:]}
    g = json.loads(p.stdout)
    failed = sorted(k for k, v in g["checks"].items() if not v.get("passed"))
    return g["reward"], {"failed": failed, "contract": g.get("contract_errors")}


def expect(label, ok, detail=""):
    print(("   ok   " if ok else "   FAIL ") + label + (f"  [{detail}]" if detail else ""))
    if not ok:
        FAILS.append(label)


def rebuild(task):
    for s in ("make_checks.py", "make_contract.py", "build_tests.py"):
        run([task / "authoring" / s, task])


def edit(task, rel, old, new, count=1):
    p = task / "environment/files" / rel
    t = p.read_text(encoding="utf-8")
    assert t.count(old) == count, (rel, old, t.count(old))
    p.write_text(t.replace(old, new), encoding="utf-8")
    run([task / "authoring/build_tests.py", task])   # refreeze manifest and projections of the edited copy


def mod(ans, path, value):
    a = copy.deepcopy(ans)
    cur = a
    keys = path.split(".")
    for k in keys[:-1]:
        cur = cur[k]
    cur[keys[-1]] = value
    return a


base = fresh("base")
REF = solve(base)
print("1. REFERENCE AND EMPTY")
print("   key:", json.dumps(REF, ensure_ascii=False, separators=(",", ":")))
r, info = grade(base, REF)
expect("reference scores 1.0", r == 1.0, f"{r} {info}")
r, info = grade(base)
expect("empty workspace scores 0.0", r == 0.0, f"{r} {info.get('contract')}")

print("2. MISREADINGS (each alone, the interlocked pair, the decisive trio and all five; design_lint runs all 32 subsets)")
traps = json.loads((TASK / "authoring/traps.json").read_text())
weights = {c["id"]: c["weight"] for c in json.loads((TASK / "tests/checks.json").read_text())["checks"]}
MISREAD_OUT = {}
for subset in [["P1"], ["P2"], ["P5"], ["P6"], ["P7"], ["P1", "P2"], ["P5", "P6"], ["P2", "P5", "P7"], ["P1", "P2", "P5", "P6", "P7"]]:
    ans = solve(base, ",".join(subset))
    MISREAD_OUT[",".join(subset)] = ans
    r, info = grade(base, ans)
    want = sorted(c for p in traps["premises"] if p["id"] in subset for c in p["checks"])
    wr = round(1 - sum(weights[c] for c in want) / 100, 4)
    expect(f"misread {','.join(subset)} fails exactly {want}, reward {wr}", info["failed"] == want and abs(r - wr) < 1e-9,
           f"got {info['failed']} {r}")

print("2b. NO ANOMALY UNDER THE DEFAULT (HARD-DOCTRINE section 7.1): the all-misread deliverable is complete and consistent")
M = MISREAD_OUT["P1,P2,P5,P6,P7"]
ms = M["slide1"]
mrows = list(csv.DictReader(io.StringIO((base / "environment/files" / MATRIX).read_text(encoding="utf-8"))))
prints = {r["Название позиции"].split(" / ")[0] for r in mrows}
letter_new = re.search(r"рисунок меняем на «([^»]+)»", (base / "environment/files" / KOV).read_text(encoding="utf-8")).group(1)
labels = {k: sum(r["Размер (этикетка поставщика)"] == k for r in mrows) for k in ("S", "M", "L", "XL")}
deck = (base / "environment/files/defence/zashchita_slaydy_v5.md").read_text(encoding="utf-8")
deck_split = {k: int(v) for k, v in re.findall(r"(S|M|L|XL) — (\d+)", deck)}
cons = [
    ("design_count equals len(designs)", M["design_count"] == len(M["designs"])),
    ("every misread design is a matrix print or the letter's new print (no stray, nothing unmatched)",
     set(M["designs"]) <= prints | {letter_new} and prints <= set(M["designs"])),
    ("size split sums to matrix_sku_count (60) and equals the supplier-label split and the deck's split",
     sum(M["skus_by_size"].values()) == M["matrix_sku_count"] == 60 and M["skus_by_size"] == labels == deck_split),
    ("cluster and body splits sum to 60", sum(M["skus_by_colour_cluster"].values()) == 60 == sum(M["skus_by_body"].values())),
    ("price split sums to 60 and every segment is used (no empty or implausible segment)",
     sum(M["skus_by_price_segment"].values()) == 60 and min(M["skus_by_price_segment"].values()) > 0),
    ("active_skus_after equals the subcategory sum and the 9 October export's row count",
     ms["active_skus_after"] == sum(ms["active_skus_after_by_subcategory"].values()) == len(
         list(csv.DictReader(io.StringIO((base / "environment/files" / LAST).read_text(encoding="utf-8")))))),
    ("share is a plausible whole percent of its own counts", 0 < ms["ru_share_after_pct"] < 100
     and abs(ms["ru_share_after_pct"] - 100 * ms["ru_skus_after"] / ms["active_skus_after"]) < 1),
]
for label, ok in cons:
    expect(label, ok)
print("   misread deliverable:", json.dumps({k: M[k] for k in ("design_count", "skus_by_size")}, ensure_ascii=False),
      json.dumps(ms, ensure_ascii=False))

print("3. RULE-BREAKING VARIANTS (each must lose credit)")
S = REF["skus_by_size"]
C = REF["skus_by_colour_cluster"]
from fractions import Fraction


def split_of(f):
    out = {"base": 0, "mid": 0, "top": 0}
    for r in mrows:
        x = f(r)
        out["base" if x <= 599 else "mid" if x <= 749 else "top"] += 1
    return out


def price(r):
    return Fraction(int(r["Цена закупки (руб)"]))


split_all_net = split_of(lambda r: price(r) / Fraction(122, 100))
split_all_gross = split_of(lambda r: price(r) if r["Поставщик"] == "Багажный щит" else price(r) * Fraction(122, 100))
split_minus22 = split_of(lambda r: price(r) * Fraction(78, 100) if r["Поставщик"] == "Багажный щит" else price(r))
split_20 = split_of(lambda r: price(r) / Fraction(120, 100) if r["Поставщик"] == "Багажный щит" else price(r))
expect("P7 census: VAT at 20 % on Багажный щит's rows gives the reference split (not a wrong reading)",
       split_20 == REF["skus_by_price_segment"], f"{split_20}")
expect("P7 census: printed, all-net and all-gross splits each differ from the reference and from each other",
       len({json.dumps(x, sort_keys=True) for x in (M["skus_by_price_segment"], split_all_net, split_all_gross,
                                                     REF["skus_by_price_segment"])}) == 4,
       f"printed={M['skus_by_price_segment']} all_net={split_all_net} all_gross={split_all_gross}")
s1 = REF["slide1"]
AS = s1["active_skus_after_by_subcategory"]
D = REF["designs"]


def subc(**kw):
    return mod(REF, "slide1.active_skus_after_by_subcategory", dict(AS, **kw))


variants = [
    ("designs = the 28 position names (2.0.0's print convention)", mod(mod(REF, "designs", sorted({r["Название позиции"] for r in mrows})), "design_count", 28), ["obj_designs"]),
    ("designs keep 'Ретро-марки' and add the new print (P5 default)", mod(mod(REF, "designs", D + ["Ретро-марки"]), "design_count", len(D) + 1), ["obj_designs"]),
    ("designs drop 'Ретро-марки' but omit the new print", mod(mod(REF, "designs", [d for d in D if d != letter_new]), "design_count", len(D) - 1), ["obj_designs"]),
    ("designs ignore the letter (the 24 matrix prints)", mod(mod(REF, "designs", sorted(prints)), "design_count", len(prints)), ["obj_designs"]),
    ("designs missing one print", mod(mod(REF, "designs", D[1:]), "design_count", len(D) - 1), ["obj_designs"]),
    ("designs with one print repeated under its ground colour", mod(mod(REF, "designs", D + ["Карта мира / молоко"]), "design_count", len(D) + 1), ["obj_designs"]),
    ("design_count disagrees with the solver's own list", mod(REF, "design_count", len(D) + 4), ["obj_design_count"]),
    ("scales left at the export's count, total not updated (2.1.1: share on own counts still passes)", subc(luggage_scales=AS["luggage_scales"] + 6),
     ["obj_after_by_subcategory", "obj_after_total"]),
    ("scales and total both left at the export (P1, consistent)", mod(subc(luggage_scales=AS["luggage_scales"] + 6), "slide1.active_skus_after", s1["active_skus_after"] + 6),
     ["obj_after_by_subcategory"]),
    ("all Indian SKUs of every subcategory removed", mod(subc(accessories=AS["accessories"] - 1), "slide1.active_skus_after", s1["active_skus_after"] - 1),
     ["obj_after_by_subcategory", "obj_after_total"]),
    ("every luggage scale removed (own share kept consistent)", mod(mod(subc(luggage_scales=0), "slide1.active_skus_after", s1["active_skus_after"] - AS["luggage_scales"]),
     "slide1.ru_share_after_pct", 100 * s1["ru_skus_after"] // (s1["active_skus_after"] - AS["luggage_scales"])), ["obj_after_by_subcategory"]),
    ("share rounded to nearest (P2)", mod(REF, "slide1.ru_share_after_pct", s1["ru_share_after_pct"] + 1), ["obj_ru_share_pct"]),
    ("share one below the floor", mod(REF, "slide1.ru_share_after_pct", s1["ru_share_after_pct"] - 1), ["obj_ru_share_pct"]),
    ("sizes by supplier label = lower end (P6)", mod(REF, "skus_by_size", labels), ["obj_size_bands"]),
    ("price segments on the printed price (P7 default)", mod(REF, "skus_by_price_segment", M["skus_by_price_segment"]), ["obj_price_segments"]),
    ("price segments with the VAT taken out of every row, both suppliers (P7 census)", mod(REF, "skus_by_price_segment", split_all_net), ["obj_price_segments"]),
    ("price segments with VAT added to Ковертэк's rows, all on the gross basis (P7 census)", mod(REF, "skus_by_price_segment", split_all_gross), ["obj_price_segments"]),
    ("price segments with 22 % of the gross taken off Багажный щит's figures (x0.78, an arithmetic slip; P7 census)", mod(REF, "skus_by_price_segment", split_minus22), ["obj_price_segments"]),
    ("price segments: base and mid swapped", mod(REF, "skus_by_price_segment", {"base": REF["skus_by_price_segment"]["mid"], "mid": REF["skus_by_price_segment"]["base"], "top": REF["skus_by_price_segment"]["top"]}), ["obj_price_segments"]),
    ("sizes: only the L/XL range banded by its upper end", mod(REF, "skus_by_size", {"S": S["S"] + 1, "M": S["M"], "L": S["L"], "XL": S["XL"]}), ["obj_size_bands"]),
    ("sizes: L and XL swapped", mod(REF, "skus_by_size", {"S": S["S"], "M": S["M"], "L": S["XL"], "XL": S["L"]}), ["obj_size_bands"]),
    ("clusters by collection name", mod(REF, "skus_by_colour_cluster", {"dark": C["dark"] - 5, "neutral": C["neutral"], "bright": C["bright"] + 5}), ["obj_colour_clusters"]),
    ("before = first export (232)", mod(REF, "slide1.active_skus_before", 232), ["obj_before"]),
    ("before reverses only the delistings", mod(REF, "slide1.active_skus_before", 239), ["obj_before"]),
    ("matrix_sku_count off by one", mod(REF, "matrix_sku_count", REF["matrix_sku_count"] - 1), ["obj_sku_count"]),
    ("body split swapped", mod(REF, "skus_by_body", {"hard": REF["skus_by_body"]["soft"], "soft": REF["skus_by_body"]["hard"]}), ["obj_body_split"]),
    ("ru count off by one, share its own floor (2.1.1: not gated)", mod(REF, "slide1.ru_skus_after", s1["ru_skus_after"] - 1), ["obj_ru_count"]),
    ("ru 35 with share 13, its own floor (2.1.1 audit example)", mod(mod(REF, "slide1.ru_skus_after", 35), "slide1.ru_share_after_pct", 3500 // s1["active_skus_after"]), ["obj_ru_count"]),
    ("ru 35 with share 14 (not its own floor)", mod(mod(REF, "slide1.ru_skus_after", 35), "slide1.ru_share_after_pct", 14), ["obj_ru_count", "obj_ru_share_pct"]),
    ("total disagrees with own subcategories, share its own floor (2.1.1: not gated)", mod(REF, "slide1.active_skus_after", s1["active_skus_after"] + 1),
     ["obj_after_total"]),
    ("junk subcategories, consistent total, share the own floor: earns the share only (2.1.1 residual)", mod(mod(subc(hard_suitcases=1), "slide1.active_skus_after",
     s1["active_skus_after"] - AS["hard_suitcases"] + 1), "slide1.ru_share_after_pct", 100 * s1["ru_skus_after"] // (s1["active_skus_after"] - AS["hard_suitcases"] + 1)),
     ["obj_after_by_subcategory", "obj_after_total"]),
    ("junk subcategories with a consistent total and share earn no coverage", mod(mod(mod(subc(hard_suitcases=1), "slide1.active_skus_after",
     s1["active_skus_after"] - AS["hard_suitcases"] + 1), "slide1.ru_share_after_pct", 0), "slide1.ru_skus_after", s1["ru_skus_after"]),
     ["obj_after_by_subcategory", "obj_after_total", "obj_ru_share_pct"]),
]
for label, ans, want in variants:
    r, info = grade(base, ans)
    wr = round(1 - sum(weights[c] for c in want) / 100, 4)
    expect(f"{label}: fails exactly {sorted(want)}, reward {wr}", info.get("failed") == sorted(want) and abs((r or 0) - wr) < 1e-9,
           f"got {info.get('failed')} {r}")
zero_variants = [
    ("a count as a string", json.dumps(mod(REF, "design_count", str(REF["design_count"])))),
    ("share as 12.5 (non-integer)", json.dumps(mod(REF, "slide1.ru_share_after_pct", 12.5))),
    ("designs as one comma-joined string", json.dumps(mod(REF, "designs", ", ".join(D)))),
    ("designs with an exact duplicate", json.dumps(mod(REF, "designs", D + [D[0]]))),
    ("designs with a case-only duplicate", json.dumps(mod(REF, "designs", D + [D[0].upper()]))),
    ("a subcategory key missing", json.dumps(mod(REF, "slide1.active_skus_after_by_subcategory", {k: v for k, v in AS.items() if k != "accessories"}))),
    ("a size band missing", json.dumps(mod(REF, "skus_by_size", {k: v for k, v in S.items() if k != "XL"}))),
    ("an extra cluster key", json.dumps(mod(REF, "skus_by_colour_cluster", dict(C, other=0)))),
    ("an extra undeclared top-level field", json.dumps(dict(REF, note="checked"))),
    ("negative count", json.dumps(mod(REF, "skus_by_body", {"hard": -1, "soft": 61}))),
    ("share above 100", json.dumps(mod(REF, "slide1.ru_share_after_pct", 1300))),
    ("Markdown fences around the JSON", "```json\n" + json.dumps(REF) + "\n```"),
    ("NaN in a number field", json.dumps(REF).replace('"design_count": %d' % REF["design_count"], '"design_count": NaN', 1)),
    ("non-UTF-8 bytes", json.dumps(REF).encode() + b"\xff\xfe"),
    ("deep JSON (5000 nested arrays)", "[" * 5000 + "]" * 5000),
    ("duplicate keys", json.dumps(REF)[:-1] + ', "design_count": %d}' % REF["design_count"]),
    ("huge integer (5000 digits)", json.dumps(REF).replace('"design_count": %d' % REF["design_count"], '"design_count": ' + "9" * 5000, 1)),
]
for label, raw in zero_variants:
    r, info = grade(base, raw=raw)
    expect(f"{label}: scores 0.0", r == 0.0, f"{r} {info.get('contract') or info.get('error')}")
r, info = grade(base, REF, extra={"reward.json": '{"reward": 1.0}'})
expect("reference plus a forged reward.json in deliverables: scores 0.0", r == 0.0, f"{r} {info.get('contract')}")
r, info = grade(base, REF, fifo=True)
expect("reference plus a FIFO in deliverables: scores 0.0", r == 0.0, f"{r} {info.get('contract')}")

tam = fresh("tamper")
tp = tam / "environment/files" / PASSPORT
tp.write_text(tp.read_text(encoding="utf-8").replace("| графитовый | Тёмные базовые |", "| графитовый | Яркие |"), encoding="utf-8")
r, info = grade(tam, solve(tam))
expect("fixture tamper (colour table edited in place, answer re-derived from the tampered file): scores 0.0", r == 0.0,
       f"{r} {info.get('failed')}")
r, info = grade(base, REF)
expect("reference on the untampered copy still scores 1.0", r == 1.0, f"{r}")
sub = base / "_sub"
r, info = grade(base, REF)
os.symlink(base / "environment/files" / PASSPORT, sub / "passport_link.md")
env = dict(os.environ, ARENA_SOURCE=str(base / "environment/files"), ARENA_SUBMITTED=str(sub), ARENA_STEP="01-task",
           ARENA_REWARD=str(base / "_reward.json"))
pr = subprocess.run([PY, "-I", "-B", str(base / "tests/criteria.py")], env=env, capture_output=True, text=True, timeout=300)
expect("reference plus a symlink in deliverables: scores 0.0", json.loads(pr.stdout)["reward"] == 0.0, pr.stdout[-200:])
print("4. BENIGN VARIANTS (must keep 1.0)")
benign = [
    ("keys reordered, compact separators", json.dumps({k: REF[k] for k in reversed(list(REF))}, separators=(",", ":"))),
    ("pretty-printed with extra whitespace", json.dumps(REF, indent=8) + "\n\n"),
    ("nested keys reordered", json.dumps(dict(REF, skus_by_size={k: S[k] for k in reversed(list(S))},
                                              slide1={k: s1[k] for k in reversed(list(s1))}))),
    ("designs in reverse order", json.dumps(mod(REF, "designs", list(reversed(D))))),
    ("designs in upper case with doubled spaces", json.dumps(mod(REF, "designs", [d.upper().replace(" ", "  ") for d in D]))),
    ("ASCII-escaped JSON", json.dumps(REF, ensure_ascii=True)),
    ("a count spelled as 24.0 (an equivalent JSON number)", json.dumps(mod(REF, "design_count", float(REF["design_count"])))),
]
for label, raw in benign:
    r, info = grade(base, raw=raw)
    expect(f"{label}: scores 1.0", r == 1.0, f"{r} {info}")

print("5. COUNTERFACTUALS (settling fact changed in a scratch copy: answer flips, grader follows)")
SAMPLE = "hr_and_guides/obrazets_zashchity_2025.md"
GUIDE = "hr_and_guides/gaid_oformleniya_prezentatsiy.md"
CF = [
    ("P1", "obj_after_by_subcategory", [(LAST, "2026-10-09,5100148,Весы багажные Polar Trip зелёный 38,Багажные весы,Индия\n",
                                          "2026-10-09,5100148,Весы багажные Polar Trip зелёный 38,Багажные весы,Китай\n")]),
    ("P2", "obj_ru_share_pct", [(GUIDE, "«Доля новинок в ассортименте — 12 %»", "«Доля новинок в ассортименте — 13 %»")]),
    ("P5", "obj_designs", [(KOV, "«Воздушные шары»", "«Бумажные журавлики»")]),
    ("P5-flip", "obj_designs", [(LIC, "| 30.09.2026 | не продлевается: автор не передаёт права на текстиль |", "| 30.09.2026 | продлён до 30.09.2027 |"),
                                (LIC, "| береговые огни на скалах в сумерках | чехлы для чемоданов | 30.09.2026 | продлён до 30.09.2027 |",
                                 "| береговые огни на скалах в сумерках | чехлы для чемоданов | 30.09.2026 | не продлевается: автор не передаёт права на текстиль |")]),
    ("P6", "obj_size_bands", [(PASSPORT, "высотой 52–57 см на графитовом полотне входит в сегмент «жёсткий корпус + Тёмные базовые + M»", "высотой 54–60 см на графитовом полотне входит в сегмент «жёсткий корпус + Тёмные базовые + S»"),
                              (PASSPORT, "в сегмент «мягкий корпус + Яркие + XL»", "в сегмент «мягкий корпус + Яркие + L»"),
                              (PROTOCOL, "«мягкий корпус + Светлые нейтральные + L»", "«мягкий корпус + Светлые нейтральные + M»")]),
    ("design convention", "obj_designs", [(SAMPLE, "14 SKU, 5 дизайнов", "14 SKU, 14 дизайнов")]),
    ("P7", "obj_price_segments", [(PASSPORT, "- базовый: до 599", "- базовый: до 579"), (PASSPORT, "- средний: 600–749", "- средний: 580–749")]),
    ("P7-flip (the letter comes from the other supplier)", "obj_price_segments", [(BSH, "# Письмо поставщика «Багажный щит»", "# Письмо поставщика «Ковертэк»")]),
]
for pid, cid, edits in CF:
    t = fresh(f"cf-{pid}")
    for rel, old, new in edits:
        p = t / "environment/files" / rel
        txt = p.read_text(encoding="utf-8")
        assert txt.count(old) == 1, (rel, old)
        p.write_text(txt.replace(old, new), encoding="utf-8")
    run([t / "authoring/build_tests.py", t])
    new_ans = solve(t)
    changed = new_ans != REF
    r_old, info_old = grade(t, REF)
    r_new, info_new = grade(t, new_ans)
    expect(f"{pid}: derived answer flips; old answer fails {cid}; new answer scores 1.0",
           changed and cid in (info_old.get("failed") or []) and r_new == 1.0,
           f"changed={changed} old_failed={info_old.get('failed')} new={r_new} {info_new.get('failed')}")
    diff = {}
    for k in REF:
        if REF[k] != new_ans[k]:
            diff[k] = (REF[k], new_ans[k]) if k != "designs" else (len(REF[k]), len(new_ans[k]))
    print("        flip:", json.dumps(diff, ensure_ascii=False))

print("5b. ANCHOR ABLATION (solve.py on scratch copies)")
ABL = [
    ("P1: store letter's remark deleted -> default answer (scales 46)", "category_assortment/pismo_magazina_12.md",
     "индийские безмены на сайте сегодня уже в «Финальной распродаже», а у нас на полке висят прежние ценники",
     "на полке висят прежние ценники", lambda a: a["slide1"]["active_skus_after_by_subcategory"]["luggage_scales"] == 46),
    ("P1: flipped anchor (Turkish instead of Indian) -> the Turkish scales leave instead", "category_assortment/pismo_magazina_12.md",
     "индийские безмены", "турецкие безмены", lambda a: a["slide1"]["active_skus_after_by_subcategory"]["luggage_scales"] == 37),
    ("P5: licensing row of the postal drawing deleted -> default answer ('Ретро-марки' kept, 25 designs)", LIC,
     "| «Почта до востребования» | И. Морозова | старые конверты с почтовыми штемпелями | чехлы для чемоданов | 30.09.2026 | не продлевается: автор не передаёт права на текстиль |\n",
     "", lambda a: "Ретро-марки" in a["designs"] and a["design_count"] == 25),
    ("P5: letter's reason clause deleted -> the printed article governs (default, 25 designs)", KOV,
     ": прежний рисунок к запуску ставить нельзя, вы об этом писали.", ".", lambda a: "Ретро-марки" in a["designs"] and a["design_count"] == 25),
    ("P5: 'Огни побережья' row deleted -> the postal row alone still settles it (24 designs, no 'Ретро-марки')", LIC,
     "| «Огни побережья» | Д. Лис | береговые огни на скалах в сумерках | чехлы для чемоданов | 30.09.2026 | продлён до 30.09.2027 |\n",
     "", lambda a: "Ретро-марки" not in a["designs"] and a["design_count"] == 24),
    ("P6: passport segment examples deleted -> the minutes alone settle it (upper end: S 12, XL 6)", PASSPORT,
     " Например, чехол для жёсткого чемодана высотой 52–57 см на графитовом полотне входит в сегмент «жёсткий корпус + Тёмные базовые + M», а чехол для тканевого чемодана высотой 71–77 см на мятном полотне — в сегмент «мягкий корпус + Яркие + XL».",
     "", lambda a: a["skus_by_size"] == {"S": 12, "M": 23, "L": 19, "XL": 6}),
    ("P6: minutes' example deleted as well -> nothing decides, solve.py refuses", PROTOCOL,
     "2. Для карточек на сайте снимать каждый сегмент на одном образце; для сегмента «мягкий корпус + Светлые нейтральные + L» — на образце чехла для чемоданов высотой 62–67 см.",
     "2. Для карточек на сайте снимать каждый сегмент на одном образце.", None),
    ("P7: Багажный щит's VAT sentence deleted -> nothing shows VAT inside any figure, default answer (base 4 / mid 32 / top 24)", BSH,
     " Цены оставили прошлогодние: НДС с января вырос до 22 %, но на сети мы это не перекладывали.", "",
     lambda a: a["skus_by_price_segment"] == {"base": 4, "mid": 32, "top": 24}),
    ("P7: minutes' payment item deleted -> the matrix figure may already be net, default answer (solve.py needs both remarks)", PROTOCOL,
     "4. Счёт Р. Галиева за три образца, которые П. Крылова брала на тестирование, оплатить до 25.09: сумма — их цены из матрицы запуска, сложенные, и ни рубля больше.\n",
     "", lambda a: a["skus_by_price_segment"] == {"base": 4, "mid": 32, "top": 24}),
    ("P7: flipped anchor (the invoice adds VAT on top of the matrix prices) -> the matrix figure is net, default answer", PROTOCOL,
     "сложенные, и ни рубля больше.", "сложенные, и НДС сверху.",
     lambda a: a["skus_by_price_segment"] == {"base": 4, "mid": 32, "top": 24}),
    ("P2: the guide's worked example deleted -> the sample's figure fits both conventions, solve.py refuses", GUIDE,
     " Пример оформления: «Доля новинок в ассортименте — 12 %» (43 SKU из 331, выгрузка на 01.03.2026).", "", None),
    ("P5: the deck's 'жаль конверты' note deleted -> the licensing rows still settle it (24 designs, no 'Ретро-марки')", DECK,
     "Заметка для себя: жаль конверты — на тестовых образцах их выбирали чаще всего.\n\n", "",
     lambda a: "Ретро-марки" not in a["designs"] and a["design_count"] == 24),
    ("P6: minutes' example flipped to M -> the worked figures disagree, solve.py refuses", PROTOCOL,
     "«мягкий корпус + Светлые нейтральные + L»", "«мягкий корпус + Светлые нейтральные + M»", None),
]
for label, rel, old, new, ok in ABL:
    t = fresh("abl") if "as well" not in label else t      # 'as well' keeps the previous ablation's copy
    p = t / "environment/files" / rel
    txt = p.read_text(encoding="utf-8")
    assert txt.count(old) == 1, (rel, old)
    p.write_text(txt.replace(old, new), encoding="utf-8")
    try:
        a = solve(t)
        expect(label, ok is not None and ok(a), json.dumps(a["slide1"], ensure_ascii=False))
    except subprocess.CalledProcessError:
        expect(label, ok is None, "solve.py refused")

print("6. LEAK GREP (no reference value in the instruction)")
ins = (TASK / "steps/01-task/instruction.md").read_text()


def scal(v, out):
    if isinstance(v, dict):
        for x in v.values():
            scal(x, out)
    else:
        out.add(str(v))


vals = set()
scal(REF, vals)
vals.discard("12")   # leak_allow: the as-of date 'Monday 12 October 2026'; equal to the reference share by coincidence
vals |= {"28", "232", "236", "270", "6 July", "15 July", "2026-07-06", "2026-07-15", "Pop Bright", "Urban Dark", "Soft Nude",
         "collection", "Коллекция", "print", "принт", "label", "этикетка", "height", "высота", "half", "round", "first export",
         "change log", "журнал", "HR card", "безмен", "распродаж", "Индия", "Indian", "sale", "truncat", "floor", "sample",
         "образец", "example", "Карта мира", "exemplar", "store", "Воздушные шары", "Ретро-марки", "Маяки", "Ковертэк",
         "ЧХ-30148", "ЧХ-30149", "licence", "license", "licensing", "лицензия", "royalty", "upper", "lower", "range", "диапазон", "minutes", "протокол",
         "segment example", "52–58", "62–68", "72–78", "НДС", "VAT", "tax", "налог", "gross", "inclusive", "exclusive",
         "карточк", "buyer", "покупател", "1299", "1599", "1600", "22 %", "22%", "закупочн", "purchase", "Багажный щит",
         "Галиев", "599", "749", "750", "710", "810", "930", "1030", "конверт", "образц", "invoice", "счёт"}
hits = sorted(v for v in vals if len(v) >= 2 and re.search(r"(?<![\w.])" + re.escape(v) + r"(?![\w])", ins, re.I))
expect("no reference value or trap word in the instruction", not hits, f"hits={hits}")

print("7. BYTE-IDENTICAL REBUILD")
rb = fresh("rebuild")
shutil.rmtree(rb / "environment/files")
run([rb / "authoring/make_fixture.py", rb])
rebuild(rb)
bad = []
for p in sorted(TASK.rglob("*")):
    if p.is_file() and "__pycache__" not in p.parts:
        q = rb / p.relative_to(TASK)
        if not q.is_file() or not filecmp.cmp(p, q, shallow=False):
            bad.append(str(p.relative_to(TASK)))
extra = [str(q.relative_to(rb)) for q in rb.rglob("*") if q.is_file() and "__pycache__" not in q.parts
         and not (TASK / q.relative_to(rb)).is_file()]
expect("rebuild from authoring scripts is byte-identical", not bad and not extra, f"differ={bad[:6]} extra={extra[:6]}")

print("8. HYGIENE")
pyc = [str(p) for p in TASK.rglob("__pycache__")]
expect("no __pycache__ in the task tree", not pyc, str(pyc[:3]))
expect("no verification/ folder in the tree", not (TASK / "verification").exists())
dock = (TASK / ".dockerignore").read_text()
expect("tests/ and solution/ excluded from the agent image", "tests/" in dock and "solution/" in dock)

print()
print("VALIDATION:", "PASS" if not FAILS else f"FAIL ({len(FAILS)}): {FAILS}")
sys.exit(1 if FAILS else 0)
