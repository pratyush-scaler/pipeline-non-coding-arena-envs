# B9 author/tuner addendum (2026-10-16): measured on the first 3 x 2 pilots of batch b9

Applies on top of `AUTHOR-BRIEF-B8.md`; where they disagree, this addendum wins for b9 and later batches.
Evidence: `research/B9-PILOT-FORENSICS-20261016.md` (24 runs, 96 premise-runs over labour-code, repair-returns,
working-capital, maize; n = 3 per premise per model) plus six more easy pilots the same day (lab-procurement,
qa-evidence, script-claim, import-container, startup, laptop: 9 of 10 first builds measured easy, 0 finals bought).

**Status of the rules below.** The "solved" rules (what does NOT bite) are measured: treat them as hard constraints.
The "bites" rules rest mostly on one task (maize, unaudited): treat them as the best current hypotheses, pilot first.

## 4. AUTHOR ADDENDUM B9

1. **Assume every file is read.** In 24/24 runs, every anchor and resolving quote of all 16 premises was in the
   model's own tool output (both models print the whole folder in 1-3 commands). Burying a line, file count and
   position buy nothing. Only the interpretation a line demands matters. (all four tasks)
2. **An anchor that shares any token with a record cell is a join, not an inference** (30/30 solved; one maize P4
   run went by the bypass of item 6).
   - labour P4: first names "Ibrahima" and "Sekou" in the register's name column;
   - labour P3: the card list repeats "BANGOURA Alpha";
   - repair P3: "Friday" and "Wednesday" equal the printed day column;
   - repair P4: "gate ... Monday" equals the only `Gate walk-in,Mon` row;
   - maize P4: diary "09.10 (Fri)" equals the only 9 October row.

   Grep each anchor's names, weekdays, dates and route words against every column, not only the key.
3. **A worked figure printed with its inputs is executed, not read** (labour P2, repair P1, WC P2: 0/18 misses).
   Fable ran it as an assert or check in 6/9 runs (repair: `assert add_wd(D("2026-09-05"),10,PLANT)==D("2026-09-17")`)
   and Astra in 3/9. "Exactly one discriminating figure" held Astra on 0/9. Never make a single-figure T2 decisive.
   Guess: the field text "as the final account prints it" (labour P2) also pointed at the convention.
4. **An exemplar bites Fable only against a default it can cite a sentence for.** In maize P3, "whole bags; nobody
   opens a bag" led Fable to round up "as the card's buying rule requires". It called Vikram's 1,098 kg -> 24 bags a
   slip ("needs 25 bags") in 3/3 runs and never cited the card's own "420 kg: 8 bags". T2s with no citable default
   sentence were 0/9 on Fable. Build T7 from three parts: a sentence that reads as the default's rationale without
   stating it, a domain-justified default, and one figure in a second party's plan line.
5. **One witnessed row gets a row repair, not a new reading of the column.** In maize P2, 6/6 runs saw that the cash
   book (14 bags) and diary (2 x 7) contradict the 07-10 "24". 5/6 explained it locally ("I took 24 as a copying
   slip"; "a POS entry error") and kept 09-10 at 32, against a true 8. Witness exactly one row. Put the graded error
   on rows no anchor counts, and prove for the audit that the column reading is the only route. Guess: more witnesses
   on the already-witnessed row will not move it.
6. **No premise's answer may be readable off another premise's anchor.** In maize P4, the cash book that settles P2
   also counts the shed (2,665 + 3,731 = 24 bags), so 6/6 runs wrote the true 24. Astra UwJJmMm never mentions the
   real owner (`shed_bags = 10 + 2 * 7`, asserted equal to the cash-book count). Census each premise as "solve it
   with only the other premises' anchors"; any hit is a bypass.
7. **Do not grade a downstream number against the solver's own upstream when the files witness it directly.** Maize
   P4's two graded zeros (Fable 6bsoNtr, Astra UwJJmMm) both wrote the true shed of 24. The check demanded own lifts
   minus one lift (66 - 32 = 34). Give the premise its own set-valued check (the dates whose bags are in the shed).
   Add "downstream computed from its own witness" to the executed additivity census.
8. **A blank unit is a visible gap, and a unit word on the record is the answer** (12/12 solved). Maize P1: "The seed
   price on Kadam's list carries no unit". Repair P2: item "Tanker lid lock set" ("The ticket's quantity of 5 counts
   tanker sets"). Give the record a plausible unit of its own and carry the true basis in routine anchors. Guess: a
   printed unit the default misreads is the T3 shape that bites Fable (B8 §6.8); it is untested here.
9. **A rule scoped by a leading "For the X," or a closed list is a stated rule: T9 went 0/12.** WC P3 opens "For the
   net profit margin, ..."; labour P1's PP-04 s6 reads "no notice pay, no severance indemnity and no pro-rata share of
   the year-end bonus". Both models quoted the scope back ("only net profit margin excludes the after-tax property
   gain"). Do not make T9 decisive in this shape.
10. **Qualitative anchors with every total tying beat Astra, not Fable.** In WC P1, Astra 2/3 was voiced-and-rejected
    ("the narrative comments provide no explicit corrections to those balances") after its own tie-out asserts
    passed. Fable 3/3 tested each remark on the printed 2024 column ("the statement shows inventories falling"). Aim
    this shape at Astra. Guess: for Fable, no anchor may be testable against a printed prior-period figure.
11. **A definition that names a class makes both models classify every candidate line.** A letter that states the
    line's nature then settles it: WC P4 6/6 ("short-term bank credit ... whatever form the borrowing takes", then
    "stood undrawn since you repaid it in March 2025" and "paid ... with ninety-day accepted bills"). The nature must
    follow from routine facts in two files, never from a sentence saying what the line is.
12. **Expect voiced misses, so trap what a model does after it voices the conflict.** All 10 real misses were voiced
    (7 rejected, 3 resolved wrongly) and none was silent; Astra voiced 4/4, against B8 §1.4's 83% silent. Fable
    reversed records 15/15 where anchors map to one row (labour P4, repair P3, repair P4, maize P4, WC P1), against
    B8 §1.3. Fable failed only by not generalising one row to a column (maize P2) and by overruling an exemplar with a
    rule it could cite (maize P3): aim Fable traps there. n = 3 per premise per model.

