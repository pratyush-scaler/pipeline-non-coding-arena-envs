# Internal trap evidence, refreshed 2026-10-15 (snapshot 19:56 IST)

This refresh replaces the hand-assembled 45-task pass (`INTERNAL-trap-evidence.md`/`.csv`) with a script.
`production/traps/build_evidence.py` reads the live workspace read-only and writes three files:

- `INTERNAL-evidence-20261015.csv`: one row per task, version, premise and stage, with both models side by side;
- `INTERNAL-evidence-20261015-pooled.json`: per mode and per declared template, every skip with its reason, and every verdict citation check;
- `traps/modes-internal.json`: schema traplib/1.

Rerun it with `python3 -I build_evidence.py --root <W> --out <dir>`. Its tests are `test_build_evidence.py`, run as `python3 -I -m unittest` from `production/traps`.

Harness: Fable 5.1 (`anthropic/claude-fable-5-1`) in Claude Code and GPT-6 Astra (`openai/gpt-6-astra`) in Codex, both at high effort with no turn or time limits. Campaigns were still running while this was built: 4 runs were launched but not yet pulled, and 2 finished runs were never pulled. One Astra campaign landed between the last two runs of the script. A rerun will move some numbers.

## How a number is made

- **Missed premise.** A premise is missed in a valid trial when any of its checks, in its own step, was evaluated below 1.0. This follows `signal_gate.py`.
- **Voids.** A trial with `valid=false` is dropped. A whole run is dropped when the ledger marks it void-auth or lists it in a `void_history`, or when an unledgered run's logs match `measure.py`'s credential-failure pattern.
- **Gated checks.** A premise whose only failing checks were gated out, skipped or absent counts as neither missed nor passed.
  - The counted runs contain 0 void trials and 0 gated checks.
  - All 798 void trials and 232 gated-out checks in the workspace sit in runs that are not counted: void-auth runs, or tasks with no premise map.
- **Premise maps.** Each campaign joins the `authoring/traps.json` of the tree with the same task name and version. If several trees carry that version and their maps differ, the ledger digest picks one.
- **Mode assignment** (`traps/mode-map.json`). Rules apply in this order:
  1. an explicit override (15 rules, each with its reason);
  2. a stated premise goes to D1, unless its own mechanism is already a dead one;
  3. the premise's `template`;
  4. the hand-reviewed mechanism label from the 45-task pass, carried forward to later versions of the same task, premise id, family and mechanism code;
  5. a mechanism-code fallback.

  No unit is left unmapped.
- **Verdicts** (`traps/audit-verdicts.json`).
  - The 45-task pass verdicts form the base.
  - On top come 32 records from the B7 audits, the re-audits and the genuineness log after 15:30. Each record carries a quote, and the script checks that the quote is in the cited file. All 32 are found.
  - The latest record wins.
- **Pools.**
  - `evidence.pooled` covers every valid run, pilot and final, with AMBIGUOUS and DEFECT units excluded.
  - **proven** is decided on final rows only. It also drops unaudited units missed at least 90% on either model, which are presumed ambiguous (124 rows carry that flag). It needs GENUINE or GENUINE-soft final units that actually bit in at least 2 tasks.
  - **dead** uses the all-stage pool.
  - **bimodal** uses per-task final rates on each model at n ≥ 10.
- **Lever lab.** Task-level results from L01–L29 (5 episodes per model) are added as pilot rows for the dead modes they test. L20 is excluded because it was an ambiguity.

## Scope, and what changed against the 45-task pass

| | 45-task pass | this refresh |
|---|---|---|
| tasks | 45 | 45 (no new task has a premise map yet) |
| task-versions | 217 | 257 (+40: the v6/B7 rounds) |
| task-version-premise units | 1,129 | 1,348 (+224 new; 5 old units dropped, from brightwater 1.0.0) |
| units with Astra runs | 606 | 881 (the 10-12/10-13/10-15 key reruns landed) |
| premise-runs, Fable / Astra | 7,805 / 4,880 | 9,870 / 7,310 |
| final 10×2 premise-runs, Fable / Astra | not split | 3,130 / 2,990 |
| campaigns counted, Fable / Astra | 561 / 462 (incl. b4) | 317 / 221 (premise-mapped only) |

**Cross-check.** Every unit-stage-model count the 45-task pass reported was recomputed: 2,126 agree, 0 disagree. The 10 missing cells are brightwater 1.0.0, which has no frozen premise map. The old pass took those from a gates JSON; this run skips them, with the reason recorded.

**Skips** (all listed with reasons in the pooled JSON):

| model runs | reason |
|---|---|
| 441 | no premise map (b4/fb trees) |
| 137 | legacy `traps[]` map, whose checks are shared between traps and so not attributable |
| 152 | void-auth run |
| 35 | version with no tree on disk |
| 2 | failed |
| 6 | in the ledger but not on disk (4 launched, 2 finished but never pulled) |

Also skipped: 2 probe folders, and 5 lever labs with no matching mode.

## Statuses (computed) and what moved

F = Fable, A = Astra. "Final" counts only 10×2 runs; "all" adds pilots; AMBIGUOUS and DEFECT units are excluded. "Genuine tasks" counts tasks with a GENUINE final unit that actually bit.

| id | mode | final F | final A | all F | all A | genuine tasks | status | catalogue B7 said |
|---|---|---|---|---|---|---|---|---|
| T1 | keying slip | 345/680 | 299/640 | 742/1825 | 576/1450 | 13 | **proven** | proven |
| T2 | convention from worked figures | 185/960 | 129/900 | 434/2650 | 247/2005 | 10 | **promising** | proven: **moved** |
| T3 | quantity basis on the record | 78/90 | 23/90 | 153/235 | 49/200 | 4 | **proven** | proven |
| T4 | already in hand | 13/70 | 8/70 | 24/165 | 13/145 | 2 | **promising** | proven: **moved** |
| T5 | misfiled note or record | 26/80 | 41/80 | 53/170 | 81/170 | 2 | **proven** | under test: **moved up** |
| T6 | edition by the real date | 50/80 | 59/70 | 96/245 | 94/120 | 1 | **promising** | proven: **moved** (one audited task) |
| T7 | two-party worked figures | 9/30 | 1/30 | 16/55 | 4/45 | 1 | **promising** | proven: **moved** (one task) |
| T8 | changed premise before issue | 7/30 | 0/30 | 12/55 | 0/45 | 1 | **promising** | proven, filler: **moved** |
| T9 | rule-scope shield | 20/40 | 0/40 | 43/95 | 1/95 | 1 | **promising** | added as proven: **moved** |
| T10 | structural misfile (new) | 12/30 | 26/30 | 17/55 | 41/55 | 0 | **promising** | not listed |
| T11 | copied filed column (new) | 2/40 | 40/40 | 12/90 | 77/85 | 1 | **promising** | "Astra-only shape" |
| T12 | line transposition (new) | 27/50 | 36/50 | 52/135 | 75/130 | 2 | **proven** | "Astra-only shape" |
| T13 | units/scale by remarks (new) | 10/160 | 0/140 | 29/520 | 4/375 | 1 | **bimodal** | "Fable-only shape" |
| T14 | cumulative vs period (L5 promoted) | 0/10 | 0/10 | 1/15 | 0/15 | 0 | **promising** | L5, untested |
| D1–D4, D6–D16 | §5 dead list | | | | | | **dead** | dead |
| D5 | totals that tie | – | – | 0/50 | 0/15 | 0 | **promising** | dead |
| D17 | decoys and pointers | – | – | 0/5 | 0/5 | 0 | **promising** | dead |

What the movements mean:

- **T2 sits right at the bar.** As authors use the template, it covers every convention fixed by worked figures, and its final pool is F 19.3%, A 14.3%.
  - The rounding/truncation sub-shape alone is F 119/550 (21.6%) and A 108/520 (20.8%), which would compute proven.
  - The non-rounding conventions (HSV basis, day counts, word counts, range ends) are F 66/410 and A 21/380.
  - Labels decide which way it falls. `mode-map.json` folds CV.method into T2 because the catalogue's own T2 text includes "per-bill vs per-line" and "which end of a range". Split it if the library wants the stronger number.
- **T4, T6, T7, T8 and T9 are promising, not proven,** because each has one audited task that bit.
  - T4 also falls below 0.20 on both models once its second task (psychopathy P6, Astra) is pooled.
  - The catalogue's "proven" label for these rests on one task each.
- **T5 meets the proven bar** on ats P6 (1.7.0, F 10/10, A 10/10, GENUINE; flat) and deck P5 (2.8.0 GENUINE, F 2/10).
- **T12 meets the proven bar** on melody P2 and home-bp 2.12.0 P6, both GENUINE. pupil P2 is blind-reader only.
- **D15 (clock offset) computes dead** at F 11/230 (4.8%) and A 1/145. It is borderline on Fable, and the deck 2.2.0 P3 cascade (a DEFECT, Astra 15/15) is excluded. Council P5's lead-or-clock premise is labelled a worked-figure convention, so it sits in T2.
- **D5 and D17 compute promising** because the dead rule needs n ≥ 20 on both models, and Astra has 15 and 5. This is a schema gap rather than evidence that they work. `design_lint` treats promising as acceptable, so a decisive premise built on D5 or D17 would pass the lint.

## The candidate new modes, checked against the data

- **Structural misfile (T10).** Built only where the premise's anchors carry a conservation sentence ("one row per page field").
  - It bit Astra in brightwater P6 (1.5.0/1.6.0 finals, A 20/20; F 12/20) and killzone 1.5.0 P5 (A 6/10, F 0/10).
  - It bit neither model in spice 2.6.0 P7 or line-colour 1.5.0 P5 (pilots, 0/5 each).
  - No audit exists yet.
- **What the brief's list really separates.** Kibo, ats, pathway and deck are content-only misfiles (kibo P7, ats P6, pathway P7, deck P2): no conservation sentence. They bit Astra in finals: ats A 21/30, pathway A 20/20, deck A 40/40.
  - Content-only misfiles that died: spice 2.5.0, line-colour 1.4.0, killzone 1.4.0 and timesheet 2.7.0.
  - So the conservation sentence is not what separates bite from no-bite. The candidate holds as a shape for Astra, but its mechanism is unproven.
  - The content-only ones stay in T5, or in T11 where the author called them a copied column.
- **Copied filed column (T11).** One clean task: deck P2, A 40/40 and F 2/40 across 2.2–2.8 finals, GENUINE.
  - Its second build, kibo 2.9.0 P7, was audited AMBIGUOUS on one of its two checks.
  - It is Astra-only and flat.
- **Line transposition (T12).** It holds on both models (home-bp P6 F 20/20, A 15/20; melody P2 A 17/20; pupil P2 F 6/10, A 4/10). Okra's transposed cells were dead.
- **Units or scale by incidental remarks (T13).** Bimodal: profile P7 is the only real bite (F 10/10 in the 2.4.0 final, GENUINE).
  - The other 17 tasks' scale premises were solved.
  - The one exception is niche 1.3.0 P1, Astra 4/5 in a pilot after the inches ambiguity was fixed; it is unaudited.
- **Rule-scope shield (T9).**
  - melody P3 is GENUINE after the re-audit: F 16/20 finals, A 0/20.
  - killzone P1 bit F 4/10, unaudited.
  - council 1.4.0 P6 and line-colour P8 were dead.

## Caveats

- **Low n.** 1,348 of 1,661 rows are 5-run pilots. A pilot is triage, never proof. T7, T8, T9, T10, T11 and T14 have final pools of 40 runs or fewer per model, and none of them has two audited tasks.
- **Unaudited bites.** T10 has no audit. T11 has one clean task. Units missed at 90% or more without an audit (124 rows) are kept in the pools but kept out of every proven decision.
- **Judgement calls.**
  - Mechanism labels and the 15 overrides are judgements, all recorded in `mode-map.json`.
  - Verdicts were transcribed by hand from free text. GENUINE-soft counts as genuine; BLIND-1.0 and UNCONFIRMED count as neither.
  - kibo 2.9.0 P7 is excluded as AMBIGUOUS because one of its two checks was ambiguous.
  - The lever-lab rows are task-level passes, not premise checks.
- **Checks that differ from `traplib.py`.** Its own status check counts GENUINE final rows whether or not they bit, and tests bimodality row by row. This script is stricter in both. `traplib build --strict` on the produced file reports no disagreement today; it could diverge on future data.
- **`aimed_at`.** It comes from pooled rates of at least 0.20, else from any task at 0.5 or more. For dead modes it falls back to the premises' declared aim.
- **Not covered.** Batch-4 tasks with no or legacy trap maps (578 model runs) are excluded.
  - So are the clock bites in those maps: exam-prep and m-e-survey, recorded in the 45-task pass.
  - Arena 261013 found the clock as the primary failure in 34 of 37 batch-4 tasks. D15 measures only the b6 CLOCK premises.
