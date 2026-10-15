# Trap library schema (`traplib/1`)

The trap library is the single source of truth for which trap modes an author may build a decisive
premise from, and what is known about each one. `production/traps/traplib.py build` merges the
source files below into `library.json`, validates every mode against this schema, and renders
`TRAP-LIBRARY.md`. Never edit `library.json` or `TRAP-LIBRARY.md` by hand.

| source file | written by | ids | statuses allowed |
|---|---|---|---|
| `modes-internal.json` | `build_evidence.py` (measured in this harness) + curated recipe text | `T<n>`, `D<n>` | proven, promising, bimodal, dead |
| `modes-external.json` | research (papers, benchmark repos) | `L<n>` | literature |
| `modes-trace.json` | `tools/trace_traps.py` mining the trace dump | `R<n>` | trace-derived |

`T1`–`T9` and `L1`–`L5` keep the meaning they have in `briefs/TRAP-CATALOG-B7.md`, so every
`authoring/traps.json` already in the field still resolves.

## File shape

```json
{"schema": "traplib/1", "source": "internal|external|trace", "generated": "2026-10-15T19:30+05:30",
 "modes": [ MODE, ... ]}
```

## MODE

| field | type | meaning |
|---|---|---|
| `id` | string, `^[TLRD][0-9]+$` | stable; never reused for a different mechanism |
| `aliases` | list of strings | older labels (e.g. design_lint mechanism codes, TRAJ loophole names) |
| `name` | string, <= 80 chars | short mechanism name |
| `family` | enum, see below | mechanism family; batch diversity quotas count this |
| `status` | enum: `proven`, `promising`, `bimodal`, `literature`, `trace-derived`, `dead` | see status rules |
| `aimed_at` | enum: `fable`, `astra`, `both`, `unknown` | which calibration model it has bitten (or is expected to) |
| `clock` | bool | true if the mode is a clock / timestamp-ordering trap (Arena 261013: never the primary failure) |
| `summary` | string | one paragraph: the default the model takes and why the files make it wrong |
| `loopholes` | list of `L-record`,`L-join`,`L-shield`,`L-default`,`L-absorb`,`L-threshold`,`L-union`,`other` | model behaviour exploited (TRAJ §3) |
| `recipe` | object `{record, anchors, withheld, dials, conservation, shields}` (strings; `dials` a list) | how to build it so it stays genuine (TRAP-CATALOG §4) |
| `proof_obligations` | list of strings | what `authoring/validate.py` must execute for this mode (uniqueness, ablation, counterfactual, census...) |
| `hazards` | list of strings | ways this mode has been ruled unfair/ambiguous by an audit, with the task that taught it |
| `kills` | list of strings | edits that measurably killed it (e.g. "a stated rule", "a second figure inside the rate entry") |
| `trace_signals` | list of strings | what in a source trace suggests this mode fits the seed |
| `domains` | list of strings | professional settings where it occurs naturally |
| `example` | string | one concrete instantiation (no task-identifying graded values) |
| `evidence` | object, below | |
| `low_n` | bool, optional | a `D` mode whose computed status is not `dead` only because a model has n < 20 must say `true` (2026-10-15); `traplib.py build` refuses a non-dead `D` id without it |

### `evidence`

```json
{"internal": [{"task": "a_f1_gst-workbook-answer-key", "version": "1.7.0", "premise": "P1",
               "stage": "final", "fable": [9, 10], "astra": [10, 10], "audit": "GENUINE"}],
 "pooled": {"fable": [k, n], "astra": [k, n]},
 "external": [{"source": "OfficeQA Pro", "url": "https://...", "year": 2026,
               "finding": "...", "models": "...", "metric": "..."}],
 "traces": [{"session": "<session id>", "signal": "<paraphrase, never raw trace text>"}]}
```

`[k, n]` = premise MISSED in k of n valid runs (voids excluded). Pilot rows carry `"stage": "pilot"`
and are never pooled into a `proven` decision.

## Families

`record_reversal` (a structured record keyed/filed to the wrong owner, reversed by first-hand anchors) ·
`convention_inference` (a convention fixed only by worked figures) · `quantity_basis` (tax/pack/unit/scale
basis cued on the record) · `possession_state` (already in hand / still needed) · `authority_selection`
(which document, edition or rate governs) · `rule_scope` (a real rule over-applied beyond its scope) ·
`temporal_anchor` (which event starts a period; fiscal vs calendar; clocks) · `aggregation_basis`
(cumulative vs period, conservation, double counting) · `revision_supersession` (a later restatement or
changed premise replaces an earlier figure) · `identity_resolution` (pairing orphan and missing records) ·
`other`.

## Status rules (computed, not asserted)

- `proven`: audited GENUINE in >= 2 tasks, and pooled FINAL miss rate >= 0.20 on at least one model
  with n >= 20 on that model.
- `promising`: measured here but short of `proven` (one task, or pilot-only, or n < 20).
- `bimodal`: missed either ~never or ~always across tasks (per-task final rates all <= 0.1 or >= 0.9,
  spanning both ends).
- `dead`: pooled miss rate <= 0.05 on BOTH models with n >= 20 each.
- `literature`: external evidence only; no measured row here yet.
- `trace-derived`: mined from traces; not yet measured here.

## How the pipeline reads it

- `design_lint`: a decisive premise's `template` must be a library id (or alias). `dead` → FAIL;
  `literature` / `trace-derived` / `bimodal` → WARN "pilot first"; `proven` / `promising` → ok.
  A `D` id, or a mode listing a `D` id among its aliases, is the dead list: FAIL as a decisive template
  whatever its computed status (2026-10-15), and `plan_batch.py` never plans it.
- `plan_batch.py`: allocates modes to seeds under the batch quotas (no family heaviest in > 20–25%
  of tasks, >= 3 decisive families per task, at least one decisive mode aimed at each model).
- `trace_traps.py`: proposes library ids for a seed from its trace signals.
- Promotion: `build_evidence.py` recomputes statuses from campaigns + audits; a `L`/`R` mode that
  gets measured rows is re-issued as a `T` mode with the old id kept in `aliases`.
