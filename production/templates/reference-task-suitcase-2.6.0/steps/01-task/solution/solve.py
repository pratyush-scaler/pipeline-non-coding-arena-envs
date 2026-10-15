"""Reference solution: derives the numbers for Polina's defence deck from the files.

Nothing here is a stored answer. Every figure is recomputed from the fixture: the cover matrix, the subcategory
passport (design definition, size grid, segment examples, colour table), the approval minutes, Ковертэк's letter, the
licensing list, last year's sample defence, the presentation guide, the HR card, the assortment exports, the change log,
the category README, the e-commerce memo, store 12's letter and Багажный щит's letter.

ARENA_MISREAD="P1,P5" writes what a solver who misread exactly those premises would write:
  P1  takes 'now' straight from the latest export (9 October) and never connects store 12's 'индийские безмены ...
      в «Финальной распродаже»' with the memo's rule that the sale section holds only SKUs whose delisting is in force
  P2  rounds the Russian-supplier share to the nearest whole percent (halves up) instead of cutting it down to the
      whole percent, the convention the guide's worked example shows (last year's sample defence fits both)
  P5  applies Ковертэк's drawing swap to the article the letter prints (ЧХ-30148, a Маяки cover) instead of the cover
      whose drawing cannot be used (the licensing list's postal drawing, the matrix's 'Ретро-марки' cover), so
      'Ретро-марки' stays among the designs
  P6  bands a suitcase-height range by its lower end (what the supplier's label shows) instead of its upper end, the
      convention the passport's segment examples and the approval minutes show
  P7  bands each cover's printed purchase price by the passport's bounds, although the passport's purchase price is
      without VAT and Багажный щит's figures carry it (its letter: last year's prices held through January's VAT rise, not
      passed on; the minutes: its sample invoice is paid at exactly the matrix prices, nothing more)
Run with ARENA_SOURCE / ARENA_OUT to work on a copy.
"""
from __future__ import annotations

import csv
import io
import json
import os
import re
from fractions import Fraction
from pathlib import Path

SRC = Path(os.environ.get("ARENA_SOURCE", "/app/environment/files"))
OUT = Path(os.environ.get("ARENA_OUT", "/app/deliverables"))
MIS = {m.strip().upper() for m in os.environ.get("ARENA_MISREAD", "").split(",") if m.strip()}


def text(rel):
    return (SRC / rel).read_text(encoding="utf-8")


def table(rel):
    return list(csv.DictReader(io.StringIO(text(rel))))


def md_rows(doc):
    out = []
    for line in doc.splitlines():
        s = line.strip()
        if s.startswith("|") and not set(s) <= set("|- "):
            out.append([c.strip() for c in s.strip("|").split("|")])
    return out


matrix = table("subcategory_covers/matritsa_chekhly_zapusk.csv")
passport = text("subcategory_covers/pasport_subkategorii_chekhly.md")
guide = text("hr_and_guides/gaid_oformleniya_prezentatsiy.md")
sample = text("hr_and_guides/obrazets_zashchity_2025.md")
hr = text("hr_and_guides/kartochka_stazhera.md")
readme = text("category_assortment/README.md")
memo = text("category_assortment/pamyatka_razdely_saita.md")
letter = text("category_assortment/pismo_magazina_12.md")
exports = sorted((SRC / "category_assortment").glob("aktivnyy_assortiment_*.csv"))
logs = sorted((SRC / "category_assortment").glob("zhurnal_izmeneniy_assortimenta_*.csv"))
log = table(str(logs[-1].relative_to(SRC)))
NAME = "Название позиции"

# ---------------------------------------------------------------- matrix size and body (coverage)
sku_count = len(matrix)
body = {"hard": sum(r["Корпус чемодана"] == "жёсткий" for r in matrix),
        "soft": sum(r["Корпус чемодана"] == "мягкий" for r in matrix)}
assert body["hard"] + body["soft"] == sku_count


# ---------------------------------------------------------------- designs: one design is one print (last year's sample defence)
def print_of(name):
    return re.match(r"^(.+?) / ", name).group(1)


assert "Дизайн — рисунок (принт) на полотне, с которым чехол поступит в продажу." in passport
sample_n = int(re.search(r"(\d+) SKU, (\d+) дизайнов", sample).group(2))
sample_names = [r[1] for r in md_rows(sample) if re.fullmatch(r"БР-\d+", r[0])]
design_is_print = len({print_of(n) for n in sample_names}) == sample_n
assert design_is_print or len(set(sample_names)) == sample_n      # the sample must decide it

# ---------------------------------------------------------------- P5: the drawing each cover goes on sale with
# Ковертэк's letter swaps one cover's drawing, "прежний рисунок к запуску ставить нельзя", and files it under an article.
# The licensing list says which drawing cannot be used: a contract title and its subject, never a matrix name. The subject
# reading below (a frozen dictionary, like P1's adjective table) ties each listed drawing to the matrix's working print name.
kovertek = text("subcategory_covers/pismo_kovertek_2026-10-06.md")
licences = text("licensing/litsenzii_na_risunki_2026-10-01.md")
m = re.search(r"По артикулу (ЧХ-\d+) рисунок меняем на «([^»]+)»([^\n]*)", kovertek)
named_article, new_print = m.group(1), m.group(2)
unusable = "прежний рисунок к запуску ставить нельзя" in m.group(3)      # the swap replaces a drawing that cannot be used
SUBJECT = {"конверт": "Ретро-марки", "береговые огни": "Маяки", "атлас": "Карта мира", "небоскр": "Город"}
lapsed = set()
for row in md_rows(licences):
    if len(row) == 6 and "чехлы для чемоданов" in row[3] and row[5].startswith("не продлевается"):
        hit = {p for key, p in SUBJECT.items() if key in row[2]}
        assert len(hit) == 1, row
        lapsed |= hit
by_article = {r["Артикул"]: r for r in matrix}
named_print = print_of(by_article[named_article][NAME])
if unusable and lapsed and named_print not in lapsed:      # the letter's article is not the cover whose drawing cannot be used
    swapped = {r["Артикул"] for r in matrix if print_of(r[NAME]) in lapsed}
else:
    swapped = {named_article}
if "P5" in MIS:
    swapped = {named_article}


def design_of(r):
    if r["Артикул"] in swapped:
        return new_print
    return print_of(r[NAME]) if design_is_print else r[NAME]


designs = sorted({design_of(r) for r in matrix})

# ---------------------------------------------------------------- coverage: colour cluster by background colour (table 5.1)
cluster_of = {}
for line in passport.splitlines():
    m = re.fullmatch(r"\| (.+?) \| (Тёмные базовые|Светлые нейтральные|Яркие) \|", line.strip())
    if m:
        cluster_of[m.group(1)] = m.group(2)
KEY = {"Тёмные базовые": "dark", "Светлые нейтральные": "neutral", "Яркие": "bright"}
clusters = {"dark": 0, "neutral": 0, "bright": 0}
for r in matrix:
    clusters[KEY[cluster_of[r["Цвет фона"]]]] += 1

# ---------------------------------------------------------------- P6: the band of a suitcase-height range (passport section 4)
s_hi = int(re.search(r"S \(ручная кладь\): высота чемодана до (\d+) см", passport).group(1))
m_hi = int(re.search(r"M \(средний\): высота чемодана \d+–(\d+) см", passport).group(1))
l_hi = int(re.search(r"L \(большой\): высота чемодана \d+–(\d+) см", passport).group(1))


def grid(h):
    return "S" if h <= s_hi else "M" if h <= m_hi else "L" if h <= l_hi else "XL"


# Worked figures: the passport's segment examples (section 6) and the approval minutes' photo plan.
protocol = text("subcategory_covers/protokol_soglasovaniya_2026-09-21.md")
examples = [(int(a), int(b), c) for a, b, c in
            re.findall(r"высотой (\d+)–(\d+) см на [а-яё]+ полотне (?:входит|—) в сегмент «[^»]+\+ (S|M|L|XL)»", passport)]
examples += [(int(b), int(c), a) for a, b, c in
             re.findall(r"для сегмента «[^»]+\+ (S|M|L|XL)» — на образце чехла для чемоданов высотой (\d+)–(\d+) см", protocol)]
assert examples, examples
CONVENTIONS = {"lower": lambda lo, hi: grid(lo), "upper": lambda lo, hi: grid(hi),
               "middle": lambda lo, hi: grid(Fraction(lo + hi, 2))}
fits = [k for k, f in CONVENTIONS.items() if all(f(lo, hi) == b for lo, hi, b in examples)]
assert len(fits) == 1, (fits, examples)        # the worked figures must decide it
band_of = CONVENTIONS["lower" if "P6" in MIS else fits[0]]


def band(height):
    lo, hi = (int(x) for x in re.fullmatch(r"(\d+)–(\d+)", height).groups())
    return band_of(lo, hi)


sizes = {"S": 0, "M": 0, "L": 0, "XL": 0}
for r in matrix:
    sizes[band(r["Высота чемодана (см)"])] += 1

# ---------------------------------------------------------------- P7: the price segment of each cover (passport sections 2 and 8)
# Section 2: the purchase price is the price the chain pays a supplier, without VAT. Section 8 bands a cover by it. The
# matrix's purchase-price column is on that basis unless a supplier's own figures carry VAT: a supplier that kept last
# year's prices through January's VAT rise "and has not passed that on" has the VAT inside its prices, and the minutes pay
# that supplier's (contact's) sample invoice at exactly the matrix prices, nothing more, so its matrix figures are the
# VAT-inclusive amounts. Those rows are banded with the rate the letter names taken out.
protocol_text = protocol
assert "Закупочная цена — цена, по которой сеть покупает чехол у поставщика, без НДС." in passport
assert "Ценовой сегмент чехла определяется по его закупочной цене." in passport
base_hi = int(re.search(r"- базовый: до (\d+)", passport).group(1))
mid_lo, mid_hi = (int(x) for x in re.search(r"- средний: (\d+)–(\d+)", passport).groups())
top_lo = int(re.search(r"- верхний: от (\d+)", passport).group(1))
assert base_hi < mid_lo <= mid_hi < top_lo
paid_as_matrix = set(re.findall(r"Счёт ([А-ЯЁ]\. [А-ЯЁ][а-яё]+?)а за [^\n]*?: сумма — их цены из матрицы запуска, сложенные, "
                                r"и ни рубля больше\.", protocol_text))
gross = {}                       # supplier -> VAT rate inside its matrix figures
for path in sorted((SRC / "subcategory_covers").glob("pismo_*.md")):
    doc = path.read_text(encoding="utf-8")
    sup = re.search(r"^# Письмо поставщика «([^»]+)»", doc, re.M).group(1)
    sender = re.search(r"\*\*От:\*\* ([А-ЯЁ]\. [А-ЯЁ][а-яё]+)", doc).group(1)
    m = re.search(r"Цены оставили прошлогодние: НДС с января вырос до (\d+) %, но на сети мы это не перекладывали\.", doc)
    if m and sender in paid_as_matrix:
        gross[sup] = Fraction(int(m.group(1)), 100)
if "P7" in MIS:
    gross = {}
PRICE = "Цена закупки (руб)"


def segment(r):
    price = Fraction(int(r[PRICE]))
    net = price / (1 + gross[r["Поставщик"]]) if r["Поставщик"] in gross else price
    return "base" if net <= base_hi else "mid" if net <= mid_hi else "top"


segments = {"base": 0, "mid": 0, "top": 0}
for r in matrix:
    segments[segment(r)] += 1

# ---------------------------------------------------------------- coverage: 'before' = state on the internship's first day
start = re.search(r"Дата начала стажировки: (\d{4}-\d{2}-\d{2})", hr).group(1)
first = table(str(exports[0].relative_to(SRC)))
first_date = first[0]["Дата выгрузки"]
assert start < first_date
window = [e for e in log if start <= e["Дата"] < first_date]
before = len(first) + sum(e["Действие"] == "вывод" for e in window) - sum(e["Действие"] == "ввод" for e in window)

# ---------------------------------------------------------------- P1: the category now
last = table(str(exports[-1].relative_to(SRC)))
last_date = last[0]["Дата выгрузки"]
assert not [e for e in log if e["Дата"] > last_date]
# The memo: the sale section holds only SKUs whose delisting is already in force.
assert re.search(r"«Финальная распродажа» — раздел собирается автоматически: в него попадают только товары, вывод которых "
                 r"из ассортимента уже вступил в силу", memo)
# README: which subcategory a nickname names.
nick_to_sub = {}
for row in md_rows(readme):
    if len(row) == 2 and row[0] != "Подкатегория":
        for word in re.findall(r"[а-яё]+", row[1]):
            nick_to_sub.setdefault(word, row[0])
ADJ = {"индийск": "Индия", "китайск": "Китай", "турецк": "Турция", "российск": "Россия"}
d = re.search(r"(\d{2})\.(\d{2})\.(\d{4})", letter)
letter_iso = f"{d.group(3)}-{d.group(2)}-{d.group(1)}"
gone = set()
for adj, noun in re.findall(r"([а-яё]+)ие ([а-яё]+) на сайте сегодня уже в «Финальной распродаже»", letter):
    country, sub = ADJ[adj], nick_to_sub[noun]
    assert last_date < letter_iso <= "2026-10-12"      # in the section after the export was taken, before the as-of date
    gone |= {r["Артикул"] for r in last if r["Подкатегория"] == sub and r["Страна поставщика"] == country}
if "P1" in MIS:
    gone = set()
now = [r for r in last if r["Артикул"] not in gone]
SUBS = {"hard_suitcases": "Чемоданы пластиковые", "soft_suitcases": "Чемоданы тканевые", "travel_bags": "Дорожные сумки",
        "backpacks": "Рюкзаки дорожные", "luggage_scales": "Багажные весы", "accessories": "Аксессуары для путешествий"}
by_sub = {k: sum(r["Подкатегория"] == v for r in now) for k, v in SUBS.items()}
assert sum(by_sub.values()) == len(now)
after = len(now)
ru = sum(r["Страна поставщика"] == "Россия" for r in now)

# ---------------------------------------------------------------- P2: the whole-percent convention the exemplars show
shown_examples = [(int(a), int(b), int(c)) for a, b, c in re.findall(r"— (\d+) %» \((\d+) SKU из (\d+)", guide)]
shown_examples += [(int(a), int(b), int(c)) for a, b, c in re.findall(r"(\d+) % \((\d+) из (\d+)\)", sample)]
assert shown_examples


def floor_pct(n, d):
    return int(Fraction(100 * n, d))


def half_up_pct(n, d):
    s = Fraction(100 * n, d)
    return int(s) + (1 if s - int(s) >= Fraction(1, 2) else 0)


truncates = all(shown == floor_pct(n, d) for shown, n, d in shown_examples)
rounds = all(shown == half_up_pct(n, d) for shown, n, d in shown_examples)
assert truncates != rounds, shown_examples          # the worked figures must decide it (2.6.0: only the guide's does)
pct = floor_pct(ru, after) if truncates else half_up_pct(ru, after)
if "P2" in MIS:
    pct = half_up_pct(ru, after)

out = {
    "matrix_sku_count": sku_count,
    "designs": designs,
    "design_count": len(designs),
    "skus_by_body": body,
    "skus_by_colour_cluster": clusters,
    "skus_by_size": sizes,
    "skus_by_price_segment": segments,
    "slide1": {"active_skus_before": before, "active_skus_after_by_subcategory": by_sub, "active_skus_after": after,
               "ru_skus_after": ru, "ru_share_after_pct": pct},
}
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "cover_matrix_check.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
