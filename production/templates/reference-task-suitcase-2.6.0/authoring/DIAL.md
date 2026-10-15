# Dial sentences (B6v6 proven templates, 2.6.0, 2026-10-15)

Tree: `envs-b6/_v6/a_f1_suitcase-cover-matrix-check` (2.6.0, `DIAL = "v6"` in `authoring/make_fixture.py`), built from
`_v5b` 2.3.0. One version only; every sentence below is a dial the operator may turn after measurement. Everything not
listed is byte-identical to 2.3.0 except the P7 rebuild (section "Not dials").

## Measured history used

| trap | template | measured (missed runs) |
|---|---|---|
| P5 keying slip | T1 | 2.1.1 final F 9/10, A 9/10 (no dial line); 2.3.0 pilot F 4/5 (licensing line B); 2.4.0 pilot F 4/5, 2.5.0 pilot F 2/5 (B line + deck note) |
| P2 share convention | T2 (was two-figure §9) | 2.1.1 final F 3/10, A 0/10 (two discriminating figures; Astra's code comment: "Both company examples truncate: 43/331 -> 12%, 47/262 -> 17%"); 2.3.0 pilot F 1/5 |
| P7 price segment | T3 (rebuilt) | 2.3.0 (caption 'руб. без НДС' over the bounds) F 0/5; 2.4.0/2.5.0 (VAT behind a showcase figure) F 5/5 but blind reader missed too: INVALID, not reused |

## Dial sentences

| trap | file (environment/files/) | exact text in 2.6.0 | direction if measured too hard / too easy |
|---|---|---|---|
| P5 (T1, both) | defence/zashchita_slaydy_v5.md (after slide 7's speaker notes) | `Заметка для себя: жаль конверты — на тестовых образцах их выбирали чаще всего.` | too hard: keep, add a fourth by-the-way paraphrase elsewhere; too easy: delete it (2.3.0 setting, F 4/5) |
| P5 (T1, both) | licensing/litsenzii_na_risunki_2026-10-01.md (last line) | `Категориям, у которых договор на рисунок не продлевается, отдел сообщил об этом 25.09; замену рисунка категория согласует с поставщиком сама.` | too easy: replace by 2.2.0's undated A line or delete (2.1.1: 9/10) |
| P2 (T2, Astra) | hr_and_guides/obrazets_zashchity_2025.md | `- Доля SKU собственной торговой марки сейчас: 17 % (45 из 262)` | too hard (Fable): restore `(47 из 262)` (a second discriminating figure; measured Astra 0/10, so this flips Astra too). Never add a figure for Astra. Fable-only alternative: move the guide's example next to the slide 1 template (not available without editing the deck) |
| P7 (T3, Fable) | subcategory_covers/pismo_bagazhnyy_shchit_2026-09-10.md | `Цены оставили прошлогодние: НДС с января вырос до 22 %, но на сети мы это не перекладывали.` | required anchor (VAT inside the supplier's prices); not removable |
| P7 (T3, Fable) | subcategory_covers/protokol_soglasovaniya_2026-09-21.md (item 4) | `4. Счёт Р. Галиева за три образца, которые П. Крылова брала на тестирование, оплатить до 25.09: сумма — их цены из матрицы запуска, сложенные, и ни рубля больше.` | required anchor (the matrix figure is the amount paid); not removable |
| P7 (T3, Fable) | (none yet) | gst 1.7.0's third route, a counter-board remark, was NOT added: a chain buying at a supplier's showroom retail tags is implausible in Russian retail | too hard: add one more by-the-way remark on Galiev's figures in a third document (e.g. a delivery message: `Счёт — одной суммой, как и прайс`) |

## Not dials (the P7 rebuild, identical whatever the dial)

- `subcategory_covers/pasport_subkategorii_chekhly.md`: section 2 gains `- Закупочная цена — цена, по которой сеть покупает чехол у поставщика, без НДС.`; section 8 becomes `Ценовой сегмент чехла определяется по его закупочной цене. Границы сегментов, руб.:` with `базовый: до 599`, `средний: 600–749`, `верхний: от 750` (2.3.0's caption `руб. без НДС (ставка 22 %)` over the bounds is gone).
- `subcategory_covers/matritsa_chekhly_zapusk.csv`: column `Цена (руб)` becomes `Цена закупки (руб)`; Ковертэк rows carry purchase prices without VAT (soft 520/600/680/760 by S/M/L/XL, hard +80); Багажный щит rows carry its price-list figures with VAT inside (710 soft M and hard S; 810 soft L and hard M; 930 hard L; 1030 hard XL).
- `subcategory_covers/pismo_bagazhnyy_shchit_2026-09-10.md`: new file (the supplier confirms its part of the matrix and sends test samples).
- `subcategory_covers/protokol_soglasovaniya_2026-09-21.md`: item 3 loses 2.2.0's `, цены на карточки ставим из матрицы запуска`; item 4 (above) is new.
- `category_assortment/pamyatka_razdely_saita.md`: 2.2.0's card-price bullet is removed (byte-identical to 2.1.1 again).

## Templates not built, and why

- **T3 tax-inclusive on the whole matrix (2.2.0-2.5.0 shape):** a net basis stated next to the bounds announces the conversion (0/5); a basis hidden in non-governing documents was invalid. The rebuild follows gst P3 instead: the basis is a term definition, the normal figures already sit on it, and only one supplier's figures differ, shown by remarks about that supplier.
- **T4 (already in hand):** the deliverable has no order or purchase decision; nothing is "still needed".
- **T5 (misfiled note):** the task's one misfiled record is already P5's swap letter (filed under ЧХ-30148, about the postal drawing); a second would be the same mechanism as T1 in this task.
- **T6 (authority-parity temporal):** the only date-dependent figure is the first-day count, which rests on the HR card; any second source dating her start differently would set an informal remark against an official record (the measured invalid shape).

## Expected miss rates (unmeasured; design aims)

P7: Fable 50-70 %, Astra 10-30 %. P5: Fable 40-60 %, Astra 50-80 %. P2: Astra 80-100 %, Fable 40-70 %.
Implied pass@1: Fable about 0.05-0.15, Astra about 0.0-0.1. Free share 0.38 (coverage 28 + P1 5 + P6 5).
