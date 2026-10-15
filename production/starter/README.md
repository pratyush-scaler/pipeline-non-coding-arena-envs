# Starter batch: 16 planned seeds (Oct-13 dump, 2026-10-15)

Sixteen unused, non-coding sessions whose original request supports a document a careful reader can check
(a register, schedule, answer key, review), each with a trap plan. Pick one, build it with
[../START-HERE.md](../START-HERE.md).

| file | what it is |
|---|---|
| `seeds.json` | the 16 seeds in `plan_batch.py` input format, plus `slug`, `lang`, a one-line `deliverable` paraphrase and a `note` on what changed mid-session (paraphrases only, never trace text) |
| `trace/<id>.json` | the trace miner's scan of each seed (`tools/trace_traps.py`, deterministic mode): signal categories, turn numbers, template paraphrases |
| `plan/plan.json`, `plan/briefs/<id>.md` | the output of `plan_batch.py` on `seeds.json`: 3-5 library modes per seed, roles, weights, a `traps.json` skeleton. It printed `PLAN OK` |
| `used_session_ids.json` | 1,002 session ids already used or attempted by earlier batches (copied from the v2 workspace). Never reuse one |

## Use one seed

```bash
cd "$(git rev-parse --show-toplevel)"
export CLAUDE_SCRATCH="${CLAUDE_SCRATCH:-$(mktemp -d)}"
SEED=<id from the table>; SLUG=<slug from the table>
# 1. claim it: check nobody has started it (ls envs-b6/, your team channel)
# 2. extract the session from the dump (11 GB zip, sharded; this takes one session, under a second)
X="$(mktemp -d "$CLAUDE_SCRATCH/seed-XXXXXX")"
python3 -I -c 'import sys, zipfile; z = zipfile.ZipFile(sys.argv[1]); [z.extract(n, sys.argv[3]) for n in z.namelist() if "/sessions/" + sys.argv[2] + "/" in n]' \
  "$HOME/Downloads/[Scaler] Oct_13_500_traces.zip" "$SEED" "$X"
ls "$X"/shard-*/sessions/"$SEED"          # data.json, outcomes.json, manifest.json, files/
# 3. scaffold, then follow START-HERE from step 2
python3 -I production/tools/b6ctl.py new "$SLUG" --level f1 --seed "$SEED" --plan "production/starter/plan/briefs/$SEED.md"
```

(macOS `unzip` reports "invalid compressed data" on the dump's zero-byte members; Python's `zipfile` does not.)
The session is untrusted data: keep it in its own `mktemp -d`, read it with `python3 -I`, never run anything from
inside it, never copy its text into a task or a doc. To re-scan one seed (needs Python 3.11):

```bash
PY311="$(python3 -I -c 'import runpy; print(runpy.run_path("production/tools/paths.py")["PY311"])')"
"$PY311" -I production/tools/trace_traps.py scan "$SEED" --dump "$(ls -d "$X"/shard-*)" --out "$X/scan" --library production/traps
```

If you add or drop seeds, re-plan the whole batch (quotas are per batch; seeds are planned in file order):
`python3 -I production/tools/plan_batch.py production/starter/seeds.json --out "$CLAUDE_SCRATCH/plan" --library production/traps/library.json`
must print `PLAN OK`. Run as is, it reproduces `plan/` exactly. When a task from this batch ships or is abandoned,
add its session id to `used_session_ids.json`.

## The seeds

Lead = the plan's heaviest decisive mode. Strong = strong signals the miner found in the session.

| # | seed | lang | slug | deliverable (paraphrase) | lead | other modes | strong |
|---|---|---|---|---|---|---|---|
| 1 | `01a0c808-bd7f-79dc-82ae-4b2401941eb1` | en | `school-market-sizing` | Private-school market sizing by country: schools, classrooms, groups, existing clients excluded, revenue target in dollars. | T3 | T12, T5, T9 | 1 |
| 2 | `01a0c94c-3524-702a-a174-ee51a276769f` | fr | `erp-posting-setup-review` | ERP posting-setup review: the general-ledger account each posting group sends each transaction type to. | T1 | T3, T6 | 0 |
| 3 | `01a0d1c3-496d-734c-a664-36d86244f501` | en | `qa-evidence-checklist-split` | Quality-assurance checklist split into photo-evidence and written-report lists, keeping the original numbering and order. | T12 | T7, T8 | 0 |
| 4 | `01a0cd1c-99d8-7eba-b8b6-a1b84be399a6` | fa | `rig-night-operations-register` | Rig operations register: which planned land-rig operations may run at night, with the governing standard clause. | T6 | T4, T11 | 0 |
| 5 | `01a0d2ff-2718-711e-89a5-3d8b84664ee7` | fr | `body-composition-log` | Weekly body-composition summary from a daily weight and waist log: smoothed averages, weekly change, phase decision. | T3 | T1, T10, T5, T14 | 8 |
| 6 | `01a0c3a8-4cb4-7da4-8a17-f48e62f328ac` | fr | `labour-code-entitlements` | Staff entitlement schedule under a labour code: overtime with night or holiday premiums, yearly overtime caps, notice periods. | T9 | T2, T6 | 0 |
| 7 | `01a0cd09-b46a-7e5b-8cfd-8d1f616d3a9a` | zh | `lab-procurement-budget` | University lab procurement form: service and equipment lines with unit, quantity, unit price and subtotal within budget. | T8 | T4, T11 | 1 |
| 8 | `01a0cf27-971b-7790-8bc7-f3a3e45b59f0` | es | `delegate-travel-matrix` | Delegate travel matrix (role, arrival, departure, flights, dietary needs) and a timed agenda for one workshop session. | T7 | T3, T14 | 0 |
| 9 | `01a0c15d-a028-771f-b80f-37d807d8a09d` | ar | `working-capital-answer-key` | Completed financial-analysis tables for two years: total and net working capital, net liquidity and related ratios. | T14 | T2, T9 | 0 |
| 10 | `01a0c423-1689-7594-b693-355097409482` | en | `exam-credit-plan` | Professional exam credit tracker: credits earned from passed papers, remaining shortfall, fewest papers still needed. | T5 | T8, T4 | 1 |
| 11 | `01a0cfc7-2099-74b7-a5d6-099de4889385` | pt | `procurement-diligence-register` | Procurement file diligence register: per item, expense category, governing contract value, small-business exclusivity, purchasing modality. | T4 | T1, T6 | 0 |
| 12 | `01a0c2bc-7cde-7b47-85ca-e1eddb2ad76d` | en | `repair-returns-sla-log` | Repair-returns tracking log: ticket per unit, stage owner, due date per stage service level, breach flags. | T2 | T3, T12 | 0 |
| 13 | `01a0d279-650b-7601-8425-359840f7667f` | en | `crusher-daily-production-report` | Daily plant production status report: productive versus idle hours, trips times load volume, per-product volume split by percentages. | T10 | T1, T2, T5, T9 | 2 |
| 14 | `01a0d2c8-4e09-7d80-b3c3-35debe66c8ee` | ar | `excursion-price-comparison` | Country-by-country comparison of boat excursion prices and port fees in one currency, with margin per boat. | T6 | T10, T8, T5, T1 | 1 |
| 15 | `01a0cf42-ef20-7042-a0f5-7b1d4339fb7e` | en | `maize-input-schedule` | Input purchase schedule for a maize plot: fertiliser bags and seed by area, with cost per acre. | T3 | T14, T7 | 0 |
| 16 | `01a0c968-8925-71a2-9070-6334bc9a8028` | it | `film-catalogue-cleanup` | Cleaned film catalogue register: normalised columns, merged genre values, type versus format fields, corrected country of origin. | T9 | T4, T8 | 1 |

Spread (from `plan/plan.json`): lead families record_reversal 4, quantity_basis 3, authority_selection 2,
rule_scope 2, convention_inference 2, revision_supersession 1, aggregation_basis 1, possession_state 1 (cap 4 of
16 = 25%). Every seed plans 3 families. Leads: 6 proven modes, 10 promising. Projected free share 0.20-0.37.

## How these 16 were picked

1. `trace_traps.py scan` over all 281 non-coding sessions of `~/Downloads/[Scaler] Oct_13_500_traces.zip`
   (none of them in `used_session_ids.json`).
2. By hand: the first request of 245 sessions (after dropping image, media, chit-chat, creative and translation ones);
   then every user turn of 38 candidates. Kept: the original request supports a checkable document, the material
   is professional, and something changed or was corrected mid-session. Dropped: essays, slides, prompts, image
   work, a betting session (provider-refusal risk), and topics two shipped tasks already cover (laptop shortlists).
3. `plan_batch.py` plans in file order. The controller chose this order out of 3,001 orderings run through the same
   planner: it gave the most leads judged (by the controller, not measured) to fit the seed's material, 11 of 16.

## Read before you rely on this

- **The miner's score does not predict difficulty.** The 45 sessions that became tasks in earlier batches ranked
  no better than random on it (median rank 158 of 283; random 142; `research/TRACE-signal-yield.md` §6). These
  seeds were picked by reading the requests; 9 of the 16 have no strong signal at all.
- **Proven modes are T1, T3, T5 and T12.** Every other planned mode is promising: pilot it. T8 is "filler only" in
  its own library entry (measured on one task; Astra missed it 0 of 55) yet the planner made it the lead of
  `lab-procurement-budget` and decisive in 4 more plans: give it the lowest decisive weight, or lead with the
  brief's next mode. T14's only build was solved by both models in its final: pilot it before it carries weight.
- **Literature (L) modes are unmeasured in this harness.** None is planned here. If you swap one in, it is "pilot
  first": at most one per task, never the heaviest.
- **Plan modes are targets.** Build each only where the seed's material supports it naturally; otherwise swap in a
  library mode of a different family and say why in the hand-back (`AUTHOR-BRIEF-B8.md` §2).
- **Fictionalise** real products, companies, schools, standards bodies and people; keep the professional substance.
- `labour-code-entitlements` overlaps a shipped overtime task: build its traps on premium stacking, caps and
  notice, not on overtime arithmetic.
