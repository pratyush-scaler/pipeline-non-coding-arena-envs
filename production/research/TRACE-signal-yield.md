# TRACE: trap-signal yield of the unused non-coding traces

B8 research, written 2026-10-15 (clock read 20:13 IST while finishing). The tool is `production/tools/trace_traps.py`; its tests are in `test_trace_traps.py`; the R-mode source file is `production/traps/modes-trace.json`.

Nothing in this file is raw trace text. Session ids are given in full. Every description of a moment is either the tool's fixed template or my own paraphrase in at most 20 words. All of them were checked against their session's text with the tool's 5-word-shingle guard.

## 1. Tool

```
cd production/tools
python3 -I trace_traps.py scan <session-id>... --out DIR [--dump DUMP] [--library DIR] [--llm]
python3 -I trace_traps.py scan --list ids.json [--exclude used.json] [--limit N] --out DIR [--dump DUMP]
python3 -I trace_traps.py report DIR [--top 15] [-o yield.md]
```

**Loading**

- Python 3.11 or later is required, because the pipeline imports `tomllib`; macOS `/usr/bin/python3` 3.9 cannot run it.
- Sessions load through the pipeline's own readers, imported read-only from this worktree:
  - `pipeline.dump.recover.load_trace`;
  - `pipeline.dump.evidence.read_channels`, for user and assistant text records with their undo markers;
  - `pipeline.dump.signals.load_outcomes` / `build_seeds`, for Arena's steer, complaint and outcome-failure labels.
- `--dump` accepts a dump root or its `sessions/` directory. Without it, the tool uses the pipeline's configured dump (`ARENA_DUMP`, then `workspace.toml`).
- An unreadable session is listed under `errors` in `summary.json`. It is never silently dropped.

**Signals**

- There are ten categories:
  - `user_correction`
  - `requirement_change`
  - `document_conflict`
  - `misattribution`
  - `unit_or_basis`
  - `convention` (rounding / aggregation)
  - `edition_or_date` (edition / fiscal / period_start)
  - `possession`
  - `rule_shield`
  - `assistant_error_caught`
- Each signal carries a 0-based message index (`turn`, the `traces[0].messages` convention of `seeds-b6.json`) and a 1-based `user_turn`.
- Strength runs from 0 to 1. A signal is "strong" at 0.6 or above.
- Detection is deterministic: multilingual cue lexicons for en, ru, fa, ar, zh, es, pt, fr, it, de, pl, tr, id/ms, nl, he, ja, ko, hi/Hinglish, bn, th and vi. Text is normalised for Arabic/Persian letter forms, ZWNJ and Persian/Arabic digits.
- Strength is reduced by context penalties:
  - sandbox or download complaints;
  - styling-only complaints;
  - a cue that sits inside pasted material, meaning a long turn where the cue falls outside the user's own opening or closing lines.
- Strength is raised by corroboration: Arena's outcome label on the same turn, a concession in the reply, or a concrete figure.
- An Arena outcome label with no lexical cue yields a weak `user_correction` (0.4, cue `outcome_only`).

**Mapping**

- Mode ids come from the `trace_signals` of `production/traps/modes-internal.json`, `modes-external.json` and `modes-trace.json`. These are the three files `traplib.py` reads. Any other `modes-*.json` is skipped and listed; `modes-curated.json` is skipped this way.
- The mode's `family` adds a tie-break bonus, but only once a trace-signal stem has matched. Dead modes are never proposed.
- When no library mode matches, a built-in map of the T1–T9 / L1–L5 catalogue applies.
- A generic correction with no object is left unmapped (`mapping_source: none`). Nearly every mode's trace signals begin "the user corrects …", so such a correction says nothing about mechanism.

**Paraphrases**

- Paraphrases are fixed English templates, clipped to 20 words.
- Each one is checked against the session's own text. A paraphrase sharing 5 consecutive words, or 6 consecutive non-ASCII characters, is replaced by `<category> signal at message N`.
- Cue matches are recorded as class names, never as matched strings.

**Ranking**

- The trap-rich score sums the five strongest strong events. A strong event is a strong signal, with the same category on adjacent user turns merged into one event. On top of that:
  - +1.0 when there are at least 2 independent moments (event turn ranges that neither overlap nor touch);
  - +0.75 for a strong mid-session premise change (`requirement_change` or `edition_or_date` after the first request and before the last turn);
  - a category-diversity bonus;
  - a weak-signal tail of 0.05 per weak signal, capped at 0.5, so one strong event always outranks a session with only weak signals.
- The score is halved when the session's metadata has no knowledge-work category.

**`--llm`**

- Off by default.
- It makes one strict-schema, forced-tool call per session through `pipeline.select.classify._call`, which goes through the provider `request_slot` budget and credential routing. No `temperature` is sent.
- Every returned item is validated locally, and its paraphrase still goes through the raw-text guard.
- Unit-tested with a fake transport only. It was never run against the live API.

**Tests**

- 41 tests on synthetic sessions, with no dump and no network. They cover:
  - every category, plus ru/fa/zh/es/ar cases;
  - the context penalties and undo handling;
  - scoring;
  - mapping with no library, a missing library directory, a synthetic library (skipped, broken and dead files), and the real library;
  - the no-raw-text rule end to end: every fixture message carries a marker, and no output file may contain it;
  - the `--llm` validation path.
- How to run them:
  - `python3 -I -m unittest discover -s . -p test_trace_traps.py` → 41 OK.
  - `python3 -I test_trace_traps.py` → 41 OK.
  - Bare `python3 -I -m unittest` in `production/tools`, the README-FLOW convention → 80 OK, 1 skipped, which includes these 41.
- The literal `python3 -I -m unittest test_trace_traps` cannot import any module from the current directory. `-I` implies `-P`, so the cwd is not on `sys.path`. This is equally true of every other suite in this repo.

## 2. Coverage

**The population the brief named is empty.**

- `unscreened_noncode.json` is `[]`.
- `used_session_ids.json` lists all 500 sessions of `accepted_500_traces` (all 283 non-coding ones included) and all 500 of `kaizen_dump`.
- `scan --list unscreened_noncode.json --exclude used_session_ids.json` therefore scans 0/0.

**The scanned population: the Oct-13 dump.**

- Source: `~/Downloads/[Scaler] Oct_13_500_traces.zip`, 500 sessions, none of them in `used_session_ids.json`.
- Non-coding means no `code_*` category in the session metadata. This rule reproduces `datasets/noncode_sids.txt` exactly on `accepted_500_traces` (283 of 283, no extras). On the Oct-13 dump it gives 281 non-coding sessions.
- Only their `data.json`, `outcomes.json` and `manifest.json` were extracted, into this session's scratch directory (700 MB). Nothing was written under W or in the repo.
- Scanned 281 of 281, 0 unreadable, in 17 s (deterministic mode).
- Session language: en 119, ru 49, fa 26, ar 15, zh 14, fr 10, pt 7, hi 7, others 34.

**The comparison population: the 283 used non-coding sessions of `accepted_500_traces`.** These were scanned the same way and used only as a check (§6).

## 3. Yield (281 unused non-coding sessions)

| measure | sessions |
|---|---|
| ≥ 1 strong signal | 33 (12%) |
| ≥ 2 independent strong signals | 6 (2%) |
| strong mid-session premise change | 4 (1%) |
| ≥ 2 independent strong signals **and** a mid-session premise change | 3 (1%) |
| Arena outcome corrections ≥ 2 (the pipeline's `CORRECTIONS_STRONG` bar) | 129 (46%) |

| category | signals | strong | sessions with a strong one |
|---|---|---|---|
| user_correction | 541 (413 outcome-label only) | 45 | 31 |
| requirement_change | 54 | 4 | 4 |
| document_conflict | 29 | 2 | 2 |
| misattribution | 11 | 2 | 2 |
| unit_or_basis | 6 | 0 | 0 |
| convention | 5 | 1 | 1 |
| edition_or_date | 15 | 0 | 0 |
| possession | 3 | 0 | 0 |
| rule_shield | 4 | 0 | 0 |
| assistant_error_caught | 149 | 42 | 30 |

Ids mapped from strong signals (library mapping):

| ids | count |
|---|---|
| T1, T5, T10 | 17, 17, 15 |
| T8, L1, L8 | 4 each |
| T6, L9, T3, T12 | 2 each |
| T2 | 1 |

The T1/T5/T10 counts come mostly from generic record corrections (record-reversal family), not from identified keying slips.

**Comparison population** (283 used sessions):
- ≥1 strong signal: 26 (9%).
- ≥2 independent strong signals: 4 (1%).
- Mid-session premise change: 2.
- Both together: 0.
- Outcome-label corrections ≥2: 30 (11%). The Oct-13 dump carries far denser Arena outcome labels.

**What the numbers say.**
- Strong, trap-shaped moments are rare: about 1 session in 8 has one, and 1 in 50 has two independent ones.
- The specific mechanisms the catalogue cares about (basis, convention, edition, possession, rule scope) almost never show up as strong lexical events. Almost all strong signals are generic corrections; the mechanism has to be read off the turn by hand.
- Arena's outcome labels mark far more turns than the lexicons do: 413 label-only turns against 128 lexical ones. They are a cheap candidate list but a noisy one (§5).

## 4. Top 15 sessions by trap-richness

The fit note is my own paraphrase after reading the strong turns. The moment column holds the tool's template for the strongest event.

| # | session | lang | score | strong events (indep.) | mid change | proposed ids | strongest moment (tool) | fit note (mine) |
|---|---|---|---|---|---|---|---|---|
| 1 | `01a0ce67-844d-7752-bce3-29fca34b4376` | pt | 6.20 | 5 (4) | yes | T6, T8, L9, L1 | m15 user_correction 0.8: user says the previous output was wrong and gives a figure | Prompt specs for a product-image workflow; two reference files disagree with the prompt; user names the governing reference. Medium. |
| 2 | `01a0c3d6-a781-7f48-9d95-454fcf6b055f` | fa | 4.80 | 4 (3) | no | T1, T5, T10, T12 | m6 user_correction 0.95: wrong, gives a figure; assistant concedes | Garment renders from a character sheet; repeated rejections; one swatch built from the wrong reference. Low (image edits). |
| 3 | `01a0d00f-9856-74bb-8239-5fdab9e8049d` | en | 4.00 | 3 (2) | yes | T8, L1, L8 | m24 requirement_change 0.65: requirement changes after work began, with a figure | Laptop shortlist research; agreed processor series drifted; an availability ruling reversed by a part number. High (T1/L9). |
| 4 | `01a0d2ff-2718-711e-89a5-3d8b84664ee7` | fr | 4.00 | 3 (3) | no | T1, T5, T10, T6 | m126 user_correction 0.95: figure or record wrong; assistant concedes | Personal training-log analytics; projection premise and one-versus-pair load corrected. High (T3 pair basis, revised premise). |
| 5 | `01a0d14c-e98c-734c-b0a7-9f29f6765baf` | en | 3.45 | 2 (2) | yes | T8, T1, L1, T5 | m20 requirement_change 0.7: requirement changes after work began, with a figure | Course answers on education policy; user supplies the governing policy names by year. Medium (T6/L2 edition by date). |
| 6 | `01a0ce77-6bb8-740e-9487-146523c26802` | en | 2.90 | 2 (2) | no | T1, T5, T10 | m221 user_correction 0.8: figure or record wrong | Very long mixed session; omissions in a document list flagged. Low. |
| 7 | `01a0d279-650b-7601-8425-359840f7667f` | en | 1.65 | 2 (1) | no | T1, T2, T5, T10 | m18 convention 0.6: rounding convention disputed | Daily plant production report in a fixed format; percentage-split rounding disputed with worked figures. High (T2); its local-clock times are a dead lever. |
| 8 | `01a0cf66-48c1-71b1-9b39-45acc9ebd117` | en | 1.55 | 1 (1) | yes | T8, L1, L8 | m18 requirement_change 0.6 | Trading-journal design; a checklist turned into a computed grade. Low. |
| 9 | `01a0c864-15a1-7dfb-a1af-5553ccc03d1c` | tr | 1.25 | 1 (1) | no | – | m27 user_correction 0.75: wrong, gives a figure | Security curriculum prompt; officially published iteration figure versus the one used; algorithm switched. High (T6/L1). |
| 10 | `01a0c9b1-abfc-76b4-9e2c-160785c7e3b0` | en | 1.25 | 1 (1) | no | – | m42 user_correction 0.75 | Competition pitch pack; a pasted critique exposes a second-year cash gap; assistant concedes. Medium. |
| 11 | `01a0c97e-079d-773f-aedd-17050dae052f` | pt | 1.15 | 1 (1) | no | T1, T5, T10 | m57 user_correction 0.65 | Clinic sales script and question bank; answer order still wrong after a fix. Low–medium. |
| 12 | `01a0cd67-feb7-757e-97ba-bd7a86b1b071` | en | 0.95 | 1 (1) | no | – | m16 user_correction 0.75 | Anime image generation, repeated rejections. None (image). |
| 13 | `01a0cd78-9c21-7c38-84b6-9d243560f68a` | fa | 0.95 | 1 (1) | no | T1, T5, T10 | m6 user_correction 0.8 | Contract-form PDF; blank fields misplaced. Low (layout). |
| 14 | `01a0d2c8-4e09-7d80-b3c3-35debe66c8ee` | ar | 0.90 | 1 (1) | no | T1, T5, T10 | m39 user_correction 0.65 | Boat-trip price comparison deck; user disputes prices and asks for booking-page sources. Medium. |
| 15 | `01a0c8de-8cfe-711d-9805-6cd1bb69a5d5` | ru | 0.85 | 1 (1) | no | – | m5 user_correction 0.8: wrong, gives a figure | Group presentation; user says the assistant split the sections among the presenters wrongly. Medium (T1/T5 ownership). |

**Notes on the ranking.**
- **The weak-signal tail was capped after a check.** The first ranking put a session with ten weak doubts and no strong event at rank 15, above 19 sessions with one strong event (17 of them knowledge-work). The tail is now 0.05 per weak signal, at most 0.5. Ties are broken by session id.
- **The ranking is shallow.** From rank 8 down, every session rests on a single strong moment.
- **The knowledge-work factor has a gap.** The 0.5 factor does not catch image sessions labelled `media_analysis` (ranks 2 and 12).
- **The generic paraphrases don't show the mechanism.** Ranks 9 and 15 propose no ids, because their corrections carry no record noun. Their mechanism (T6 at rank 9, ownership at rank 15) shows only on reading.

**Seeds I would look at first:** `01a0d279…` (T2), `01a0c864…` (T6/L1), `01a0d2ff…` (T3), `01a0d00f…` (T1/L9) and `01a0d14c…` (L2/T6).

## 5. Precision spot-check

**Method.**
1. Two tuning passes came first, and the lexicons were fixed after each:
   - pass 1: 25 random strong signals on the first scanner; 15 were real moments;
   - pass 2: 15 more on the fourth version; 9 were real, 7 with the right category.
2. The formal check drew 10 at random (seed 2026) from the 35 strong, non-concession signals that neither pass had shown me, on the scanner as it stood. I then read each turn with its neighbours.

| # | session | msg | flagged | verdict | what it is (my paraphrase) |
|---|---|---|---|---|---|
| 1 | `01a0c8bc-de99-7ad7-9aa4-6edfc92b3def` | 12 | user_correction 0.65 | real, right category | A requested question bank was left out of the compiled worksheet. |
| 2 | `01a0ce67-844d-7752-bce3-29fca34b4376` | 15 | user_correction 0.8 (+ document_conflict 0.7) | real, right category | User asks where the prompt's item count comes from; two reference files show otherwise. |
| 3 | `01a0d2ff-2718-711e-89a5-3d8b84664ee7` | 70 | document_conflict 0.6 | not real | Repeat measurements spread widely and the user kept the middle one; no document disagrees. |
| 4 | `01a0c804-49e5-7cea-a246-709ea5126a70` | 8 | requirement_change 0.6 | not real | A request to keep regenerated characters visually consistent, not a changed premise. |
| 5 | `01a0d00f-9856-74bb-8239-5fdab9e8049d` | 26 | user_correction 0.65 | not real | User repeats an earlier instruction; nothing in the previous output is corrected. |
| 6 | `01a0d2ff-2718-711e-89a5-3d8b84664ee7` | 128 | user_correction 0.95 | real, right category | User rejects a false claim about a repeated question and the use of a limit figure. |
| 7 | `01a0d2f8-8f02-7fd0-b621-c504edc618d5` | 4 | user_correction 0.8 | real, right category | Spelling-only fixes were authorised; the assistant reworded and added text. |
| 8 | `01a0ce27-895c-7461-bdab-39e4f0e2e4fc` | 42 | user_correction 0.75 | not real | A sandbox error report after a download step. |
| 9 | `01a0d00f-9856-74bb-8239-5fdab9e8049d` | 24 | requirement_change 0.65 | real moment, wrong category | The assistant drifted from an agreed processor series; this is drift, not a requirement change. |
| 10 | `01a0cd78-9c21-7c38-84b6-9d243560f68a` | 6 | user_correction 0.8 | real, right category | Blank fields on a form are misplaced (layout only). |

**Result.**
- **6 of 10 are real** correction moments; **5 of 10** carry the right category.
- 3 of the 10 are seed-quality for a knowledge-work trap: #2, #6 and #9. The others are a coverage omission (a dead family), a stated scope instruction, or layout.
- After the check I fixed two lexicon entries: the sandbox-error phrasing (#8) and an Indonesian "change" verb (#4). With those fixes, #4 and #8 drop below strong, so the same sample gives 6 of 8. That second number is not blind.

**Recall was not measured systematically.** In 30 random Arena outcome-label-only turns, about 7 were real corrections the lexicons missed. Cues for those phrasings were added afterwards.

## 6. Does trap-richness pick the sessions that became tasks?

**Not on this evidence.**
- 45 of the 283 used non-coding sessions are `source_trace` of a task under `envs-b6/_versions`.
- Their trap-rich ranks have median 158 of 283; random would be 142.
- Only 2 of 45 have any strong signal, against a 9% base rate (26 of 283).

The b6 traps were authored from the catalogue, not replayed from trace corrections (F0–F2 targets). So this neither validates nor refutes the score. Whether trap-rich seeds give harder tasks needs a build and a 10×2 measurement. Until then, treat the ranking as a reading list, not a difficulty prediction.

## 7. R-modes

**None qualified, and `modes-trace.json` ships with `"modes": []`.** It validates in `traplib.py build` together with `modes-external.json`. A full build with all three sources is currently refused, because `modes-internal.json` fails on D5 and D17 ("D id with status 'promising'"). That file belongs to another agent and I did not change it.

Recurring patterns considered, each found in 3 or more sessions. The evidence rows are in the file's `considered` key; `traplib.py` ignores that key.

| pattern | sessions | why rejected |
|---|---|---|
| Scope bleed: the assistant edits beyond the authorised scope and the user says it was not asked for | 3, of which 2 are image edits | The authorisation is a stated instruction, and stated rules never bite. The over-application mechanism is T9 / L12. |
| A user-supplied reference or official source overrides the assistant's figure | ≥ 3 | Covered by T6 and L2/L9. Context-versus-memory conflicts are listed as solved in TRAP-CATALOG-B7 §6. |
| A figure computed from a count or split is corrected (ceiling of a duration split, one load versus a pair) | 3 | Covered by T2 and T3. |
| The user corrects their own earlier premise, or forwards a later fact | ≥ 3 | Covered by L9, L1 and T8 (filler only). |

## 8. Limitations

- **Lexical detection.** Precision is about 0.6 (blind, n=10). Recall is unknown; label-only turns suggest about 1 in 4 is missed. Persistence ("still not right") and pasted critiques are counted as corrections whatever their content. Mechanism categories fire rarely.
- **Templates hide the mechanism.** The paraphrases are generic by design, because they must never carry trace text. Telling a T3 seed from a T1 seed still means reading the turn.
- **Knowledge-work filter.** The fit factor relies on Arena's metadata categories. Image work labelled `media_analysis` passes it.
- **Mapping depends on prose.** It follows other agents' prose `trace_signals`. If those change, the proposed ids change. Every proposed id is still a mode that has not been piloted for this seed.
- **`--llm` untested.** It has not run against the live API. No credentials were read.
- **Scan inputs and outputs live in scratch.** The extracted Oct-13 files (700 MB) and the scan outputs are in this session's scratchpad (`…/scratchpad/libC-WT90/`). Rerun `scan` to regenerate them; nothing under W or the repo depends on them.
