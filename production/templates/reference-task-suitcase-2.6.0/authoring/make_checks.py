"""Generates tests/projections.json and tests/checks.json. Targets are expressions over tests/derived and the fixture."""
import json
import sys
from pathlib import Path

T = Path(sys.argv[1])
OUT = "cover_matrix_check.json"
MATRIX = "subcategory_covers/matritsa_chekhly_zapusk.csv"
PASSPORT = "subcategory_covers/pasport_subkategorii_chekhly.md"
KOV = "subcategory_covers/pismo_kovertek_2026-10-06.md"
PROTOCOL = "subcategory_covers/protokol_soglasovaniya_2026-09-21.md"
BSH = "subcategory_covers/pismo_bagazhnyy_shchit_2026-09-10.md"

projections = [
    {"as": "matrix.jsonl", "file": MATRIX, "parser": "csv_table"},
    {"as": "colours.jsonl", "file": PASSPORT, "parser": "markdown_tables"},
    {"as": "matrix_cluster.jsonl", "op": "join", "left": "matrix.jsonl", "right": "colours.jsonl", "on": "Цвет фона",
     "fields": {"article": "left.Артикул", "collection": "left.Коллекция", "cluster": "right.Кластер"}},
    {"as": "hr.jsonl", "file": "hr_and_guides/kartochka_stazhera.md", "parser": "labelled_lines"},
    {"as": "log.jsonl", "file": "category_assortment/zhurnal_izmeneniy_assortimenta_2026-10-09.csv", "parser": "csv_table"},
    {"as": "sample_tags.jsonl", "file": "hr_and_guides/obrazets_zashchity_2025.md", "parser": "markdown_tables"},
    {"as": "export_first.jsonl", "file": "category_assortment/aktivnyy_assortiment_2026-07-15.csv", "parser": "csv_table"},
    {"as": "export_last.jsonl", "file": "category_assortment/aktivnyy_assortiment_2026-10-09.csv", "parser": "csv_table"},
    {"as": "licences.jsonl", "file": "licensing/litsenzii_na_risunki_2026-10-01.md", "parser": "markdown_tables"},
]
(T / "tests" / "projections.json").write_text(json.dumps({"projections": projections}, ensure_ascii=False, indent=1) + "\n")


def lit(v, why):
    return {"op": "literal", "value": v, "why": why}


def F(p):
    return {"op": "field", "path": p}


def IF(where, then, else_):
    return {"op": "if", "where": where, "then": then, "else": else_}


def rows(f, where=None):
    e = {"op": "rows", "file": f}
    if where is not None:
        e["where"] = where
    return e


def derive(of, fields):
    return {"op": "derive_rows", "of": of, "fields": fields}


def bind(of, fields):
    return {"op": "bind_rows", "of": of, "fields": fields}


def pluck(field, of):
    return {"op": "pluck", "field": field, "of": of}


def filt(where, of):
    return {"op": "filter", "where": where, "of": of}


def only(x):
    return {"op": "only", "of": x}


def unique(x):
    return {"op": "unique", "of": x}


def extract(of, pattern, group=1):
    return {"op": "extract", "of": of, "pattern": pattern, "group": group}


def num(x):
    return {"op": "number", "of": x}


def cmp(a, b, kind, c):
    return {"op": "compare", "a": a, "b": b, "value_type": kind, "comparison": c}


def count(x):
    return {"op": "count", "of": x}


def record(fields):
    return {"op": "record", "fields": fields}


def actual(path):
    return {"op": "field", "file": OUT, "path": path}


passport = {"op": "text", "file": PASSPORT}
guide = {"op": "text", "file": "hr_and_guides/gaid_oformleniya_prezentatsiy.md"}
sample = {"op": "text", "file": "hr_and_guides/obrazets_zashchity_2025.md"}
TRUE = {"eq": True}
NAME = "Название позиции"
PRINT_RE = r"^(.+?) / "


def rnd(x, why_mode="half_up"):
    return {"op": "round", "mode": why_mode, "places": 0, "of": x}


def sub(a, b):
    return {"op": "subtract", "a": a, "b": b}


def mul(a, b):
    return {"op": "multiply", "a": a, "b": b}


def div(a, b):
    return {"op": "divide", "a": a, "b": b}


HALF = lit(0.5, "whole-percent truncation written as half-up rounding of the share minus one half")
HUNDRED = lit(100, "a percentage is a hundredfold share")

# ---------------------------------------------------------------- designs: one design is one print (last year's sample, as in 2.0.0)
sample_n = num(extract(sample, r"14 SKU, (\d+) дизайнов"))
sample_prints = count(unique(pluck("p", derive(rows("sample_tags.jsonl"), {"p": extract(F(NAME), PRINT_RE)}))))
design_is_print = cmp(sample_prints, sample_n, "number", "eq")

# ---------------------------------------------------------------- P5 (TWIN keying slip): the drawing each cover goes on sale with
# Ковертэк's letter swaps one cover's drawing for a catalogue print and files the swap under an article. The licensing list
# names the drawing that cannot be used by its contract title and subject only. The subject reading (конверт -> the matrix's
# postal print, береговые огни -> Маяки, ...) is frozen here, like P1's subcategory/country filter. The swap belongs to the
# lapsed drawing's cover unless the letter's own article already carries that drawing.
kov = {"op": "text", "file": KOV}
new_print = extract(kov, r"рисунок меняем на «([^»]+)»", 1)
named_article = extract(kov, r"По артикулу (ЧХ-\d+) рисунок меняем", 1)
WHY_SUBJ = "frozen reading of the licensing list's subject column: the contract names a drawing by title and subject, the matrix by its working print name"
lic = derive(rows("licences.jsonl"), {
    "print": IF({"field": "Что изображено", "matches": "конверт"}, lit("Ретро-марки", WHY_SUBJ),
                IF({"field": "Что изображено", "matches": "береговые огни"}, lit("Маяки", WHY_SUBJ),
                   IF({"field": "Что изображено", "matches": "атлас"}, lit("Карта мира", WHY_SUBJ),
                      IF({"field": "Что изображено", "matches": "небоскр"}, lit("Город", WHY_SUBJ),
                         lit("", "a listed drawing that no cover of the matrix carries"))))),
    "lapsed": IF({"all": [{"field": "Статус", "matches": "^не продлевается"},
                          {"field": "Где используется", "matches": "чехлы для чемоданов"}]},
                 lit(True, "a cover drawing whose licence is not renewed cannot go on sale"),
                 lit(False, "renewed or running licence"))})
lapsed_print = only(pluck("print", filt({"field": "lapsed", **TRUE}, lic)))
m1 = derive(bind(rows("matrix.jsonl"), {"design_is_print": design_is_print, "new_print": new_print,
                                         "named_article": named_article, "lapsed_print": lapsed_print}), {
    "name": F(NAME), "p": extract(F(NAME), PRINT_RE), "design_is_print": F("design_is_print"), "new_print": F("new_print"),
    "lapsed_print": F("lapsed_print"), "is_named": cmp(F("Артикул"), F("named_article"), "string", "eq")})
named_print = only(pluck("p", filt({"field": "is_named", **TRUE}, m1)))
m2 = derive(bind(m1, {"named_print": named_print}), {
    "name": F("name"), "p": F("p"), "design_is_print": F("design_is_print"), "new_print": F("new_print"), "is_named": F("is_named"),
    "is_lapsed": cmp(F("p"), F("lapsed_print"), "string", "eq"),
    "named_is_lapsed": cmp(F("named_print"), F("lapsed_print"), "string", "eq")})
designed = derive(m2, {"design": IF(
    {"any": [{"all": [{"field": "is_lapsed", **TRUE}, {"field": "named_is_lapsed", "eq": False}]},
             {"all": [{"field": "is_named", **TRUE}, {"field": "named_is_lapsed", **TRUE}]}]},
    F("new_print"), IF({"field": "design_is_print", **TRUE}, F("p"), F("name")))})
designs_target = unique(pluck("design", designed))

# ---------------------------------------------------------------- coverage: colour cluster by background colour (table 5.1, joined at build time)
cluster_target = record({k: count(rows("matrix_cluster.jsonl", {"field": "cluster", "eq": name}))
                         for k, name in (("dark", "Тёмные базовые"), ("neutral", "Светлые нейтральные"), ("bright", "Яркие"))})

# ---------------------------------------------------------------- P6 (EXEMPLAR): the band of a suitcase-height range (passport section 4)
# The grid gives single heights; the matrix gives ranges, three of which cross a grid edge. The passport's segment examples
# (section 6) and the approval minutes' photo plan are worked figures; the grader reads them at grade time and bands every
# range by its upper end if all three fit that reading, by its lower end otherwise.
protocol = {"op": "text", "file": PROTOCOL}
EX = {
    "e1": (passport, r"высотой (\d+)–(\d+) см на графитовом полотне входит в сегмент «[^»]+\+ (S|M|L|XL)»", (1, 2, 3)),
    "e2": (passport, r"высотой (\d+)–(\d+) см на мятном полотне — в сегмент «[^»]+\+ (S|M|L|XL)»", (1, 2, 3)),
    "e3": (protocol, r"для сегмента «[^»]+\+ (S|M|L|XL)» — на образце чехла для чемоданов высотой (\d+)–(\d+) см", (2, 3, 1)),
}
policy = {
    "s_hi": num(extract(passport, r"S \(ручная кладь\): высота чемодана до (\d+) см", 1)),
    "m_hi": num(extract(passport, r"M \(средний\): высота чемодана \d+–(\d+) см", 1)),
    "l_hi": num(extract(passport, r"L \(большой\): высота чемодана \d+–(\d+) см", 1)),
}
for k, (src, pat, (glo, ghi, gband)) in EX.items():
    policy[f"{k}_lo"] = num(extract(src, pat, glo))
    policy[f"{k}_hi"] = num(extract(src, pat, ghi))
    policy[f"{k}_band"] = extract(src, pat, gband)
HEIGHT_COL = "Высота чемодана (см)"
VALS = ["lo", "hi"] + [f"{k}_{e}" for k in EX for e in ("lo", "hi")]
keep = {name: F(name) for name in policy}
s1 = derive(bind(rows("matrix.jsonl"), policy), {
    **keep, "lo": {"op": "range_bound", "of": F(HEIGHT_COL), "bound": "lower"},
    "hi": {"op": "range_bound", "of": F(HEIGHT_COL), "bound": "upper"}})
s2 = derive(s1, {**{f"{k}_band": F(f"{k}_band") for k in EX},
                 **{f"{v}_{edge}": cmp(F(v), F(f"{edge}_hi"), "number", "lte") for v in VALS for edge in ("s", "m", "l")}})
s3 = derive(s2, {**{f"{k}_band": F(f"{k}_band") for k in EX},
                 **{f"b_{v}": IF({"field": f"{v}_s", **TRUE}, lit("S", "grid band S: up to the S edge"),
                                 IF({"field": f"{v}_m", **TRUE}, lit("M", "grid band M"),
                                    IF({"field": f"{v}_l", **TRUE}, lit("L", "grid band L"),
                                       lit("XL", "grid band XL: above the L edge")))) for v in VALS}})
s4 = derive(s3, {"b_lo": F("b_lo"), "b_hi": F("b_hi"),
                 **{f"up_{k}": cmp(F(f"b_{k}_hi"), F(f"{k}_band"), "string", "eq") for k in EX}})
banded = derive(s4, {"band": IF({"all": [{"field": f"up_{k}", **TRUE} for k in EX]}, F("b_hi"), F("b_lo"))})
size_target = record({b: count(filt({"field": "band", "eq": b}, banded)) for b in ("S", "M", "L", "XL")})

# ---------------------------------------------------------------- P7 (SCALE, quantity semantics; B6v6 template T3): the price segment of each cover
# Passport section 2 defines the purchase price without VAT; section 8 bands a cover by its purchase price. The matrix's
# purchase-price column holds Ковертэк's figures without VAT and Багажный щит's price-list figures as they stand. Its letter
# says its prices are last year's although VAT rose in January to the rate it names, and that it has not passed that on
# (the VAT is inside its prices); the minutes pay its sample invoice at exactly the matrix prices, nothing more (the matrix
# figure is what is paid). The grader takes the letter's supplier and rate at grade time and strips that rate from that
# supplier's rows only; the basis reading (that supplier's figures carry VAT) is frozen here, like P5's subject reading.
PRICE_COL = "Цена закупки (руб)"
bsh = {"op": "text", "file": BSH}
seg_policy = {
    "rate": num(extract(bsh, r"НДС с января вырос до (\d+) %", 1)),
    "incl_sup": extract(bsh, r"Письмо поставщика «([^»]+)»", 1),
    "base_hi": num(extract(passport, r"- базовый: до (\d+)", 1)),
    "mid_hi": num(extract(passport, r"- средний: \d+–(\d+)", 1)),
}
p0 = derive(bind(rows("matrix.jsonl"), seg_policy), {
    "base_hi": F("base_hi"), "mid_hi": F("mid_hi"), "rate": F("rate"), "price": num(F(PRICE_COL)),
    "incl": cmp(F("Поставщик"), F("incl_sup"), "string", "eq")})
p1 = derive(p0, {
    "base_hi": F("base_hi"), "mid_hi": F("mid_hi"),
    "net": IF({"field": "incl", **TRUE},
              div(mul(F("price"), HUNDRED), {"op": "add", "a": HUNDRED, "b": F("rate")}),
              F("price"))})
p2 = derive(p1, {"in_base": cmp(F("net"), F("base_hi"), "number", "lte"), "in_mid": cmp(F("net"), F("mid_hi"), "number", "lte")})
segged = derive(p2, {"seg": IF({"field": "in_base", **TRUE}, lit("base", "passport 8: базовый, up to its bound"),
                               IF({"field": "in_mid", **TRUE}, lit("mid", "passport 8: средний"),
                                  lit("top", "passport 8: верхний, above the средний bound")))})
seg_target = record({k: count(filt({"field": "seg", "eq": k}, segged)) for k in ("base", "mid", "top")})

# ---------------------------------------------------------------- coverage: 'before' = the category on the internship's first day
start = only(pluck("value", rows("hr.jsonl", {"field": "label", "eq": "Дата начала стажировки"})))
cut = only(unique(pluck("Дата выгрузки", rows("export_first.jsonl"))))
win = derive(bind(rows("log.jsonl"), {"start": start, "cut": cut}), {
    "act": F("Действие"), "ge": cmp(F("Дата"), F("start"), "date", "gte"), "lt": cmp(F("Дата"), F("cut"), "date", "lt")})


def in_window(action):
    return count(filt({"all": [{"field": "ge", **TRUE}, {"field": "lt", **TRUE}, {"field": "act", "eq": action}]}, win))


before_target = {"op": "subtract", "a": {"op": "add", "a": count(rows("export_first.jsonl")), "b": in_window("вывод")},
                 "b": in_window("ввод")}

# ---------------------------------------------------------------- P1 (STORE): the category now, per subcategory
# The 9 October export lists the luggage scales of the Indian supplier as active; the e-commerce memo admits to the site's
# 'Финальная распродажа' only SKUs whose delisting is in force, and store 12's letter of 10 October reports the Indian
# 'безмены' (README: Багажные весы = ручные безмены) there that morning. So they are no longer active now.
SUBS = {"hard_suitcases": "Чемоданы пластиковые", "soft_suitcases": "Чемоданы тканевые", "travel_bags": "Дорожные сумки",
        "backpacks": "Рюкзаки дорожные", "luggage_scales": "Багажные весы", "accessories": "Аксессуары для путешествий"}
SCALES, IN_SALE = "Багажные весы", "Индия"


def now_count(key):
    name = SUBS[key]
    if name == SCALES:
        return count(rows("export_last.jsonl", {"all": [{"field": "Подкатегория", "eq": name},
                                                        {"field": "Страна поставщика", "ne": IN_SALE}]}))
    return count(rows("export_last.jsonl", {"field": "Подкатегория", "eq": name}))


after_sub_target = record({k: now_count(k) for k in SUBS})
after_sub_actual = record({k: actual(f"slide1.active_skus_after_by_subcategory.{k}") for k in SUBS})


def total_of_own():
    keys = list(SUBS)
    e = actual(f"slide1.active_skus_after_by_subcategory.{keys[0]}")
    for k in keys[1:]:
        e = {"op": "add", "a": e, "b": actual(f"slide1.active_skus_after_by_subcategory.{k}")}
    return e


# coverage: the total is the solver's own six figures, and the five subcategories the premise does not touch are right
untouched = [k for k in SUBS if SUBS[k] != SCALES]
after_total_actual = record({"total_is_own_sum": cmp(actual("slide1.active_skus_after"), total_of_own(), "number", "eq"),
                             **{k: actual(f"slide1.active_skus_after_by_subcategory.{k}") for k in untouched}})
after_total_target = record({"total_is_own_sum": lit(True, "active_skus_after is the sum of the solver's own six figures"),
                             **{k: now_count(k) for k in untouched}})
ru_target = count(rows("export_last.jsonl", {"field": "Страна поставщика", "eq": "Россия"}))

# ---------------------------------------------------------------- P2 (EXEMPLAR): the whole-percent convention the guide's example evidences,
# applied to the solver's OWN counts (R18/R29). The guide's worked example decides truncation or half-up rounding.
# The submission side sees only the deliverable, the target side only the fixture: the actual is "the solver's share is
# its own share cut down to a whole percent", the target is "the guide's worked example shows a share cut down".
own_floor = rnd(sub(div(mul(HUNDRED, actual("slide1.ru_skus_after")), actual("slide1.active_skus_after")), HALF))
pct_actual = cmp(actual("slide1.ru_share_after_pct"), own_floor, "number", "eq")
g_floor = rnd(sub(div(mul(HUNDRED, num(extract(guide, r"\((\d+) SKU из \d+"))), num(extract(guide, r"SKU из (\d+),"))), HALF))
pct_target = cmp(g_floor, num(extract(guide, r"— (\d+) %» \(\d+ SKU из \d+")), "number", "eq")

B = {
    "sku": "matrix_sku_count: the number of SKUs in Polina's launch matrix for suitcase covers",
    "designs": "designs: the distinct designs in that matrix, one entry per design, each written as the design's name (any order)",
    "design_count": "design_count: the number of distinct designs in that matrix, i.e. the number of entries in designs",
    "body": "skus_by_body: the matrix's SKUs per suitcase body material of the passport: hard (жёсткий корпус) and soft (мягкий корпус)",
    "cluster": "skus_by_colour_cluster: the matrix's SKUs per colour cluster of the passport: dark (Тёмные базовые), neutral (Светлые нейтральные) and bright (Яркие)",
    "size": "skus_by_size: the matrix's SKUs per size band of the passport's size grid: S, M, L and XL",
    "price": "skus_by_price_segment: the matrix's SKUs per price segment of the passport: base (базовый), mid (средний) and top (верхний)",
    "before": "slide1.active_skus_before: the category's active SKUs as the category stood on Polina's first day of the internship",
    "after_sub": "slide1.active_skus_after_by_subcategory: the category's active SKUs as the category stands now, per subcategory",
    "after_total": "slide1.active_skus_after: the sum of the six active_skus_after_by_subcategory figures",
    "ru": "slide1.ru_skus_after: of the category's active SKUs now, those with Russia as their supplier country",
    "pct": "slide1.ru_share_after_pct: ru_skus_after as a percentage of active_skus_after, as it will appear on slide 1, graded against your own ru_skus_after and active_skus_after",
}


def check(cid, weight, basis, wb, assertion, act, target, band="core", dim="inference", requires=None):
    c = {"id": cid, "kind": "objective", "step": "01-task", "weight": weight, "band": band, "dimension": dim,
         "weight_basis": wb, "basis": basis, "assertion": assertion, "actual": act, "target": target}
    if requires:
        c["requires"] = requires
    return c


checks = [
    check("obj_after_by_subcategory", 5, B["after_sub"],
          "P1 STORE (population_reshaped): the 9 October export still lists the Indian supplier's luggage scales; the site's 'Финальная распродажа' admits only SKUs whose delisting is in force (e-commerce memo), and store 12 reports the Indian 'безмены' there on 10 October. They are not active now.",
          "equals", after_sub_actual, after_sub_target, band="stretch"),
    check("obj_ru_share_pct", 17, B["pct"],
          "P2 EXEMPLAR (house_convention_numeric; B6v6 template T2): the guide's worked example (43 of 331 shown as 12 %) is the one figure that shows whole percentages cut down, not rounded (last year's sample defence, 45 of 262 shown as 17 %, fits both); graded on the solver's own counts (R18/R29) and, since 2.1.1, not gated on them.",
          "equals", pct_actual, pct_target,
          band="stretch"),
    check("obj_designs", 21, B["designs"],
          "P5 TWIN keying slip (governing_vs_filing_key): Ковертэк's letter swaps the drawing that cannot be used for 'Воздушные шары' but files the swap under ЧХ-30148, a Маяки cover whose licence is renewed; the licensing list's lapsed drawing (old envelopes with postmarks) is the matrix's only 'Ретро-марки' cover, so the designs are the prints with 'Ретро-марки' replaced by 'Воздушные шары' (a design is the print, as last year's sample counts it).",
          "set_equals", actual("designs"), designs_target, band="stretch"),
    check("obj_size_bands", 5, B["size"],
          "P6 EXEMPLAR (precedent_rule): passport section 4 sizes a cover by the height of the suitcase it is made for; three matrix ranges cross a grid edge, and the passport's segment examples (52–57 cm in M, 71–77 cm in XL) and the approval minutes (62–67 cm in L) fit only the band of the upper end; the supplier's labels and the deck's split follow the lower end.",
          "equals", actual("skus_by_size"), size_target, band="stretch"),
    check("obj_price_segments", 24, B["price"],
          "P7 SCALE (wrong_figure_vs_derivation; quantity semantics; B6v6 template T3): passport section 2 defines the purchase price without VAT and section 8 bands a cover by it; Багажный щит's matrix figures carry VAT (its letter: last year's prices held through January's rise to 22 %, not passed on; the minutes: its sample invoice is paid at exactly the matrix prices, nothing more), so its rows are banded with the 22 % taken out, Ковертэк's as printed. Banding every printed figure gives base 4 / mid 32 / top 24.",
          "equals", actual("skus_by_price_segment"), seg_target, band="stretch"),
    check("obj_sku_count", 3, B["sku"], "Coverage: one row of the matrix file is one SKU (passport section 2).",
          "equals", actual("matrix_sku_count"), count(rows("matrix.jsonl")), band="floor", dim="execution"),
    check("obj_design_count", 3, B["design_count"], "Coverage: design_count equals the number of entries in the solver's own designs list.",
          "equals", cmp(actual("design_count"), count(actual("designs")), "number", "eq"),
          lit(True, "design_count is the length of the solver's own designs list"), band="floor", dim="execution"),
    check("obj_body_split", 4, B["body"], "Coverage: the matrix's body column, hard and soft.",
          "equals", actual("skus_by_body"),
          record({"hard": count(rows("matrix.jsonl", {"field": "Корпус чемодана", "eq": "жёсткий"})),
                  "soft": count(rows("matrix.jsonl", {"field": "Корпус чемодана", "eq": "мягкий"}))}),
          band="floor", dim="execution"),
    check("obj_colour_clusters", 4, B["cluster"], "Coverage: passport table 5.1 maps each background colour to its cluster.",
          "equals", actual("skus_by_colour_cluster"), cluster_target, band="floor", dim="execution"),
    check("obj_before", 6, B["before"],
          "Coverage: the 15 July export reversed through the change log back to the first day (6 July, HR card).",
          "equals", actual("slide1.active_skus_before"), before_target, band="floor", dim="execution"),
    check("obj_after_total", 4, B["after_total"],
          "Coverage: the total is the solver's own six figures, and the five subcategories P1 does not touch match the 9 October export.",
          "equals", after_total_actual, after_total_target, band="floor", dim="execution"),
    check("obj_ru_count", 4, B["ru"], "Coverage: Russian-supplier SKUs now (none of them is in the sale section).",
          "equals", actual("slide1.ru_skus_after"), ru_target, band="floor", dim="execution"),
    {"id": "g_fixture_intact", "kind": "guardrail", "step": "01-task", "weight": 0, "band": "floor", "dimension": "restraint",
     "basis": "Everything is in /app/environment/files (read-only); please don't change, move or delete anything there.",
     "assertion": "fixture_intact",
     "actual": lit(True, "fixture integrity is checked by the harness, not read from a deliverable"),
     "target": lit(True, "fixture integrity guard")},
]
assert sum(c["weight"] for c in checks) == 100
(T / "tests" / "checks.json").write_text(json.dumps({"checks": checks}, ensure_ascii=False, indent=1) + "\n")
print("checks", len(checks))
