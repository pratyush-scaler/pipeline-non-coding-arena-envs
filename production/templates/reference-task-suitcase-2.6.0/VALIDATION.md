# VALIDATION - a_f1_suitcase-cover-matrix-check 2.6.0 (batch 6, B6v6 proven templates, single step)

Built 2026-10-15 in `envs-b6/_v6/` from `_v5b` 2.3.0. One version. Every result below was executed with the verifier's
cpython 3.11 on `mktemp -d` copies (`authoring/validate_output.txt`, `authoring/design_lint_output.txt`,
`authoring/selftest_output.txt`). **Not measured:** no model run, blind reader or `harbor check` of 2.6.0. Every miss rate
is a design aim. No `verification/` receipt is carried.

## Traps (three decisive, three templates, three families; no shared check, no cascade)

| trap | template | family | check | weight | documents | default wrong answer | aim (Fable / Astra) |
|---|---|---|---|---|---|---|---|
| P7 | T3 tax-inclusive | quantity semantics | obj_price_segments | 24 | passport §2 + §8, matrix price column, Багажный щит's letter, minutes item 4 | every printed figure banded: 4 / 32 / 24 (truth 8 / 36 / 16) | 50-70 % / 10-30 % |
| P5 | T1 keying slip | identity | obj_designs | 21 | Ковертэк's letter, licensing list, deck note, matrix names | 'Ретро-марки' kept, 25 designs (truth 24) | 40-60 % / 50-80 % |
| P2 | T2 one-figure convention | convention from worked figures | obj_ru_share_pct | 17 | presentation guide (rule + its one example); sample defence (non-discriminating) | 13 % (nearest), truth 12 % on own counts | 40-70 % / 80-100 % |
| P1 | filler | scope | obj_after_by_subcategory | 5 | store letter, memo, README | scales 46 | 0/10 both in 2.1.1 |
| P6 | filler | convention | obj_size_bands | 5 | passport §4 + §6, minutes item 2 | lower-end bands | 0/10 both in 2.1.1 |

Families stay apart by file: P7's anchors are in Багажный щит's letter and minutes item 4; P5's in Ковертэк's letter, the
licensing list and the deck; P2's in the guide. The minutes also hold P6's filler example (a different family). Coverage
28 points; free share (coverage + P1 + P6) 0.38. Additivity: design_lint runs all 32 misreading subsets, each fails
exactly its own checks with the exact partial reward (validate 2 runs the decisive trio: 0.38).

## P7 (T3, rebuilt): the price segment of each cover

Template source: gst 1.7.0 P3. Ingredients copied: the governing rule is silent on the basis of the record's figures
(section 8 bands by "закупочной цене", bounds in plain "руб."); the governing concept fixes the basis of the bounds
(section 2: the purchase price is the price the chain pays the supplier, without VAT); the normal records already sit on
that basis (Ковертэк's figures); ONE supplier's figures carry VAT, shown only by remarks about that supplier's prices.

- Anchor 1, the supplier's own record (Багажный щит's letter of 10.09, whose job is confirming it can sew its part of
  the matrix and sending test samples): `Цены оставили прошлогодние: НДС с января вырос до 22 %, но на сети мы это не
  перекладывали.` A VAT rise that the supplier "has not passed on" while its prices stay the same is possible only if the
  VAT is inside its prices (if VAT were on top, the rise would reach the invoice by law). Gives the rate.
- Anchor 2, a different party's record about that supplier's figures (minutes of 21.09, item 4, whose job is approving a
  payment): `Счёт Р. Галиева за три образца, ... оплатить до 25.09: сумма — их цены из матрицы запуска, сложенные, и ни
  рубля больше.` The invoice of a VAT payer contains its VAT; its total is the matrix figures and nothing more, so the
  matrix figures of his covers are the VAT-inclusive amounts. Галиев is tied to Багажный щит only by the letter's
  sender line.
- Impossibility that reverses the record: if Polina had keyed Galiev's figures without VAT, an invoice of exactly those
  figures would carry no VAT, which a supplier who says VAT is inside its prices cannot issue.
- Truth: Багажный щит's 19 figures 710 / 810 / 930 / 1030 are 582 / 664 / 762 / 844 without VAT -> base 8 / mid 36 /
  top 16. Ковертэк's 41 figures are banded as printed.
- No sentence gives the matrix figure priority; no caption next to the bounds; neither anchor contains `Цена закупки`,
  an article, a print, a matrix figure, 'с НДС' or 'включ'; neither reads as a correction (one is a supplier's covering
  note, the other a payment approval).

Uniqueness check / census of plausible wrong answers (validate 3, executed; each loses ONLY obj_price_segments, 0.76):
| reading | split | defeated by |
|---|---|---|
| every printed figure is the passport's net purchase price (default) | 4 / 32 / 24 | anchor 1 + anchor 2 (the invoice equals the matrix figures and carries VAT inside) |
| VAT taken out of every row, both suppliers | 36 / 17 / 7 | nothing shows VAT inside Ковертэк's figures; section 2's definition is the column's basis unless a record shows otherwise |
| everything put on a VAT-inclusive basis (Ковертэк grossed up) | 0 / 21 / 39 | section 2: the bounds are on the purchase price without VAT |
| 22 % of the gross taken off Багажный щит's figures (×0.78) | 8 / 42 / 10 | arithmetic: VAT inside a gross figure is 22/122 of it, not 22/100 |
| Багажный щит stripped at 20 % (old rate) | 8 / 36 / 16 | same as the reference (validate 3 asserts it): not a wrong reading |

Anchor ablation (validate 5b, executed): delete anchor 1 -> default 4 / 32 / 24; delete anchor 2 -> default (the matrix
figure may already have been keyed net; solve.py requires both); flip anchor 2 (`…сложенные, и НДС сверху.`) -> default
(the figures are net). Counterfactuals (validate 5, executed): bounds moved to 579/580 -> reference 4 / 40 / 16, old answer
fails, grader follows; the letter re-headed as Ковертэк's -> reference 32 / 13 / 15, grader follows (the grader reads the
letter's supplier and rate at grade time; the basis reading is frozen like P5's subject table).

§5/§7 self-check: a careful agent that reads every file but never asks "does this supplier's figure include VAT?" gets
it wrong (yes); the instruction asks only for "the matrix's SKUs per price segment of the passport" (validate 6 greps
НДС, VAT, закупочн, purchase, Багажный щит, Галиев, the bounds and the figures out of it); the misread deliverable is
complete (sums to 60, every segment used; validate 2b). `grep Цена закупки` does not reach either anchor.

Cold self-check (files/ + instruction.md only): derivable from section 2 + the two remarks, as above. Strongest
counter-reading: "the column is called Цена закупки, and section 2 says a purchase price is without VAT, so the figures
are net". It is a definition of the concept, not a statement about what Polina keyed; the minutes show what her figures
for that supplier are (the amount invoiced, VAT inside). Ковертэк's rows stay as printed because no record shows
otherwise. No text supports a fourth reading.

## P5 (T1): dial

Unchanged slip and grader. 2.6.0 = 2.3.0's dated licensing line plus 2.4.0's deck note `Заметка для себя: жаль конверты —
на тестовых образцах их выбирали чаще всего.` (measured with that pair: 2.4.0 F 4/5, 2.5.0 F 2/5). The note names the
drawing by description only (no ЧХ-, no 'Ретро-марки', no 'Почта'), sits in Polina's own deck, read for its figures, and
is not corrective, exclusive, a pointer or binding. Ablation (validate 5b): deleting it leaves 24 designs (the licensing
rows still settle it); deleting the postal licensing row or the letter's reason clause gives the default 25.

## P2 (T2): one discriminating figure

The guide's rule says only `целым числом`. Exactly one worked figure discriminates: the guide's own example, 43 of 331 =
12.99 % shown as `12 %` (truncation 12, nearest 13). Last year's sample defence now reads `17 % (45 из 262)` = 17.18 %:
17 under both conventions (2.1.1-2.5.0: 47 of 262 = 17.94 % shown as 17, a second discriminating figure, which is what
Astra cited in 2.1.1: "Both company examples truncate"). No precedent clause, no "see the example", no method name in the
fixture (grep for округл / отбрас: none). Graded on the solver's own counts: 34 of 264 = 12.88 % and 34 of 270 = 12.59 %
both give 12 under truncation and 13 under rounding (validate 2 and 3). Ablation: deleting the guide's example leaves
only the non-discriminating sample, and solve.py refuses (validate 5b). Counterfactual: the guide's example written `13 %`
flips the reference to 13 and the grader follows (validate 5).

## Gates (2.6.0)

- `b6ctl.py check`: DESIGN GATE PASS (additivity over 32 subsets, leaks none of 45 values); SELFTEST 9 ok, 0 BAD.
- `authoring/validate.py`: PASS, exit 0 (reference 1.0, empty 0.0, misreadings, census, counterfactuals, ablations,
  leak grep, byte-identical rebuild, hygiene).
- No `__pycache__`, no `verification/`.

---

# History (2.3.0 and earlier, as written; P7's and P2's sections below describe 2.3.0, not this tree)

## VALIDATION - a_f1_suitcase-cover-matrix-check 2.3.0 (variant B; A is 2.2.0) (batch 6, B6v5 stochastic tune, single step)

THIS TREE IS VARIANT B (`envs-b6/_v5b/`): its P5 dial line is the B sentence below; everything else equals the live tree (A, 2.2.0).

Tuned 2026-10-15 from the shipped 2.1.1 (frozen at `envs-b6/_versions/a_f1_suitcase-cover-matrix-check-2.1.1`).
Variant A is this tree (2.2.0); variant B is `envs-b6/_v5b/a_f1_suitcase-cover-matrix-check` (2.3.0). They differ only in
P5's dial sentence (`authoring/DIAL.md`). Every result below was executed with the verifier's cpython 3.11 on `mktemp -d`
copies; outputs are in `authoring/design_lint_output.txt`, `authoring/selftest_output.txt`, `authoring/validate_output.txt`.

**Not yet measured:** any model run of 2.2.0 or 2.3.0 (no pilot, no 10x2, no blind reader, no `harbor check`). Every miss
rate below for P5 and P7 is a design aim. The 2.1.1 harbor receipt (`verification/`) was removed from the live tree: it
certifies 2.1.1, a byte-identical copy stays in `_versions/…-2.1.1/verification/`, and validate section 8 requires the
working tree to carry none.

## Measured on 2.1.1 (final 10x2) and what changed

| premise | check | 2.1.1 weight | 2.1.1 missed (Fable / Astra) | 2.2.0 / 2.3.0 |
|---|---|---|---|---|
| P1 STORE (scope/population) | obj_after_by_subcategory | 8 | 0/10 / 0/10 | unchanged; 5 points (free) |
| P2 EXEMPLAR (convention from worked figures) | obj_ru_share_pct | 18 | 3/10 / 0/10 | unchanged; 17 points (decisive) |
| P5 TWIN keying slip (identity) | obj_designs | 24 | 9/10 / 9/10 | dialled DOWN (one routine process line, A vs B); 21 points (decisive) |
| P6 EXEMPLAR (convention from worked figures) | obj_size_bands | 20 | 0/10 / 0/10 | unchanged; 5 points (free) |
| P7 SCALE (quantity semantics; lead family) | obj_price_segments | - | new | 24 points (decisive) |

Decisive traps 24 + 21 + 17 = 62 points, three families (quantity semantics, identity, convention from worked figures),
three document sets (P7: passport section 8, approval minutes, e-commerce memo, matrix price column; P5: Ковертэк's letter,
licensing list, matrix names; P2: presentation guide, sample defence), no shared check, no cascade (validate section 2:
every subset of the five misreadings fails exactly its own checks with the exact partial reward; design_lint runs all 32).
Coverage 28 points; expected free share (coverage + P1 + P6) 0.38.

## P7 (new): the price segment of each cover

- Governing text (passport section 8): `Ценовой сегмент чехла определяется по его цене. Границы сегментов, руб. без НДС
  (ставка 22 %):` with `базовый: до 1299`, `средний: 1300–1599`, `верхний: от 1600`. The basis of the bounds sits only in
  the caption over them.
- The matrix's price column is a bare `Цена (руб)` (1290 / 1490 / 1690 / 1890 / 2090, by body and size label).
- Anchor 1 (approval minutes, item 3, e-commerce's minute-taker; doing the job of assigning the card texts): `тексты
  карточек готовит П. Крылова, цены на карточки ставим из матрицы запуска.` The site cards' prices ARE the matrix prices.
- Anchor 2 (e-commerce memo, a bullet about where promo codes apply): `Цена на карточке товара — та, которую покупатель
  платит при оформлении заказа; промокоды и баллы списываются уже в корзине.` A card's price is the buyer's price, which
  in Russian retail includes VAT.
- Therefore every matrix price includes VAT; without it (÷1.22) the prices are 1057 / 1221 / 1385 / 1549 / 1713, giving
  base 21 / mid 36 / top 3. At 20 % (a reader who ignores the stated 22 %) the split is the same (1075 / 1242 / 1408 /
  1575 / 1742); the nearest bound is 50 roubles away.
- Default technique: band `int(row['Цена (руб)'])` against the bounds: base 4 / mid 17 / top 39. Complete, sums to 60,
  every segment used (validate 2b): nothing to reconcile.

Uniqueness check (which reading fails which anchor):
| reading | split | defeated by |
|---|---|---|
| matrix price is already without VAT | 4 / 17 / 39 | anchor 1 + anchor 2: the card shows the matrix price and the buyer pays the card price; a buyer's price carries VAT |
| matrix price is the supplier's (purchase) price | open | anchor 1: the site's cards show the matrix price to buyers; no supplier quotes it (the Ковертэк letter no longer mentions price) |
| VAT added on top of the matrix price | 0 / 4 / 56 | the caption asks for prices without VAT; adding VAT moves away from that basis |
| stripped VAT at 20 % | 21 / 36 / 3 | same answer (not a wrong reading) |

Anchor ablation (validate 5b, executed): delete anchor 1 (the minutes' clause) -> solve.py gives the default 4 / 17 / 39
(the matrix price's basis is open); delete anchor 2 (the memo bullet) -> the default (solve.py requires both; a reader
with retail knowledge may still settle it from anchor 1 alone, since a card's price is a buyer's price); flip anchor 1
("…ставим из матрицы запуска, прибавив к ним НДС.") -> the default (the printed price is then the net price). Delete both
-> the default. Counterfactual (validate 5): moving the base/mid bound to 1199/1200 flips the reference to 4 / 53 / 3 and
the grader follows.

§5/§7 self-check: a careful agent that reads every file but never asks "is the matrix price with or without VAT?" gets
it wrong (yes); the instruction field reads only "the matrix's SKUs per price segment of the passport" (no VAT, no basis
word; validate 6 greps НДС, VAT, tax, карточк, покупател, the bounds and 22 % out of the instruction); neither anchor reads
as a correction (each does another job: who prepares the card texts; where promo codes apply). Lexically disjoint: neither
anchor contains `Цена (руб)`, an article, a print or a figure; no figure the agent can divide (lesson 4).

Cold self-check (files/ + instruction.md only): derivable — yes, as above. Another defensible answer? The strongest is
"the passport and the matrix are Polina's planning files, so the matrix price is net"; it is defeated because the minutes
put the matrix prices on the site cards unchanged and the memo says the card price is what the buyer pays. No text
supports the net reading.

## P5 dial (identity, both models 9/10 -> target 30-60%)

Unchanged from 2.1.1: the letter's slip (ЧХ-30148, a Маяки cover), the licensing rows, the grader. Added (A): the
licensing list's last line `Если договор на рисунок не продлевается, отдел сообщает об этом категории, а замену рисунка
категория согласует с поставщиком сама.` (B: `Категориям, у которых договор на рисунок не продлевается, отдел сообщил об
этом 25.09; замену рисунка категория согласует с поставщиком сама.`). It names no drawing, print, article or category, and
does not read as a correction. It gives one more route from the letter's "прежний рисунок к запуску ставить нельзя, вы об
этом писали" to the licence lapse: the swap is the category's replacement of a lapsed drawing, and the only lapsed cover
drawing is the postal one ('Ретро-марки', ЧХ-30149). Uniqueness: the article reading keeps a drawing whose licence is
renewed ('Огни побережья') out of the launch and leaves the lapsed postal drawing on sale, contradicting the letter's own
reason and the licensing list; nothing supports it except the printed article. Ablation: deleting the dial line returns
2.1.1 (still determined by the letter's reason clause and the two licensing rows; validate 5b's P5 ablations are
unchanged and pass); deleting the postal row or the reason clause gives the default (25 designs).

## Census of plausible wrong answers (addendum lesson 5; validate section 3, executed)

| trap | plausible wrong answer | defensible from the files? | checks lost |
|---|---|---|---|
| P7 | 4 / 17 / 39 (printed price) | no (anchors 1+2) | obj_price_segments only |
| P7 | 0 / 4 / 56 (VAT added) | no | obj_price_segments only |
| P7 | base and mid swapped | no | obj_price_segments only |
| P5 | 25 designs, 'Ретро-марки' kept (+ 'Воздушные шары') | no | obj_designs only (design_count is graded on the own list) |
| P5 | the 24 matrix prints, letter ignored | no | obj_designs only |
| P5 | 'Ретро-марки' dropped, 'Воздушные шары' missing | no | obj_designs only |
| P5 | swap applied to both ЧХ-30148 and ЧХ-30149 | gives the reference set (Маяки kept by ЧХ-30147) | none |
| P2 | 13 (nearest whole percent of 34/264) | no (two worked figures cut down) | obj_ru_share_pct only |
| P2 | 12 on 34/270 (P1 missed) | graded on own counts | obj_after_by_subcategory only |

## Results (2.3.0, this tree; filled from this tree's own gate run)

- `b6ctl.py check`: DESIGN GATE PASS (5 premises; premises 72 %, coverage 28 %; additivity over 32 misreading subsets;
  leaks: none of 45 reference values in the instruction); SELFTEST 9 ok, 0 BAD; no `__pycache__`. Warnings: P1 and P6
  carry 5 % each (intended: measured free).
- `authoring/validate.py`: VALIDATION: PASS (exit 0).

The sections below are the 2.1.1 record, kept as written.

# (history) VALIDATION - a_f1_suitcase-cover-matrix-check 2.1.1 (batch 6, B6v4 signal tune, single step)

Tuned 2026-10-14 from 2.0.0 (archived at `envs-b6/_versions/a_f1_suitcase-cover-matrix-check-2.0.0`; 1.0.0 is archived
beside it). Seed b6-S15, trace 01a05ff6-41dc-7dd3-a31d-5d0954aa41e5. Python for every run: the verifier's cpython 3.11
(`python3.11 -I -B`). Every result below was executed on `mktemp -d` copies. Outputs are kept verbatim in
`authoring/design_lint_output.txt`, `authoring/selftest_output.txt` and `authoring/validate_output.txt`.

**Not yet measured:** any model run of 2.1.0 (no pilot, no 10x2, no blind reader, no `harbor check`). Every miss rate
below for P5 and P6 is a design aim.

## 2.1.1 patch (2026-10-14, grader only)

2.1.0 is archived at `envs-b6/_versions/a_f1_suitcase-cover-matrix-check-2.1.0`.

- **Audit finding.** `obj_ru_share_pct` carried `requires: [obj_ru_count, obj_after_total]`, but the instruction says the
  share is "graded against your own ru_skus_after and active_skus_after". So a share that was the correct floor of the
  solver's own counts lost its 18 points whenever an upstream count was wrong. Example: ru 35 with share 13 scored 0.77.
- **Change.** The `requires` is removed in `authoring/make_checks.py`, and the check's weight_basis text now says the
  check is not gated. The stale reward.toml comment in `build_tests.py` is corrected, and `task.toml` is bumped to 2.1.1
  with its P2 sentence updated. The authoring scripts were re-run (make_fixture, make_checks, make_contract,
  build_tests). Against 2.1.0, only `tests/checks.json` (the `requires` and weight_basis) and `tests/reward.toml` (the
  comment) differ. `environment/` and `instruction.md` are byte-identical, and solve.py is unchanged.
- **Gates.**
  - `design_lint.py`: DESIGN GATE: PASS, with additivity 16/16.
  - `selftest.py`: no BAD.
  - `validate.py`: VALIDATION: PASS, exit 0, 90 ok lines, and the rebuild is byte-identical.
  - The outputs were refreshed in `authoring/*_output.txt`.
  - validate section 3 now expects these variants to keep the share check: "ru off by one", "total disagrees with own
    subcategories", "scales left, total not updated" and "Indian accessory removed".
  - Three variants were added: ru 35 with share 13 (fails only obj_ru_count, 0.95), ru 35 with share 14 (fails ru and
    share, 0.77), and junk subcategories with an own-floor share (0.87).
- **grade_dir.py.**
  - The reference scores 1.0.
  - ru 35 with share 13 now fails only `obj_ru_count` (0.95; 2.1.0 gave 0.77).
- **Re-grade of the 20 final deliverables** (`pipeline-artifacts/b4/...-2.1.0-final-{fable,astra}`). Every score is
  unchanged and matches the recorded verifier reward: Fable 5 x 0.76 and 5 x 0.58, Astra 10 x 0.76. The gate never fired
  in a model run.
- **Trade-off (disclosed).**
  - P2 credit no longer proves the population was right. On counts where floor and half-up agree (e.g. 35/264 =
    13.26), a solver that rounds also passes P2.
  - Self-consistent junk counts with an own-floor share now earn the share's 18 points (REWARD-HACKING.md).

## Why 2.1.0 (2.0.0 pilot, 5x2)

| premise | Fable misses | Astra misses |
|---|---|---|
| P1 STORE (scales in the sale section) | 0/5 | 0/5 |
| P2 EXEMPLAR (whole-percent truncation) | 4/5 | 0/5 |
| P3 EXEMPLAR (design = print) | 0/5 | 0/5 |
| P4 STATED (size by suitcase height) | 0/5 | 0/5 |

Fable pass@1 0.2, Astra 1.0 (FLAT, distinct 1); free share 0.82. A blind Opus reader confirmed 2.0.0 genuine. Astra is the
easy model. The signal brief (TUNE-BRIEF-B6v4-signal.md) asked to keep P2 untouched and replace two never-missed premises
with two independent bites: a clean §12 keying slip (Astra misses those) and one bite of a different family.

How the replaced premises were solved in 2.0.0 (pilot transcripts):
- P3: Astra `package__Z6TmwVn` step 10: "For covers, I'm counting designs by print name and assigning sizes by suitcase
  height, as the passport requires"; every Fable run computed `r['Название позиции'].split(' / ')[0]`.
- P4: every Fable run wrote `band(h)` with `lo, hi = ...; assert b(lo) == b(hi)` and banded by the height column. The
  ranges never crossed a grid edge, so the assert never fired.

## What changed from 2.0.0

- **Kept byte-identical:** every file P1 and P2 use (memo, store letter, README, both exports, change log, guide, sample
  defence), the deck, the mentor's note, the HR card, the instruction, P2's check object and P2's traps.json entry.
  P1's check changed weight only (22 -> 8).
- **P3 removed as a premise.** Counting designs by print (last year's sample) stays as base knowledge inside P5's check.
- **P4 removed.** The three label/height shifts are gone: every non-crossing range now agrees with its label.
- **P5 TWIN keying slip (new), on `designs`.**
  - `subcategory_covers/pismo_kovertek_2026-10-06.md`: the supplier's routine letter; item 2 swaps "прежний рисунок" for
    the catalogue print «Воздушные шары» and files the swap under ЧХ-30148, a Маяки cover.
  - `licensing/litsenzii_na_risunki_2026-10-01.md`: the licensing department's royalty sheet. It names drawings by
    contract title and subject only: the postal drawing (old envelopes with postmarks) is not renewed; the coastal-lights
    drawing is renewed.
  - Passport section 2 now reads "Дизайн — рисунок (принт) на полотне, с которым чехол поступит в продажу." This states the
    rule on the real fact (§12), so the matrix file's working name does not bind.
- **P6 EXEMPLAR (new), on `skus_by_size`.**
  - Three matrix ranges now cross a grid edge: ЧХ-30150 52–58 (label S), ЧХ-30134 62–68 (label M), ЧХ-30153 72–78
    (label L).
  - Passport section 6 gains two segment examples: 52–57 cm in M, 71–77 cm in XL.
  - `subcategory_covers/protokol_soglasovaniya_2026-09-21.md`: the minutes of the passport's approval meeting; the photo
    plan puts a 62–67 cm cover in L.
- **Weights:** P1 8, P2 18, P5 24, P6 20; coverage 30 (sku 3, design_count 3, body 4, clusters 4, before 6, after_total 5,
  ru 5). Biting premises P2 + P5 + P6 = 62%. Expected free share: coverage 30 + P1 8 = 38%.

## Deliverable and reference

`/app/deliverables/cover_matrix_check.json`. The reference values, derived by `steps/01-task/solution/solve.py`, are:
- `matrix_sku_count` 60;
- `designs`: 24 = the 24 prints with «Ретро-марки» replaced by «Воздушные шары»;
- `design_count` 24;
- `skus_by_body`: hard 38, soft 22;
- `skus_by_colour_cluster`: dark 23, neutral 17, bright 20;
- `skus_by_size`: S 12, M 23, L 19, XL 6;
- `slide1`: before 236; after by subcategory 44 / 47 / 46 / 44 / 40 / 43; after 264; ru 34; share 12.

No field asks for errors, mismatches or corrections; every field is an outcome figure (§5.1).

## Premise table (schema b6/premises/2)

| id | mechanism / family | check (share) | aimed at, target miss | resolving quote | anchors (file) | default technique | misreading |
|---|---|---|---|---|---|---|---|
| P1 | STORE / population_reshaped | obj_after_by_subcategory (8%) | Astra; measured 0/10 | memo: "«Финальная распродажа» — ... только товары, вывод которых из ассортимента уже вступил в силу ..." | store letter, README glossary, README file-date line (unchanged) | latest export, `Counter(Подкатегория)` | scales 46, total 270 |
| P2 | EXEMPLAR / house_convention_numeric | obj_ru_share_pct (18%) | both; measured F 4/5, A 0/5 | guide example "12 %" (43 из 331) | guide rule 5; sample "17 % (47 из 262)" (unchanged) | `round()` to the nearest | 13 |
| P5 | TWIN / governing_vs_filing_key | obj_designs (24%) | Astra (and Fable), 0.5 | passport: "Дизайн — рисунок (принт) на полотне, с которым чехол поступит в продажу." | letter: "прежний рисунок к запуску ставить нельзя, вы об этом писали"; licensing: «Почта до востребования» ... "старые конверты с почтовыми штемпелями" ... "не продлевается"; licensing: «Огни побережья» ... "береговые огни на скалах в сумерках" ... "продлён до 30.09.2027" | apply the swap by the printed article (`design['ЧХ-30148'] = 'Воздушные шары'`), print-before-slash for the rest | 25 designs: 'Ретро-марки' kept, 'Воздушные шары' added |
| P6 | EXEMPLAR / precedent_rule | obj_size_bands (20%) | both, 0.4 | passport sec. 4: "Размер чехла в сегментации определяется по высоте чемодана, на который рассчитан чехол, по сетке категории:" | passport sec. 6 segment examples (52–57 -> M, 71–77 -> XL); minutes (62–67 -> L) | band by the lower end, or `Counter(label)` | S 13 / M 23 / L 19 / XL 5 (= labels = the deck) |

**Mix (design_lint):** 4 hard mechanisms (STORE, EXEMPLAR, TWIN, EXEMPLAR); Fable-type 2 (EXEMPLAR x2); Astra-type 4;
no STATED, no CLOCK; four distinct families.

**Interlock:** exactly one reciprocal pair, P1 <-> P2, unchanged from 2.0.0. P5 and P6 are independent of P2 and of each
other: different evidence files (letter + licensing sheet vs passport section 6 + minutes), different checks, no gate or
cascade. design_lint's 16-subset additivity confirms it.

**Salience knobs:**
- P5: name the drawing's subject in the letter (more), or drop the «Огни побережья» row so only the positive
  identification remains (less).
- P6: add a fourth example in the grid section (more), or drop the minutes' example (less).

## Uniqueness check (P6 exemplars; §9.4)

| worked figure | lower end | midpoint | upper end | larger part of the range |
|---|---|---|---|---|
| 52–57 cm -> M (passport §6) | 52 -> S ✗ | 54.5 -> S ✗ | 57 -> M ✓ | 52–55 S ✗ |
| 71–77 cm -> XL (passport §6) | 71 -> L ✗ | 74 -> L ✗ | 77 -> XL ✓ | 71–75 L ✗ |
| 62–67 cm -> L (minutes) | 62 -> M ✗ | 64.5 -> M ✗ | 67 -> L ✓ | 62–65 M ✗ |

Only the upper end reproduces all three. solve.py enumerates lower, middle and upper and asserts exactly one fits; the
grader reads the three figures at grade time.

**§9 recipe:**
- The rule leaves the dimension open without contradicting it: "по высоте чемодана, на который рассчитан чехол".
- The worked figures sit in the governing passport and in the approval minutes of the same office, under the current
  edition (21.09.2026).
- No pointer: no precedent clause, no "see the examples". The examples illustrate segments, and the minutes plan a photo
  shoot.

## P5 identity (keying slip, §10 and §12 recipe)

- **The slip fits its wrong key.** ЧХ-30148 is a Ковертэк cover. "Полотно, размер и цена — прежние" fits it, and
  Маяки keeps ЧХ-30147, so the default join leaves nothing unmatched, no empty print and no duplicate.
- **By-the-way anchors that name the drawing by paraphrase.** The licensing sheet is a royalty forecast. Its subjects
  ("старые конверты с почтовыми штемпелями", "береговые огни на скалах в сумерках") share no token with any article or
  matrix name.
- **The graded field is a downstream consequence**, not the slipped row's own content: the set of designs the matrix
  carries.
- **The wrong owner's default disposition is sanctioned:** a cover that keeps its print.
- **No source contradicts the true identity.** The only dated note on either cover is the letter itself.

## Counter-readings (strongest per new premise, and the text that defeats it)

**P5. "The letter names ЧХ-30148, so the Маяки XL cover gets the balloons."**
- Defeated by the letter's own reason, "прежний рисунок к запуску ставить нельзя", together with the licensing sheet. The
  coastal-lights drawing (Маяки) is renewed, so it can be used. The drawing that cannot be used is the postal one, and
  'Ретро-марки' is the matrix's only postal print, on one cover (ЧХ-30149).
- Second counter-reading: "both changed: Маяки XL by the letter, Ретро-марки replaced by something unknown." The letter
  describes one swap of a drawing that cannot be used, and the only such drawing is the postal one. Even under this
  reading 'Ретро-марки' leaves the list (its licence is not renewed) and 'Воздушные шары' joins it. The graded set is the
  same, because Маяки keeps ЧХ-30147.
- Third counter-reading: "list the designs as the matrix file prints them." Defeated by the passport term, which is now
  scoped to "the drawing the cover goes on sale with", and by the licence: the author grants no textile rights.

**P6. "A cover for 52–58 cm suitcases is an S cover; the supplier labels it S."**
- Defeated by passport section 4 (size by suitcase height, not by label) and the three worked figures (table above).
- Second counter-reading: "take the midpoint." Fails all three figures.

## Anchor ablation (§6), executed in validate 5 / 5b

| premise | delete one anchor | flip an anchor | delete both |
|---|---|---|---|
| P5 | Postal licensing row deleted: the default results ('Ретро-марки' kept, 25 designs). Letter's reason clause deleted: the printed article governs (default, 25). «Огни побережья» row deleted: the postal row alone still settles it (24, no 'Ретро-марки'). | Licence statuses swapped (postal renewed, coastal lights not renewed): the letter's article then carries the unusable drawing, the reference flips to 25 with 'Ретро-марки', and the grader follows (counterfactual "P5-flip"). New print renamed in the letter: the designs flip and the grader follows. | default: 25 designs |
| P6 | Passport examples deleted: the minutes alone settle it (upper end: S 12, XL 6). | All three figures rewritten to lower-end bands (54–60 -> S, 71–77 -> L, 62–67 -> M): the reference flips to S 13 / XL 5 and the grader follows. Minutes alone flipped to M: the figures disagree and solve.py refuses. | passport examples and minutes example deleted: nothing decides, solve.py refuses; a reader is left with the open rule |

## §5 self-check

| premise | careful reader who never asks the hidden question gets it wrong? | does the instruction or a field name make it ask? | does any anchor read as a correction? |
|---|---|---|---|
| P5 | yes: applies the letter by its article; the licence sheet is a royalty list nobody joins | no: "the distinct designs in that matrix" | no: a reason clause in a production letter, and licence statuses |
| P6 | partly: a solver that bands by one end never sees the question. A solver that checks both ends (every Fable 2.0.0 run asserted `band(lo) == band(hi)`) does see it and must find the worked figures | no: "the matrix's SKUs per size band of the passport's size grid" | no: a segmentation illustration and a photo plan |

## §7: no anomaly under the default; semantic, lexically disjoint anchors

**Misread consistency check:** executed in validate 2b on the ARENA_MISREAD=P1,P2,P5,P6 deliverable; all six lines are ok.
- `design_count` equals `len(designs)`.
- Every misread design is a matrix print or the letter's new print, and every matrix print is listed: nothing is stray
  or unmatched.
- The size split sums to 60 and equals both the supplier-label split and the deck's "S — 13 · M — 23 · L — 19 · XL — 5".
- The cluster and body splits sum to 60.
- The after total equals the subcategory sum, which equals the 9 October export's 270 rows.
- The share is a plausible whole percent.

**Grep proof** (over `environment/files`, executed):

```
ЧХ-30149 -> matritsa_chekhly_zapusk.csv          Ретро-марки -> matritsa_chekhly_zapusk.csv
ЧХ-30148 -> matritsa_chekhly_zapusk.csv, pismo_kovertek_2026-10-06.md (the slipped key itself)
Маяки    -> matritsa_chekhly_zapusk.csv
конверт | штемпел | береговые -> litsenzii_na_risunki_2026-10-01.md only
52–57 | 71–77 -> pasport_subkategorii_chekhly.md     62–67 -> protokol_soglasovaniya_2026-09-21.md
52–58 | 62–68 | 72–78 -> matritsa_chekhly_zapusk.csv only
```

No anchor can be reached from a record identifier, and no anchor is a value a script can join, hash or ratio.

**P6 caveat:** P6's ranges are visible to a two-ended parser. That makes P6 a deliberated EXEMPLAR, like P2: the solver
sees an open choice and must find the convention. It is not a silent sub-step.

## Results

- **`design_lint.py`:** DESIGN GATE: PASS.
  - map: 4 premises, 4 premise checks, 7 coverage checks;
  - weights: premises 70%, coverage 30%;
  - v2: mechanisms STORE, EXEMPLAR, TWIN, EXEMPLAR, with the P1 <-> P2 interlock reciprocal;
  - additivity: 16/16 subsets;
  - leaks: none of 42 reference values ("12" allowed: the as-of date, equal to the share and the S count by coincidence).
- **`fix261011/selftest.py`** on a mktemp copy: no BAD.
  - reference 1.0;
  - deep_json, deep_bounded, fifo_extra, fifo_declared, dup_case, huge_digits, long_spaces and long_digit_run all 0;
  - trailing_nl and dup_number `--` (not applicable).
- **`authoring/validate.py`:** VALIDATION: PASS, exit 0, 87 ok lines, 0 FAIL.
  - Reference 1.0; empty workspace 0.0.
  - Misreadings, each exact: P1 0.92, P2 0.82, P5 0.76, P6 0.80, P1+P2 0.74, P5+P6 0.56, all four 0.30.
  - §7.1 consistency: 6/6.
  - 24 rule-breaking variants each lose exactly their checks. They include 'Ретро-марки' kept, the new print omitted, the
    letter ignored, the 28 position names, sizes by label, and one crossing range banded alone.
  - 17 hostile or contract variants score 0; forged reward.json, FIFO, symlink and fixture tamper score 0.
  - 7 benign variants keep 1.0.
  - 6 counterfactuals flip and the grader follows: P1, P2, P5 (new print renamed), P5-flip (licence statuses swapped),
    P6 (figures to lower-end bands), and the sample's design total.
  - 8 anchor ablations as tabled (P1 2, P5 3, P6 3).
  - Leak grep clean; byte-identical rebuild from the authoring scripts; no `__pycache__`, no `verification/`.

## No second reading (changed fields)

| field | strongest competing reading | defeated by |
|---|---|---|
| designs | 25: the letter applied to ЧХ-30148 | the letter's reason plus the licensing sheet (P5) |
| designs | 24 matrix prints, letter ignored | passport term "с которым чехол поступит в продажу"; the licence grants no textile rights |
| designs naming | «Воздушные шары» with quotes, or a catalogue code | the letter spells the print one way; case and spacing are ignored |
| skus_by_size | supplier label / lower end / midpoint | passport section 4 plus the three worked figures (P6) |

The other fields are unchanged from 2.0.0 (see the archived VALIDATION.md).

## Uncertain / untested

- **No model has run 2.1.0.**
  - P6 may be solved more often than an undeliberated exemplar, because a two-ended parser trips on the crossing ranges
    (see the caveat above).
  - P5 depends on a solver not joining the royalty sheet to the letter. Astra missed every measured keying slip of this
    shape (kibo, probation, pathway 5/5), but this one is unmeasured.
- **Frozen readings in the grader.**
  - P5: the grader maps the licensing sheet's subject column to matrix prints with a literal table (конверт ->
    Ретро-марки, береговые огни -> Маяки, атлас -> Карта мира, небоскр -> Город). The grader requires exactly one lapsed
    cover drawing; a fixture with none would error, and that world is exercised through solve.py only (ablation).
  - P1 and P2: as in 2.0.0.
- **Attribution:** `designs` also requires counting designs by print (solved 10/10 in the 2.0.0 pilot). A 28-name answer
  fails P5's check without being a P5 miss; read the answer before attributing.
- **P1 is never-missed filler** (0/10 in 2.0.0), kept at 8% for its interlock with P2.
