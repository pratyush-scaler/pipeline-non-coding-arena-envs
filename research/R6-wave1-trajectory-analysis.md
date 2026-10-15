# R6: Wave-1 V2 trajectory analysis. Why five dense V2 tasks scored pass@1 1.00 on both models

Date: 2026-10-02. This is read-only research. Every number below comes from the recorded screens under
`/Users/pratyushmohanty/Downloads/arena-envs-non-coding-v2/pipeline-artifacts/native/` (written `PA/` below) and the
bundles under `envs-v2*/`. Trajectories were parsed with `research/scripts/r3_common.py` (`events`, `norm`). The R6
scratch scripts lived in `/tmp/r6scratch/` and are not part of the checkout; §1.3 gives their method in full, so the
numbers can be regenerated.

**Harness, as measured.**
- Fable 5.1 (`anthropic/claude-fable-5-1`) in Claude Code 2.1.283.
- GPT-6 Astra (`openai/gpt-6-astra`) in Codex.
- Both at high effort, no turn or time limits, 5 episodes per model per task, protocol `arena-harbor-harness/4-step-history`.
- Two steps per task. Step 2 is a fresh session.

**Scope.** Five tasks, all built under the V2 difficulty doctrine (`pipeline/author/levers.py`), all screened 5x2. All
five scored pass@1 1.00 and mean reward 1.00 on both models. a-009's screen landed during this analysis and is
included.

| task | bundle | objective checks | fragility-budget entries | Fable pass@1 (valid/5) | Astra pass@1 (valid/5) | Astra voids replaced |
|---|---|---|---|---|---|---|
| a-013 | `envs-v2/target-F2-scenario/a-013-small-business-procurement-planning` | 8 | 14 | 1.00 (5) | 1.00 (5) | 1 |
| a-016 | `envs-v2/target-F2-scenario/a-016-crypto-social-marketing` | 32 | 23 | 1.00 (5) | 1.00 (5) | 4 |
| a-011 | `envs-v2/target-F2-scenario/a-011-public-policy-analytics` | 21 | 24 | 1.00 (5) | 1.00 (5) | 5 |
| a-049 | `envs-v2b/target-F2-scenario/a-049-small-business-planning` | 19 | 34 | 1.00 (5) | 1.00 (5) | 4 |
| a-009 | `envs-v2c/target-F2-scenario/a-009-market-research` | 9 | 27 | 1.00 (5) | 1.00 (5) | 0 |

All 14 Astra voids are `ApiRateLimitError`, i.e. OpenAI's tokens-per-minute limit ("Limit 2000000"). That is infrastructure
loss. Each void was replaced by a top-up episode, so every rate below is over 5 valid episodes per model.

---

## 0. Headline findings

1. **No lever bit in any of the 1,220 lever-episodes.** That is 122 fragility-budget entries x 10 episodes. No
   episode computed a graded value wrong and then corrected it. The doctrine assumes each fragile decision fails
   with q ~ 0.10-0.15. Here q is about 0: the rule-of-three upper bound under independence is about 0.25% per
   lever-episode. Multiplying such decisions with `(1-q)^n` buys nothing.
2. **The first problem is how the rules were written, not where.** Of the 122 entries, 96 are NEUTRALISED-BY-TEXT,
   14 SEEN-AND-HANDLED and 12 DESIGN-GAP (5 more are partial design gaps). None has NEVER-REACHED as its
   primary class. In every task the deciding rules are short, numbered or timestamped sentences in one or two hub documents:
   - a-013: a WhatsApp chat holds 11 of 14 entries.
   - a-016: a help centre holds 17 of 23.
   - a-011: the SOP and minutes.
   - a-049: seven partner chats.
   - a-009: one protocol.

   Many of these rules name the tempting wrong reading, the decoy column or the code to keep: "not added up and
   divided by four", "the 'Engagements' total ... play no part", the «م» status code, "if exactly 500 round up". The
   data often labels its own trap rows as well: `kind=estimate_alt`, "СМЕНА ОХВАТА", "تو لیست ما نیست" ("not on our
   list"), "$13.54 млрд x 62.71". Once read, each lever is one transcribed line of code.
3. **Every decisive line reached the screen.** Authored budget files were displayed in full (>=90%) in 86-95% of
   file-steps in a-013, a-016 and a-049, and by Fable in a-011. The exceptions: Astra in a-011 reached 69%,
   because it parsed the 27 KB CoC export by script without displaying it, and a-009 reached 60% / 46%, because
   its budget lists legacy files whose content is duplicated elsewhere.
   Trace-origin legacy files were displayed in 0-27%. The agents read every small, relevant-looking document and
   skip long generic background material (trace-origin plans, guides, prompt libraries, national extracts) and
   duplicates, which held no decisive fact. Language is not the discriminator: the authored files the agents read in
   full are in English, Persian, Arabic and Russian. The per-task analyses checked decisive lines
   against model-visible output: 20/20 steps in a-013 and a-016, 25/25 sentences in 10/10 step-1 episodes in a-011,
   32/33 lines in 20/20 steps in a-049, and 35 probes in 20/20 steps in a-009. **The reading-habit levers
   (`unflagged_document` x10 entries, `deep_in_long_document` x2) never had a decisive fact to hide:** each
   "unflagged" file was named or pointed to by the instruction or a hub file, and each long file was either named
   (re-read after truncation, 10/10) or redundant.
4. **The correct answer was often the agents' default code path.** At least 25 entries are lures that only a
   deviation from the default idiom would trigger:
   - a strict `>` average;
   - inclusive floor division;
   - exact string or slug joins;
   - `dict` last-wins, with re-pulls placed below the originals;
   - ties already in file order;
   - thread continuations typed `reply`;
   - untagged quotes with an empty `mentions` column;
   - exact full-name payer matching;
   - half-up ties that are exact in binary.

   The doctrine's habit claims ("Astra takes the first match", "Fable uses float round()") never engaged. Both
   models read small populations item by item and hard-code literal sets after reading (`derived = {('НАДТ', 2014)}`,
   `('Dahanu','1.7')`, `['AUD-04','MSC-03']`), so no habitual predicate ever ran on a trap member.
5. **The instructions leak HOW, though the hint lexicon finds nothing.** There are 0 `HINT_LEXICON` hits across 10
   step instructions, yet the instruction prose runs to 294-668 words (doctrine: 100-250). Every task's contract
   pre-explains levers through field definitions:
   - step-2 baselines ("the comparison is between those two applications of our rules");
   - event text that copies a clause's trigger ("confirmed in writing", "announced that it has updated its methodology");
   - named governing documents ("the current edition of our methodology protocol");
   - announced trap categories ("A post that counts for two campaigns appears in both lists");
   - rounding rules.

   Two leaks were forced by validity machinery:
   - a-013's step-2 baseline sentence came from a semantic-review finding (`verification/repair-log.json`).
   - a-049's `keep/stop` 20-dirham boundary was moved into the instruction to close a `contract.ambiguity:
     undefined-category` gate.
6. **Step 2 is recomputed from scratch.** In all five tasks both models re-derived the before and after states in the
   fresh step-2 session, e.g. `before, after = f(False), f(True)`. They used their own step-1 file only to check the
   baseline. Revision levers that assume an agent patches its step-1 output (`revision_scope`,
   `aggregate_propagation`, `readmission`, `attribute_not_in_step1`) were dead on arrival. The contracts asked for
   the two-state computation explicitly anyway.
7. **The reviewer predicted every outcome and nothing acted on it.** Each task's `difficulty_advisories` (copied into
   `screen.json` `review_advisories`) said, in substance, "several traps are expressly neutralised" and "a competent
   script ... may solve the task fully". By policy these are advisories, and the designer never saw them before the
   screen.
8. **Near-misses were rare, and every one was unbudgeted or latent.**
   - a-049 Fable weighed returned-goods cost (18.01 vs 20.59 would flip `keep` to `stop`).
   - a-049 Fable weighed referral date vs service date for one deal.
   - a-011 Astra re-coded the annual rule as an AND of two conditions in one step-2 episode. No data point separated
     that reading from the correct one, so it scored 1.00.

   These are the only places a model's reading actually diverged. They point at the mechanism that might work:
   decisions that no single sentence settles, plus data that separates plausible codings of a rule.

---

## 1. Data and method

### 1.1 Episodes and campaign paths

Valid episodes are the `report.json` `trials[]` with `valid: true`, from the campaigns and top-ups listed in each
bundle's `verification/screen.json` (`index.campaigns`, `index.topups`). Evidence citations in §3 use
`<campaign-short-id>/package__<trial>/<step>`. The full paths are below; the trajectory sits at
`PA/<path>/jobs/run/package__<trial>/steps/<step>/agent/trajectory.json`.

| task | model | campaign (under `PA/`) | valid trials | void trials (rate limit) |
|---|---|---|---|---|
| a-013 | fable | `screen-d95cfec6262e42409cfcd82e2fe9544f/calibration-af928e13687e496093c777e7f32ccf5d` | 47phQiL, H5cS52S, UDhfbup, n5uKAxG, pHxDGAw | - |
| a-013 | astra | `screen-d95cfec6262e42409cfcd82e2fe9544f/calibration-57d00ff6720d4c9ebed1a8a987029aef` | Y4kj79m, YwZdXEt, ZsaShTd, eEvo8zQ | qrnSaXa |
| a-013 | astra (top-up) | `screen-d95cfec6262e42409cfcd82e2fe9544f/calibration-2410d80a4e0740aa965e8c0b38dab171` | SC8sErk | - |
| a-016 | fable | `screen-7048ad3c19864a909887fead71f5f71d/calibration-8e30b0ce2468455aa8beb77ef1eac6a6` | 37hzGqt, 8GLSTvC, d87PexB, gEPgZPF, wQ2bu3d | - |
| a-016 | astra | `screen-7048ad3c19864a909887fead71f5f71d/calibration-49c71cb72cd14f9c9d11a3433a817e7d` | sGSK8z5 | 52RAsgR, RoqAti3, XCJUkdR, werYNR6 |
| a-016 | astra (top-up) | `screen-7048ad3c19864a909887fead71f5f71d/calibration-339c235fb2f641999db67d5d46539926` | WytivBh, oiWLcMp, wDbYR4x, yci3wqW | - |
| a-011 | fable | `screen-36f47afa2c484c79bf0091b5c5262897/calibration-4ba2c45fb61248f3bc2aee72c586db85` | JkpX24Q, da6uChv, kaM9Y2T, ptDQYh6, sKVjhs3 | - |
| a-011 | astra | `screen-36f47afa2c484c79bf0091b5c5262897/calibration-df3c534b07b6470f82f6d274992c1fc9` | - | KqwTHsg, LTqpRwr, agmrfVn, kqZZkZh, q4Vhqj3 |
| a-011 | astra (top-up) | `screen-36f47afa2c484c79bf0091b5c5262897/calibration-6fb76fd9656e439180bd3067ee67f59b` | 3UMdjEt, 7ubLmSd, 8QNy3iQ, 9iM4P7t, K7TWLUg | - |
| a-049 | fable | `screen-f8cdde1f4ee94032968f03c60ac0b393/calibration-237f3a1a129c49838773356f8ab88086` | MZRdb6e, PB3JULz, j8VFZiB, pCKdnkd, udvq5LZ | - |
| a-049 | astra | `screen-f8cdde1f4ee94032968f03c60ac0b393/calibration-33bd52eb4f144a3c83919ec26ce7fa73` | uGWpnp5 | CgRMJuX, UQydUFr, smUA95q, sqCoWPo |
| a-049 | astra (top-up) | `screen-f8cdde1f4ee94032968f03c60ac0b393/calibration-aefa433a63dc47fba3e749acae5df089` | P7cggFZ, YAqADbn, gvR7ZRp, oLtTjna | - |
| a-009 | fable | `screen-324259c3a03c41b7af7a2c25125c23d1/calibration-edb0d0cf52a443538c7f3312cf5416c9` | 7XPbk2D, CmCayFq, jcMEsTa, nH7ieR8, pQpid7y | - |
| a-009 | astra | `screen-324259c3a03c41b7af7a2c25125c23d1/calibration-033d1ae2c5c445adb399fd3b0dab3f4d` | Fk6YUYG, LKPjW4x, Mtbw7LT, wJ7xRnf, zhkk2X8 | - |

Each bundle's `environment/files` was verified byte-identical to the screened campaign's `package/environment/files`.

### 1.2 What was examined per task

- `authoring/spec.json`: `quality.fragility_budget`, `traps`, `checks`, `quality.counterexamples`, `quality.difficulty_case`.
- `steps/*/instruction.md`.
- `verification/semantic-review.json` and the `review_advisories` copied into `screen.json`.
- `verification/repair-log.json`.
- Every fixture file named in a budget entry.

For each of the 122 budget entries:
- the decisive sentence or row was located in the fixture (file:line);
- the mechanism was checked against the budget's claim;
- each valid episode's model-visible output, code and prose were searched for the decisive line and for explicit
  handling of the case.

Final answers need no separate check, because every check passed in every valid episode.

### 1.3 Reading metrics (method)

- **Exposure.** For each fixture file, every line with at least 12 normalised alphanumeric characters is a probe
  (`r3_common.norm`; tags stripped for HTML). A probe is "displayed" if it is a substring of the step's normalised
  model-visible tool output.
  - Claude Code: only the `<persisted-output>` preview counts for outputs over 30 KB. The appended raw stdout is
    discarded, as in R3.
  - Codex: the decoded `output` payloads.
- **Displayed bytes.** The byte-weighted share of probes displayed, times the file's size. Files with identical
  content (the `home/user/...` duplicates) are counted once, at the better of the two exposures.
- **Fully displayed** means at least 90% of probe bytes. **Opened** means the basename or path appears in a command
  or Read call, or at least 30% is displayed.
- **Tool calls** are raw `tool_calls` per trajectory step. For Codex the inner `exec_command` and `apply_patch`
  invocations are counted separately.
- **Wall time** is `step_results[].agent_execution` finish minus start, from the trial `result.json`.
- **Caveats.**
  - Exposure is a substring test, so a reformatted print, such as a parsed row printed as a dict, counts as unseen.
    Exposure is therefore a lower bound.
  - Codex reasoning is encrypted. Fable's `reasoning_content` is present in 37 of its 50 steps, usually as one or two short sentences. Any
    claim that a model "noticed" a trap rests on its code and visible prose, and is a lower bound.

---

## 2. Reading behaviour (Q2)

### 2.1 Per task, model and step (median over 5 valid episodes; per-episode rows in Appendix A)

| task | model | step | files (unique) | opened, median (range) | fully displayed, median | fixture KB (unique) | displayed KB, median | % | tool calls, raw / commands (median) | steps with truncated / persisted output | wall s, median |
|---|---|---|---|---|---|---|---|---|---|---|---|
| a-013 | fable | 01 | 12 (9) | 9 (9-9) | 5 | 117 | 54 | 46% | 7/7 | 0/4 of 5 | 144 |
| a-013 | fable | 02 | 12 (9) | 4 (4-8) | 4 | 117 | 29 | 25% | 5/5 | 0/2 of 5 | 90 |
| a-013 | astra | 01 | 12 (9) | 9 (9-9) | 6 | 117 | 76 | 65% | 6/11 | 5/0 of 5 | 98 |
| a-013 | astra | 02 | 12 (9) | 6 (4-7) | 4 | 117 | 42 | 36% | 4/7 | 1/0 of 5 | 66 |
| a-016 | fable | 01 | 12 (11) | 11 (11-11) | 6 | 113 | 70 | 62% | 8/8 | 0/2 of 5 | 148 |
| a-016 | fable | 02 | 12 (11) | 8 (6-11) | 5 | 113 | 66 | 58% | 6/6 | 0/0 of 5 | 131 |
| a-016 | astra | 01 | 12 (11) | 11 (11-11) | 8 | 113 | 82 | 73% | 6/13 | 5/0 of 5 | 83 |
| a-016 | astra | 02 | 12 (11) | 11 (6-11) | 8 | 113 | 97 | 86% | 5/11 | 5/0 of 5 | 71 |
| a-011 | fable | 01 | 19 (16) | 16 (16-16) | 13 | 470 | 132 | 28% | 15/15 | 0/5 of 5 | 185 |
| a-011 | fable | 02 | 19 (16) | 16 (13-16) | 13 | 470 | 128 | 27% | 13/13 | 0/5 of 5 | 160 |
| a-011 | astra | 01 | 19 (16) | 15 (13-16) | 9 | 470 | 96 | 21% | 8/13 | 5/0 of 5 | 129 |
| a-011 | astra | 02 | 19 (16) | 10 (9-12) | 8 | 470 | 84 | 18% | 6/10 | 5/0 of 5 | 64 |
| a-049 | fable | 01 | 25 (21) | 20 (20-21) | 17 | 211 | 107 | 51% | 17/17 | 0/5 of 5 | 201 |
| a-049 | fable | 02 | 25 (21) | 20 (19-21) | 17 | 211 | 103 | 49% | 11/11 | 0/5 of 5 | 170 |
| a-049 | astra | 01 | 25 (21) | 21 (19-21) | 17 | 211 | 124 | 59% | 9/15 | 5/0 of 5 | 173 |
| a-049 | astra | 02 | 25 (21) | 19 (19-20) | 17 | 211 | 110 | 52% | 8/13 | 5/0 of 5 | 88 |
| a-009 | fable | 01 | 20 (14) | 12 (7-14) | 9 | 182 | 143 | 79% | 14/14 | 0/5 of 5 | 168 |
| a-009 | fable | 02 | 20 (14) | 8 (5-9) | 5 | 182 | 91 | 50% | 10/10 | 0/4 of 5 | 119 |
| a-009 | astra | 01 | 20 (14) | 6 (5-7) | 5 | 182 | 90 | 49% | 7/12 | 5/0 of 5 | 117 |
| a-009 | astra | 02 | 20 (14) | 6 (5-7) | 5 | 182 | 89 | 49% | 6/10 | 5/0 of 5 | 73 |

### 2.2 Authored (budget) files versus trace-origin (non-budget) files

| task | budget files | budget KB | largest budget file KB | non-budget files | non-budget KB | budget file-steps fully displayed, Fable / Astra | non-budget file-steps fully displayed, Fable / Astra | `unflagged_document` / `deep_in_long_document` entries |
|---|---|---|---|---|---|---|---|---|
| a-013 | 5 | 45 | 18 | 7 | 131 | 92% / 86% | 0% / 24% | 1 / 0 |
| a-016 | 6 | 60 | 19 | 6 | 59 | 88% / 87% | 0% / 27% | 2 / 0 |
| a-011 | 8 | 116 | 35 | 11 | 697 | 95% / 69% | 45% / 23% | 3 / 0 |
| a-049 | 19 | 162 | 45 | 6 | 169 | 89% / 88% | 0% / 3% | 2 / 1 |
| a-009 | 11 | 154 | 45 | 9 | 103 | 60% / 46% | 32% / 13% | 2 / 1 |

### 2.3 What the reading data says

- **Every task took little reading effort.**
  - Fable used 5-19 tool calls per step and Astra 4-11 exec calls (6-18 commands).
  - Medians were 1-3.5 minutes per step.
  - The usual sequence was one listing, one or two batched `cat` calls of every relevant-looking file, one compute
    script, and one write.
- **The agents read the authored world in full.** Authored files were displayed in full in 86-95% of file-steps.
  There are two exceptions. Astra in a-011 reached 69%, because it parsed the CoC CSV by script. a-009 is lower
  because its budget lists redundant legacy files. Both models
  treat small business records as the case file, whatever the language:
  - chats
  - registers
  - statements
  - SOPs
  - minutes
  - help centres
  - protocols
- **They skip what looks like background.** Trace-origin files were mostly never displayed:
  - a-013: Persian prompt libraries and guides, 10-31 KB.
  - a-049: Arabic plans, 23-45 KB.
  - a-011: national extracts, 131-192 KB.
  - Every task: the `home/user/...` duplicates.
  - None of these held a decisive fact the agents lacked. The one exception, a-049's plan line 11, sits 799 bytes
    in under "اقرأ هذا قبل أي شيء" ("read this before anything"), and every episode reached it by grepping the
    instruction's own phrase.
- **Truncation happened only in named governing documents, and both models recovered every time (Fable 15/15,
  Astra 15/15 steps).** This covered the a-011 SOP (35 KB) and the a-009 protocol (45 KB):
  - Codex elided the middle of the first `cat` in 5/5 Astra episodes, and Astra re-read the missing line range with
    `sed -n` every time.
  - Claude Code showed the 2 KB preview. Fable said "The SOP is the governing document and got truncated. Reading it
    in full now", then read 120-200-line slices or used Read.

    The instruction named both documents as governing, and both carry a section map and cross-references.
- **Structured populations reach the script whole, whatever is displayed.** The a-016 posts CSV (19 KB) and the
  a-011 CoC export (27 KB) were not displayed in several episodes. Both were parsed with `csv.DictReader` over every
  row, so display coverage is the wrong exposure measure for tabular data.
- **Could the reading-habit levers bite? No, in all five tasks.**
  - The ten `unflagged_document` entries all sat in small files (0.7-13.6 KB) that the instruction named
    ("دفتري", "دفتر النقدية", "the Committee minutes") or that a hub document pointed to ("Account → Activity page",
    "the time printed next to 'Closes'", protocol 4.2 naming the intake journal and its `checked_by` column).
  - Both `deep_in_long_document` entries were redundant. a-049's market study repeats dates already in a 9 KB chat.
    a-009's dossier line uses the protocol's own verb, and both files were displayed 20/20.
  - The one real long-document event, Codex cutting a-011's SOP annexes, hit a document the agent already treated
    as governing, and it was recovered 10/10.


---

## 3. Per-task lever analysis (Q1, Q3, Q4)

Each section was produced by a dedicated sub-analysis over all 20 valid step-episodes of one task (5 Fable and 5
Astra, two steps each). It used the full model-visible output, code and prose of the original trajectories, plus
the fixture lines cited. Classes:
- **NEUTRALISED-BY-TEXT (NBT):** the deciding rule is stated plainly near the data, or in a file read early, so
  handling is trivial.
- **SEEN-AND-HANDLED (SAH):** found and handled correctly despite its placement.
- **NEVER-REACHED-BUT-IRRELEVANT (NRBI):** the agent never saw it, and did not need to.
- **DESIGN-GAP (DG):** the trap is not implemented the way the budget claims.

"5/5" means handled correctly in all five valid episodes; every check passed in every valid episode. Evidence is
cited as `<campaign-short-id>/package__<trial>/<step>`; the full paths are in §1.1.

### 3.1 a-013 small-business-procurement-planning

**Summary.** All 14 levers were defeated in all 20 step-episodes, and none of them was a close call. Eleven of the 14 budget entries cite one file, `M2GSTORE/chat/WhatsApp_Chat_M2G.txt` (13.6 KB, 126 lines). Every episode `cat`s that file in full in its first or second tool call, and it states every deciding rule as a plain sentence. Most of these rules even name the code or value to use: «م», "the model column decides", "if exactly 500 round up", "raised to 100,000,000 rial". Each agent then wrote one exact-arithmetic script, with integer half-up or `Decimal ROUND_HALF_UP` and a strict `>` against the average. Each step took 5–8 tool calls and 65–158 s. The step-2 instruction spells out the aggregate-propagation lever, and the pre-screen semantic review had already said the traps were "expressly neutralized".

Campaigns: Fable `af928e13` (all 5 episodes). Astra `57d00ff6` (Y4kj79m, YwZdXEt, ZsaShTd, eEvo8zQ; qrnSaXa was void) and top-up `2410d80a` (SC8sErk).

Abbreviations: "chat" = `M2GSTORE/chat/WhatsApp_Chat_M2G.txt`, "torob" = `exports/torob_recheck_1405-06-13.csv`, "note" = `notes/divar_yazd_cases_1405-06-13.md`. Counts are correct-handling episodes out of 5 per model. Every decisive file was displayed at 90% or more in 20/20 step-episodes; the HTML sheet is the one exception, noted in its row.

| # | budget id | lever (targets) | decisive text (file:line, short quote) | Fable | Astra | class | evidence |
|---|---|---|---|---|---|---|---|
| 1 | fb_half_up | rounding_tie_betrayal (both) | chat:102 "رند به هزار تومن؛ اگه دقیقاً پونصد شد بالا رندش کن" ("round to the thousand; if exactly 500, round up") | 5/5 | 5/5 | NEUTRALISED-BY-TEXT | Astra 5/5 `((floor*3+2500)//5000)*1000` plus a `ROUND_HALF_UP` cross-check (57d00ff6/package__Y4kj79m/01-task). Fable af928e13/package__47phQiL/01-task: `if rem > 500 or abs(rem-500) < 1e-9: return base+1000` |
| 2 | fb_status_codes | non_observation_rows (both) | chat:97 "کف ترب هر کالا میشه آخرین قیمتِ «م»…" (the floor is the latest «م» price). Legend at chat:79 | 5/5 | 5/5 | NEUTRALISED-BY-TEXT. Partial DESIGN-GAP: the rule names the code to keep, so the legend is never needed | 10/10 step-1 scripts contain `if r['وضعیت']=='م':` (e.g. 57d00ff6/package__eEvo8zQ/01-task). Fable 47phQiL: "'ت','ن','ک','د' rows… ignored" |
| 3 | fb_model_identity | near_twin_negative (astra) | chat:98 "ملاک ستون مدله، نه اینکه زیر کدوم کد سرچ زدی" (the model column decides, not the search code). The torob model strings equal the sheet's exactly | 5/5 | 5/5 | NEUTRALISED-BY-TEXT. An exact-string join is correct, and exact matching is Astra's default | Astra: `q['وضعیت']=='م' and q['مدل']==row['مدل']`. Fable n5uKAxG: "The Turbo listing Sina logged under the Superfast search belongs to CBL-01" |
| 4 | fb_price_rise | house_definition_vs_convention (fable) | chat:99 "قیمت جدید جای قیمت برگه رو می‌گیره، گرون‌تر شده باشه یا ارزون‌تر" (the new price replaces the sheet's, up or down) | 5/5 | 5/5 | NEUTRALISED-BY-TEXT. No prior pulls toward "keep the lower price" | `f = floor_by_model.get(model, sheet_floor)` (af928e13/package__47phQiL/01-task) |
| 5 | fb_drops | lexical_proxy (both) | chat:87 "(MSC-03) رو کلاً خط بزن"; :88 "اونم نمی‌گیریم"; :91 QCY "بمونه"; :93 lamp "نه… بمونه" | 5/5 | 5/5 | NEUTRALISED-BY-TEXT. The file is read whole, not grepped, so the grep mechanism never engages | 10/10 hard-code `['AUD-04','MSC-03']`. Fable UDhfbup: "QCY and the LED lamp stay" |
| 6 | fb_strict_average | house_definition_vs_convention (both) | chat:56 "…از میانگینِ مدلای توی لیست خریدمون بیشتر باشه سه تا" (above the average gets three); note:17 A36 = 17 | 5/5 | 5/5 | NEUTRALISED-BY-TEXT. The default `>` is the correct reading | Astra: `qty=3 if counts[r['مدل']]*n>s else 2` (57d00ff6/package__Y4kj79m/01-task). Fable 47phQiL: "average… is exactly 17.0, so Galaxy A36 5G at 17 ads stays at 2" |
| 7 | fb_twin_population | quantifier_scope_conflation (both) | note:22 "Redmi Note 15 Pro 5G \| 25 \| تو لیست ما نیست…" (not on our list); chat:56 "مدلای توی لیست خریدمون" (the models on our buy list) | 5/5 | 5/5 | NEUTRALISED-BY-TEXT. Averaging over the sheet's case rows excludes the twin and the total row automatically | Astra: `sum(counts[r['مدل']] for r in cases)`, with cases taken from the sheet. Fable types out a 15-model dict without the 5G row (47phQiL) |
| 8 | fb_groupB_base | unflagged_document (both) | chat:59 "نان‌آورها (گروه ب برگه) پایه‌شون از هر کدوم ۲ تا" (group B base is 2 each) | 5/5 | 5/5 | DESIGN-GAP plus NEUTRALISED-BY-TEXT. The chat is the hub file every agent opens first, not an unflagged one | 10/10: `elif r['گروه']=='ب': q=2` |
| 9 | fb_rial | convention_reach (astra) | chat:19/21/106 limits in "ریال" (rial). Worked conversion at chat:5 "165,000,000 ریال، یعنی همون 16,500,000 تومن". The instruction says "All money is in toman" | 5/5 | 5/5 | NEUTRALISED-BY-TEXT | Converted silently in all 10: `card = {'A': 10_000_000 - 150_000, 'B': 10_000_000}` (47phQiL) |
| 10 | fb_porterage | implicit_constraint_plan (fable) | chat:47 "سقف کارت یعنی جمع همه کشیدنای همون روز" (the card cap is every swipe that day); :111 porterage of 150,000 "با کارت من کشیده میشه" (goes on my card) | 5/5 | 5/5 | SEEN-AND-HANDLED (two plain messages to combine) | Fable 47phQiL: `# Reza's card also takes the 150,000 freight swipe on Sunday`. Astra SC8sErk: "reserve 150000 of Reza's card limit for Sunday freight" |
| 11 | fb_superseded_sms | first_match (astra) | chat:106 "سقف خرید روزانه کارت ****4093 به 100,000,000 ریال افزایش یافت" (raised to) | 5/5 | 5/5 | NEUTRALISED-BY-TEXT. The agents read the prose rather than regex-scanning it | Astra SC8sErk: "Sina's raised limit is 10000000". Fable H5cS52S: "the bank confirmed the increase on the 13th" |
| 12 | fb_inclusive_ten | convention_reach (both) | chat:66 "هیچ کالایی با اضافه‌هاش بیشتر از ده درصدِ همین ۱۸ میلیون نشه" (no item, with its extras, over 10% of the 18M) | 5/5 | 5/5 | NEUTRALISED-BY-TEXT. The default floor-division formula is inclusive | Astra: `(1800000-r['line_cost'])//r['buy_cap']`. Fable 47phQiL: "puts that SKU at exactly the 1,800,000 ten-percent ceiling" |
| 13 | fb_s2_cascade | aggregate_propagation (fable) | Step-2 instruction: "The comparison is between those two applications of our rules (with CSE-06 on the list, and without it)…" | 5/5 | 5/5 | NEUTRALISED-BY-TEXT (by the instruction itself) | Astra eEvo8zQ/02: "lowers the case-count average from 17 to 237/14. CSE-07 now exceeds that average". Fable 47phQiL/02: "mean today 16.93" |
| 14 | fb_cushion | interested_artifact_refuted (fable) | HTML sheet: "1,311,000 مانده چیست؟ عمداً گذاشتم" (what is the 1,311,000 leftover? I left it on purpose). Countered by chat:33–35 "۱۸ میلیون کامل فقط واسه جنسه" (the full 18M is only for goods) and by the instruction | 5/5 | 5/5 | NEUTRALISED-BY-TEXT (instruction plus chat) | The HTML was displayed fully in Fable 5/5 and Astra 3/5. All 10 run the four-step top-up, and none argues for keeping the cushion |

Two budget claims are slightly off:
- fb_half_up has four caps that land on .500, not three. Banker's rounding gives the same 98,000 on one of them, so three cases still differ.
- fb_status_codes says the legend lives "only in the chat", but the price rule itself names «م».

**Near-misses.** None of any substance.
- No episode produced a wrong value and then corrected it, and there were no tracebacks or assertion failures. The only non-zero exits were housekeeping: `ls` of a missing memory directory, and `tree` not installed.
- The hedges in final messages are correct and none decided an answer. Fable 47phQiL/01: "One assumption to flag: I applied all three limits… to Reza's PWR-01 extras… Neither limit was binding." Fable H5cS52S/01: "The bus tickets were swiped on the 12th, so they don't count against Sunday's limit."
- Fable H5cS52S/02 dismissed an unbudgeted decoy (retired group caps) unprompted.
- Self-verification is structural:
  - Fable asserted that its cap formula reproduces every unchanged printed cap.
  - Astra cross-checked its integer half-up against `Decimal ROUND_HALF_UP` in 5/5 episodes.

**Instruction leaks.**
- Step 1:
  - "The whole 18,000,000 toman is for goods tomorrow: get as close to it as our rules allow, never over." This kills fb_cushion.
  - "`qty` is the number of units on the base list, i.e. before any extra units bought with the leftover money." This reveals the base-plus-top-up structure.
  - "`pwr01`, `cbl02`, `cbl03` and `car02` are the extra units…" This names the four top-up SKUs.
  - "`reza_total` and `sina_total`" announces the per-payer split, and with it the card constraint.
  - "`repriced` — … whose Torob floor is now different from the floor printed on the market sheet" announces that prices changed.
  - "All money is in toman" points at the rial limits.
- Step 2:
  - "…different from the base-list quantity the same rules gave it last night with CSE-06 still on the list … The comparison is between those two applications of our rules (with CSE-06 on the list, and without it), not with whatever numbers were typed into last night's file." This is a procedure, and it pre-explains fb_s2_cascade.
  - "`fill_plan` — the same block as last night, recomputed for today."
  - The comparison sentence was added in repair: semantic-review pass 1 required the baseline to be published (`verification/repair-log.json`).

**Reading-habit levers.**
- unflagged_document is used once (fb_groupB_base). Its files, the chat (13.6 KB) and the sheet CSV (4.8 KB), are not named by the instruction ("Everything we have decided and checked is in the M2GSTORE folder"). Both were displayed at 90% or more in 20/20 step-episodes; the chat is always the first file `cat`ed.
- No entry uses deep_in_long_document. Every decisive file is 18 KB or smaller.
- The skipped files held nothing graded. These are the 10–31 KB trace-origin Persian guides; the only rule-like content in them is the retired group caps.

**Why the traps did not bite.**
- OBSERVED: the rules sit in one hub file that every episode reads first. 11 of 14 entries live in the 126-line chat, so there is one noticing trigger for the whole budget, not 14. The doctrine's independence condition ("different file, different noticing trigger") fails.
- OBSERVED: each rule names its own answer, in operational form: «م», the model column, "exactly 500 → up", "up or down", "raised to", "not on our list".
- OBSERVED: the correct reading coincides with the agents' default idiom on 5 entries: `>` (fb_strict_average), `//` (fb_inclusive_ten), exact string equality (fb_model_identity), `dict.get` replacement (fb_price_rise) and a join on sheet rows (fb_twin_population). A trap only bites when the default idiom gives the wrong answer.
- OBSERVED: the step-2 instruction does the cascade for the agent. 10/10 re-derived the average (237/14) and re-ran the top-up.
- OBSERVED: the grep and first-match levers never engaged. The 13.6 KB chat was read whole by models fluent in Persian.
- HYPOTHESIS: moving the same self-naming sentences into other files would not change the outcome. A rule must be correct only under a reading that contradicts the coding default.

### 3.2 a-016 crypto-social-marketing

**Summary.** Both models scored 1.00 on all 34 checks in all 10 valid episodes. Each episode got every value right on its first and only computation: no recomputed totals, no assertion failures, no corrections.
- 17 of the 23 budget entries are decided by one plain sentence in a single authored rulebook, `research/nucleus-help-center-articles.md` (15.8 KB, 268 lines). That rulebook was the second tool output in every step-1 episode.
- All 17 decisive help-center sentences, plus the decisive capture and activity rows, were on screen in 20 of 20 episode-steps.
- Both models turned the rulebook into one script of about 60 lines: a type filter, an @-tag set, `timedelta(hours=15)` day bucketing, a 3/2/2/1 score, a `(-score, created_at)` sort and a day loop.
- In step 2, all 10 episodes wrote `before, after = f(False), f(True)` and took set differences, which settled every revision lever structurally.

Campaigns: Fable `8e30b0ce` (all 5 episodes). Astra: sGSK8z5 in `49c71cb7`; WytivBh, oiWLcMp, wDbYR4x and yci3wqW in top-up `339c235f`, which replaced 4 rate-limit voids.

Abbreviations: "help" = `research/nucleus-help-center-articles.md`, "capture" = `research/halaman-kampanye-nucleus-2026-09-21.md`, "activity" = `exports/nucleus_account_activity_arunika_eth.csv`, NBT = NEUTRALISED-BY-TEXT.

| # | budget id | lever (targets) | decisive text (file:line, short quote) | Fable | Astra | class | evidence |
|---|---|---|---|---|---|---|---|
| 1 | fb_contribution_day | house_definition (both) | help:140 "starts at 15:00:00 UTC and ends at 14:59:59 UTC ... not tied to midnight in any time zone" | 5/5 | 5/5 | NBT | 8e30b0ce/package__37hzGqt/01 `def cday(t): return (t-dt.timedelta(hours=15)).date()`; 49c71cb7/package__sGSK8z5/01 likewise |
| 2 | fb_interaction_score | house_definition (fable) | help:150 "reply ... 3 points, every repost 2, every quote 2 and every like 1 ... the 'Engagements' total ... play no part". This names the decoy column | 5/5 | 5/5 | NBT | 8e30b0ce/package__8GLSTvC/01 `def score(r): return 3*int(r['replies'])+2*...`; 37hzGqt/01 "The MintABear post lost 25 Sep to the staking post on score, despite more likes" |
| 3 | fb_thread_head | counting_unit (fable) | help:105 "compared using the interaction score of that first post alone" | 5/5 | 5/5 | NBT (the lure is off the default path) | Thread continuations are `type=reply`, so the universal `type in ('post','quote')` filter drops them. Fable wQ2bu3d/01: `# replies (incl. thread continuations) & reposts never count` |
| 4 | fb_reply_proxy | lexical_proxy (astra) | help:99 "Replies to posts by other accounts ... are never credited, even when they tag a project" | 5/5 | 5/5 | NBT | All 10 use `if r['type'] not in ('post','quote')` |
| 5 | fb_repost_proxy | lexical_proxy (astra) | help:99 "Reposts are never contributions" | 5/5 | 5/5 | NBT | The same type filter |
| 6 | fb_quote_own_text | lexical_proxy (both) | help:122 "For a quote post we read only the text you added: the account you quoted is not treated as tagged" | 5/5 | 5/5 | DESIGN-GAP + NBT | The quote row has an empty `mentions` column and no "@" in its URL. Both default paths (the mentions column, or `@\w+` on the text) are therefore correct; only crediting `referenced_author` would fail |
| 7 | fb_quotes_count | lexical_proxy (fable) | help:99 "Your own standalone posts and your quote posts are contributions" | 5/5 | 5/5 | NBT | `('post','quote')` in all 10 |
| 8 | fb_hashtag_only | lexical_proxy (both) | help:122 "Hashtags and cashtags do not credit a post on their own" | 5/5 | 5/5 | NBT (the lure is off the default path) | The post's mentions column is empty, so any tag predicate excludes it. Fable 8GLSTvC/01: "only the #Beldex hashtag and $BDX cashtag has no @ tag and credits nothing" |
| 9 | fb_topic_not_tag | lexical_proxy (fable) | help:122 "credited ... when the text you wrote tags the project account" | 5/5 | 5/5 | NBT (the lure is off the default path) | Fable 37hzGqt/01: "The 26 Sep 'two leaderboards' post tagged only @NucleusCodes, so it went to Season 3" |
| 10 | fb_partner_plus_nucleus | nested_exception (both) | help:130 "When a post tags a partner project as well as @NucleusCodes, it is credited to that partner's opportunity only" | 5/5 | 5/5 | NBT | Astra sGSK8z5/01: `if code=='NUCLEUS_S3' and partners&mentions: continue` |
| 11 | fb_multi_partner | quantifier_scope (astra) | help:126 "credited to each of those opportunities", and the instruction: "A post that counts for two campaigns appears in both lists" | 5/5 | 5/5 | NBT (instruction leak) | Fable 37hzGqt/01: "The 25 Sep post tagging both @vangrid_io and @sleepagotchi counts in both campaigns" |
| 12 | fb_handle_case | surface_variant (astra) | help:124 "Handles are matched without regard to capitalisation" | 5/5 | 5/5 | NBT | All 10 call `.lower()` on handles and tags |
| 13 | fb_lookalike | near_twin (both) | help:124 "misspelt or look-alike handles are not recognised" | 5/5 | 5/5 | NBT (the default exact set membership is correct) | Fable 8GLSTvC/01: "tags the look-alike handle @vangridio, not @vangrid_io, so it is not recognised" (voiced in 5/5 Fable episodes) |
| 14 | fb_enroll_twin | unflagged_document (both) | activity:20 enrolled row `sleepagotchi-s3`; help:73 "the enrollment time we go by is the one recorded on your Account → Activity page" | 5/5 | 5/5 | NBT | Astra joins on the shared `slug` column (5/5). Fable 37hzGqt/01: "published before you enrolled on 23 Sep" |
| 15 | fb_close_by_date | unflagged_document (fable) | help:79 "closes at the time printed next to 'Closes' on its page, given in UTC"; capture:11 `2026-09-29T14:00:00.000Z` | 5/5 | 5/5 | NBT | Fable 37hzGqt/01: "went out 20 minutes after the 14:00 UTC close" |
| 16 | fb_tie_break | first_match (astra) | help:150 "If two posts have the same interaction score, the one published first is kept" | 5/5 | 5/5 | DESIGN-GAP + NBT | The tied pair sits in file order, earliest first, so first match, a stable sort and `max()` all give the right answer: the habit is correct here |
| 17 | fb_mint_sliver | convention_reach (astra) | help:142 "closes partway through a contribution day, that contribution day still counts" | 5/5 | 5/5 | NBT | The generic `while day_start < end` loop counts it (10/10) |
| 18 | fb_referral_twin | near_twin (astra) | capture:12 vs 13 (Season 3 contribution vs Referral S1): name, slug, type and dates all differ | 5/5 | 5/5 | DESIGN-GAP | Not a near-twin. No episode mentioned Referral |
| 19 | fb_window_eight | counting_unit (fable) | help:140 day definition; help:146 the seven-day cap is a mild counter-lure | 5/5 | 5/5 | SEEN-AND-HANDLED | Fable d87PexB/01: "The next-7-day window spans 8 contribution days" |
| 20 | fb_current_slot | convention_reach (both) | help:140/144/156 "never add to it" | 5/5 | 5/5 | SEEN-AND-HANDLED | Voiced in 5/5 Fable and 4/5 Astra episodes. Astra WytivBh/01: "Mint still has an unused slot in the current contribution day" |
| 21 | fb_readmission | readmission (both) | Step-2 instruction (the Discord quote): "Posts published since the original closing time are being tracked as normal" | 5/5 | 5/5 | NBT (instruction) | All 10: `before, after = f(False), f(True)` |
| 22 | fb_capacity_cascade | revision_scope (fable) | help:180 replacement rule plus the extension | 5/5 | 5/5 | SEEN-AND-HANDLED (structural) | Capacity is recomputed from the `after` state; all 10 reported 43 |
| 23 | fb_removed_loser | must_not_flag_twin (both) | help:180 "If a post that was being kept ... is removed, the ... next-highest ... takes its place" | 5/5 | 5/5 | SEEN-AND-HANDLED (structural, via set difference) | Fable d87PexB/02: "removal of 2103132361593600816 changes nothing. It was already set aside" (voiced in 3/5 Fable episodes). Astra handled it through the set difference without voicing it |

Totals:
- 18 NBT, including the entries whose lure was off the default path.
- 4 SEEN-AND-HANDLED.
- 3 DESIGN-GAP (rows 6, 16 and 18).
- 0 NEVER-REACHED.

**Near-misses.** None.
- Each episode printed one value of `slots_next_7_days` per state: 36 in step 1, and 36 then 43 in step 2.
- The only hedge, in Fable 37hzGqt/01 ("posts from the last 24 hours may not yet be visible ... so I counted them as standing"), concerns a point the instruction had already settled.
- Self-verification was anchored to the prior step: Astra WytivBh/02 asserts that its recomputed baseline equals its own step-1 `answer.json`.

**Instruction leaks.**
- Step 1:
  - "My X export for the period is in `exports/x_posts_arunika_eth_2026-09-21_2026-09-30.csv`" names the population file.
  - "It's now Wednesday 30 September 2026, 19:30 WIB (12:30 UTC)" pre-converts the time zone.
  - "you can treat anything still under review as standing."
  - "a thread is identified by the `tweet_id` of its first post" flags threads as a unit (fb_thread_head).
  - "A post that counts for two campaigns appears in both lists" fully pre-explains fb_multi_partner.
  - "0 for a campaign that has already closed" and "between now and the moment it closes" cue that a campaign has closed and that the exact close moment matters.
- Step 2:
  - The quoted Discord message states the readmission rule outright.
  - "'Immediately before these two updates' means the position as it stood a moment ago, when everything still under review was standing; after the updates, the three removed posts no longer count and everything else still under review keeps standing" prescribes the before/after recompute.
  - `now_scores` / `no_longer_scores` are defined as a literal set difference.
- Most of these are contract definitions needed for one defensible answer. In effect, though, the contract encodes the procedure.

**Reading-habit levers.** Neither unflagged_document entry had a chance to bite. The fixture has 12 files (11 unique); every decisive file is under 16 KB, has a descriptive name, and was listed by the first `find`/`rg --files`.
- fb_enroll_twin's file (1.6 KB) sits in `exports/` next to the named export, and help center 4.2 points to "Account → Activity".
- fb_close_by_date's file (2.7 KB) is pointed to by help center 4.3.
- Both were displayed in 20/20 episode-steps.
- No entry uses deep_in_long_document.
- The 19 KB x_posts CSV was not displayed verbatim in four step-1 episodes; in Astra wDbYR4x its `cat` sat in the elided middle of a truncated Codex batch. This did not matter: all 10 parsed it with `csv.DictReader` and computed over every row. A structured population file reaches the script whole, whatever is displayed.

**Why the traps did not bite.**
- OBSERVED: one rulebook neutralised 17 levers. Its name announces it as the rules ("help-center-articles"), and it reached the screen at observation 2 of 6-9 in every step-1 episode. Two episodes said outright that it beats the stale plan: Astra oiWLcMp/01 "differ from the older planning notes"; Fable d87PexB/01 "not from the master plan, which has the quota wrong".
- OBSERVED: the lures were off the default code path. Thread continuations are typed `reply`; the untagged quote has an empty mentions column; the hashtag-only and topic posts lack the handle; the capture and activity export share a `slug` key; and the tie-break "earliest" equals file order. Each misreading needed extra deliberate work, while the obvious script was correct by default. Both targeted habits (exact membership and first match) produce the right answer here.
- OBSERVED: the interpretive capacity decisions all fall out of one generic loop, `while day_start < end: if day not in kept: n += 1`, written unprompted 10/10.
- OBSERVED: the contract settled the step-2 levers. It defines changes as before/after differences and quotes the readmission rule, so all 10 episodes recomputed both states.
- HYPOTHESIS: a clean 48-row structured population plus one official rulebook gives these agents a deterministic program. For a trap to survive, the deciding fact must be one that a transcribed rule does not settle mechanically.

### 3.3 a-011 public-policy-analytics

**Summary.** Every one of the 24 budget entries resolved correctly in 10/10 episodes, with no wrong-then-corrected value on a graded field.
- Of 25 decisive sentences and rows checked against model-visible output, all 25 were visible in all 10 step-1 episodes. In step 2, 23/25 were visible in all 10.
- The SOP and both sets of minutes are named in the instruction and were fully read by both models. They state every operative rule once, plainly, and often name the wrong reading outright, so each trap became one line of transcribed code.
- Four levers resolve as a side effect of the obvious algorithm: residence attribution as D − out + in, rounding before classifying, re-pull rows placed below the originals, and an export that prints the indicator number on every row.
- One real long-document event occurred. Codex cut the SOP's annexes (including the Annex C legend) out of the middle of the output in 5/5 Astra first reads, and Astra re-read the missing range with `sed` 5/5.

Campaigns: Fable `4ba2c45`. Astra `6fb76fd` is the top-up; the first Astra campaign `df3c534` had 5 voids, all `ApiRateLimitError` (OpenAI's 2M tokens-per-minute limit), which is infrastructure, not a model result.

Abbreviations: "SOP" = `policies/Palghar_ABP_Data_Cell_SOP_v3.md` (34.9 KB); "May"/"Jul" = the two Review Committee minutes; "counts csv" = `exports/palghar_source_counts_Q4_FY2025-26.csv`.

| # | budget id | lever (targets) | decisive text (file:line, short quote) | Fable | Astra | class | evidence |
|---|---|---|---|---|---|---|---|
| 1 | fb_pooled | house_definition_vs_convention (both) | SOP:125 "never combined … not added up and divided by four" | 5/5 | 5/5 | NEUTRALISED-BY-TEXT | 6fb76fd/package__3UMdjEt/01 `n=sum(ns); d=sum(ds)` |
| 2 | fb_halfup | rounding_tie_betrayal (both) | SOP:143 "exactly half-way … the higher hundredth is shown" | 5/5 | 5/5 | NEUTRALISED-BY-TEXT | All use ROUND_HALF_UP. 4ba2c45/package__sKVjhs3/01: "Ordinary spreadsheet rounding would show 40.07, 55.62 and 90.62" |
| 3 | fb_gap_stage | rounding_stage (astra) | SOP:145 "worked out from the two figures exactly as they are printed" | 5/5 | 5/5 | NEUTRALISED-BY-TEXT | 6fb76fd/package__3UMdjEt/01 `v=q(…); gap=q(v-s)` |
| 4 | fb_repull | first_match (astra) | SOP:320 "only the row with the highest upload sequence is used"; the seq-2 rows sit after seq 1 | 5/5 | 5/5 | NEUTRALISED-BY-TEXT, plus weak placement: a last-row-wins dict is also right | All episodes: `if key not in latest or int(r['upload_seq'])>…` |
| 5 | fb_memo | non_observation_rows (both) | SOP:318 "R lines are already contained in the D line … they are not further births" | 5/5 | 5/5 | NEUTRALISED-BY-TEXT | 6fb76fd/package__3UMdjEt/01 key `(lgd,kpi,measure,'D','')` |
| 6 | fb_denominator | house_definition_vs_convention (fable) | `research/indicators.txt` numerator/denominator columns; SOP Annex E restates every base in prose | 5/5 | 5/5 | NEUTRALISED-BY-TEXT | Astra `definitions` dict: 'Operational AWCs', 'GPs with BharatNet', … |
| 7 | fb_nqas | lexical_proxy (both) | indicators.txt:67-70 "NQAS certified facilities in block + no. of state NQAS certified"; SOP:363 | 5/5 | 5/5 | NEUTRALISED-BY-TEXT | 6fb76fd/package__3UMdjEt/01 `'1.4':(['…(national certification)','…(state certification)'],…)` |
| 8 | fb_backfill | fill_the_gap (fable) | SOP:129 "never turned back into a count to fill the hole"; counts csv:131 remark "not received from CDPO Talasari"; the instruction offers null | 5/5 | 5/5 | NEUTRALISED-BY-TEXT | 4ba2c45/package__da6uChv/01 "the dashboard percentage must not be worked back into a count" |
| 9 | fb_margin | unflagged_document (both) | Jul:50 "margin of 12 … is reduced to 10"; SOP:169 "as amended by any later minutes, are the authority" | 5/5 | 5/5 | NEUTRALISED-BY-TEXT (the file is not unflagged) | 4ba2c45/package__da6uChv/01 "Margin of 10 pp, not the 12 pp still quoted in the SOP's summary" |
| 10 | fb_annual + fb_carveback + fb_carve_polarity | nested_exception ×2, lexical_proxy | May:41, one paragraph: list by number → "less than two-fifths" → "applies only to indicators where more is better … never brought back on this ground" | 5/5 | 5/5 | NEUTRALISED-BY-TEXT | 6fb76fd/package__8QNy3iQ/01 `marked=positive and v<Decimal('0.4')*s` |
| 11 | fb_campaign + fb_campaign_annual | unflagged_document, nested_exception | Jul:44, in bold: "**Decision.** … A block below 98 per cent on any of the six is marked for action … the once-a-year arrangement in item 3.4 … do not apply" | 5/5 | 5/5 | NEUTRALISED-BY-TEXT; partial DESIGN-GAP | The budget says the item is "phrased as a campaign close-out rather than a marking rule", but it is a bold Decision using the instruction's own phrase "marked for action" |
| 12 | fb_hold | nested_exception (both) | May:43-49 (3.5a/b); Jul:31,34 already list the items as "remains on the verification list" | 5/5 | 5/5 | NEUTRALISED-BY-TEXT | Astra `if v==0: verify=count(…den)>0` |
| 13 | fb_deferral | unflagged_document (both) | Jul:56 "For Dahanu block, the TB treatment success indicator (1.7) is deferred" | 5/5 | 5/5 | NEUTRALISED-BY-TEXT | All 10 hard-code `('Dahanu','1.7')`. The decoy (the Vikramgad 3.3 lab closure, explained but never decided) was rejected explicitly in 2 Fable episodes |
| 14 | fb_assurance | unverifiable_authority (fable) | email:11 "Madam was kind enough to agree" vs May:51 "Assurances given during field visits … do not change the marking" | 5/5 | 5/5 | NEUTRALISED-BY-TEXT: the rule names the exact channel the email uses | 4ba2c45/package__da6uChv/01 "Under item 3.6 … that cannot change the marking" |
| 15 | fb_counts | house_definition_vs_convention (astra) | May:39 "they are not marked"; the state CSV has a `Unit=Number` column | 5/5 | 5/5 | NEUTRALISED-BY-TEXT (also by the data column) | Astra `if s['Unit']=='Number': continue` |
| 16 | fb_swap | surface_variant_identity (astra) | The CoC export rows carry `Indicator number` | 5/5 | 5/5 | DESIGN-GAP: row order cannot matter in a long-form export; the swap survives only in `uploads/*.txt`, which no check needs | `state={r['Indicator number']:…}` |
| 17 | fb_scope | revision_scope (both) | step-2 instruction: "each block's figure (Dahanu, Jawhar, Talasari, Vikramgad)" and the comparison against the sheet "as it correctly stood" | 5/5 | 5/5 | NEUTRALISED-BY-TEXT (the instruction forces a full recompute) | Astra 6fb76fd/package__7ubLmSd/02 `before = classify(False); after = classify(True)` |
| 18 | fb_outside | attribute_not_in_step1 (both) | counts csv:18-19 R "Outside district (Dadra and Nagar Haveli)" | 5/5 | 5/5 | SEEN-AND-HANDLED (the obvious algorithm drops it) | 4ba2c45/package__JkpX24Q/02 "Talasari's births to mothers from Dadra and Nagar Haveli dropped" |
| 19 | fb_nonabp_lines | attribute_not_in_step1 (astra) | counts csv:30-41 (Mokhada/Wada/Palghar facility R lines); SOP:318 "covers every rural taluka" | 5/5 | 5/5 | SEEN-AND-HANDLED | 6fb76fd/package__7ubLmSd/02 "including births at facilities outside the four blocks" |
| 20 | fb_confirmed_zero | readmission (fable) | May:45 "after which the item is judged like any other" | 5/5 | 5/5 | NEUTRALISED-BY-TEXT: the step-2 instruction repeats the trigger word for word | Astra `confirmed_zero = revised and (b,k)==('Dahanu','4.4')` |
| 21 | fb_printed_line | convention_reach (astra) | SOP:147 "any line the Committee has drawn is judged on the figures as printed" | 5/5 | 5/5 | NEUTRALISED-BY-TEXT | 4ba2c45/package__sKVjhs3/02 "At full precision the figure is 53.7647, which would exceed the three-times line. I followed SOP 8.5" |

Rows 10 and 11 group five entries that share one paragraph or decision (24 entries in 21 rows).

Totals:
- 22 NEUTRALISED-BY-TEXT, one of them with a partial DESIGN-GAP.
- 1 DESIGN-GAP (fb_swap).
- 2 SEEN-AND-HANDLED by the default algorithm.
- 0 NEVER-REACHED.

**Near-misses.** No graded value was ever computed wrong and then corrected.
- Astra 8QNy3iQ/01, 9iM4P7t/01 and K7TWLUg/01 raised AssertionErrors in *optional* checks of the CoC values against the `uploads/` national extracts. The failures were precision and column-order mismatches, which Astra fixed by mapping columns by header ("Mappings follow the inspected indicator headings, including SHC before PM-KISAN"). This is the only place the heading-swap lever had any effect, and nothing grades it.
- Fable sKVjhs3/01 hit `TypeError: Fraction * Decimal` in the two-fifths test and re-ran it.
- Judgment calls voiced (Fable only):
  - Talasari FHTC stays marked.
  - The Vikramgad 3.3 lab-closure decoy stays marked because "no deferral was recorded".
  - Dahanu 1.13 at 97.91 sits against the 98 line.
  - kaM9Y2T/02: "the result for those two depends on the SOP's half-up and 'more than' rules being applied as written".
  - Each was resolved by quoting the on-screen rule.
- A latent divergent reading the data never tests: Astra 7ubLmSd/02 re-coded the annual rule as requiring both "more than 10 behind" AND "below two-fifths", where its step-1 code required only the second. Every annual State figure is above 32, so the two readings coincide. An annual indicator with a State figure under 16.7 would have separated them.

**Instruction leaks.**
- Step 1:
  - "our last KPI table carried figures under the wrong headings and had to be withdrawn" announces fb_swap.
  - "Jawhar (Jawahar in NITI's files)" pre-resolves the name variant.
  - "Everything I have — the exports, the Data Cell SOP, the Committee minutes, the State Cell's circular, NITI's indicator sheet, the national extracts and the mails" names every governing document class, so no document is unflagged.
  - "for the four blocks taken together" echoes SOP 7.2's pooling.
  - "or null where the Data Cell's rules do not allow a figure to be stated" signals fb_backfill.
  - "allowing for whether a higher or a lower figure is better" gives the polarity.
  - "marked for action at this review" is the July decision's own phrase.
- Step 2:
  - "worked out from the residence lines in the Data Cell's source-count export" names the file, the rows and the method.
  - "confirmed in writing that Dahanu block's zero … is the real position" copies the 3.5(a) trigger word for word, and "No written confirmation has come for any other block" settles Talasari.
  - "compared with the sheet as it correctly stood before them under the same rules" tells the agent to rebuild the baseline.
  - "on this indicator a lower figure is better" restates the polarity.

**Reading-habit levers.**
- unflagged_document (fb_margin, fb_campaign, fb_deferral):
  - All three live in the July minutes (8.7 KB, 89 lines). The operative Decisions sit 46–66% of the way in.
  - The instruction names "the Committee minutes", and the SOP points to them twice.
  - The wording reuses the instruction's vocabulary ("marked for action", "margin", "red list").
  - The minutes were displayed in 10/10 step-1 episodes, with all three Decisions visible. The lever had no chance to bite.
- deep_in_long_document: no budget entry uses it, but it fired on its own. The SOP is 34.9 KB, with Annex C 66% of the way in.
  - Astra: Codex elided the middle of the first `cat` ("Warning: truncated output (original token count: 13096)"), removing the annex block, in 5/5 episodes. Astra re-read the missing range with `sed -n '245,460p'` and similar in 5/5.
  - Fable got the 2 KB persisted preview and wrote: "The SOP is the governing document and got truncated. Reading it in full now". It then read 140–200-line `sed` chunks.
  - HYPOTHESIS: they recovered because the file is named in the instruction, SOP §0 maps the annexes, and §4.3/§7.5 cross-reference "Annex C".
- The CoC export (26.7 KB) was displayed by Astra 0/5. Astra parsed it with `csv.DictReader` keyed on `Indicator number`, asserting 152 rows. A structured file reaches the script whole.
- The `uploads/*.txt` national extracts (131–192 KB, two copies each) are 73% of the unique fixture bytes. They were only ever named, never displayed, and no check needs them.

**Why the traps did not bite.**
- OBSERVED: every operative rule is stated once, plainly, in a document the instruction names, and both models read it in full. The SOP often names the wrong reading itself: "not added up and divided by four", "never turned back into a count", "they are not further births", "judged on the figures as printed".
- OBSERVED: both models turn the rulebook into one classifier: Astra's `classify()`, Fable's `DEFERRED/CAMPAIGN/YEARLY/MARGIN` constants. Nested exceptions written in one paragraph and keyed by indicator number become nested `if`s.
- OBSERVED: the obvious algorithm resolves several levers without anyone noticing:
  - D − out + in handles fb_outside and fb_nonabp_lines.
  - Round-then-classify handles fb_gap_stage and fb_printed_line.
  - Re-pulls placed below the originals handle fb_repull.
  - Numbered long-form rows handle fb_swap.
- OBSERVED: the instructions pre-solve or flag at least 8 levers.
- HYPOTHESIS: the 24 entries collapse to roughly 8 independent noticing triggers. That count is this analysis's estimate; semantic-review advisory 3 says only "The claim of about twenty independent judgments should not be inferred from field or trap counts". With q close to 0 on rules stated outright, density cannot move pass@1.

### 3.4 a-049 small-business-planning

**Summary.** None of the 34 budget entries bit, and none was missed in reading.
- 32 of 33 decisive probe sentences were visible in model-visible output in 20/20 steps. The 33rd (Nukhba "الاتفاق خلص يوم 15") was visible in 19/20.
- Every file that decides a check is 0.7–12.4 KB. Both models `cat` them in full in step 1 (Fable loops `cat` over all seven chats; Astra batches them), then hand-code a per-deal decision for every referral.
- The partners' own payment messages work as an answer key: 15 of the 26 step-1 due commissions are stated verbatim by a partner.
- The reviewer's advisories had already said that several traps are "explicitly neutralised by legitimate public evidence".

Campaigns: Fable `237f3a1a` (all 5 episodes). Astra: uGWpnp5 in `33bd52eb`; P7cggFZ, YAqADbn, gvR7ZRp and oLtTjna in top-up `aefa433a`, which replaced 4 rate-limit voids.

| # | budget id(s) | lever (targets) | decisive text (file:line, short quote) | Fable | Astra | class | evidence |
|---|---|---|---|---|---|---|---|
| 1 | fb_vat_base | house_definition (both) | Sanaiya:7 "ولا تدخل فيها ضريبة القيمة المضافة إن كان الشريك يحصّلها"; the partner pays at Sanaiya:71 "حولت 680 (أبو خالد 180 + سالم 500)" | 5/5 | 5/5 | NEUTRALISED-BY-TEXT | 237f3a1a/pCKdnkd/01 "أبو خالد 1,890 ÷ 1.05 ثم 10% = 180، وهذا اللي دفعوه فعلاً"; aefa433a/gvR7ZRp/01 `if p in {'1','4','5'}: amt/=D('1.05')` |
| 2 | fb_flat_fee_revision | first_match (astra) | Sanaiya:53 "والحماية الكاملة نخليها لك 500 ثابتة بدل 400"; :71 "سالم 500" | 5/5 | 5/5 | NEUTRALISED-BY-TEXT: the chats are never regex-scanned, so first match cannot fire | gvR7ZRp/01 `if p=='1' and n in {59,87}: raw=D(500)` |
| 3 | fb_jimi_twin | near_twin_negative (both) | Jimi:4 "لا مستقل، نفس الاسم التجاري بس الرخصة والمالك غير"; :40 "حولت 900 عن خليفة" | 5/5 | 5/5 | NEUTRALISED-BY-TEXT | All 10 output deal 63 = 900 |
| 4 | fb_proposal | unverifiable_authority (fable) | Jimi:46–47 proposal answered with "خلني أفكر فيها"; clause 8 requires written consent; the partner itself paid 12% on March jobs | 5/5 | 5/5 | NEUTRALISED-BY-TEXT | 237f3a1a/PB3JULz/02 "ما انقبل كتابةً منك، والبند 8 يشترط موافقة الطرفين" |
| 5 | fb_ramadan_scope | deep_in_long_document (both) | The operative text is in the 9 KB Waha chat (:49 "الزباين اللي ترسلهم لنا … لين آخر يوم في رمضان … عشرة بالمية"). The 45 KB market study only repeats the dates | 5/5 | 5/5 | DESIGN-GAP (the long file is not needed), then SEEN-AND-HANDLED (scope by referral date) | Astra 5/5 `'2027-02-08'<=referral_date<='2027-03-08'`. The partner's wrong 99 for deal 62 was rejected 10/10 |
| 6 | fb_ramadan_service | lexical_proxy (astra) | Waha:49, same message: "السيراميك ما عليه شي يظل مثل ما هو" | 5/5 | 5/5 | NEUTRALISED-BY-TEXT | Astra 5/5 `row['الخدمة']=='تظليل'` |
| 7 | fb_full_payment | nested_exception (both) | Rawaa:13 "لا تُستحق العمولة عن أي عقد إلا بعد أن يسدد الزبون كامل قيمة العقد"; the deal-log note on row 70 | 5/5 | 5/5 | NEUTRALISED-BY-TEXT | YAqADbn/01 `(partner=='4' and paid<contract_value)` |
| 8 | fb_instalments | nested_exception (fable) | Bustan:15 "بنود خاصة (تُقدَّم على البند 2 فيما يخالفه)". This is stated precedence, which the doctrine lists as DEAD | 5/5 | 5/5 | NEUTRALISED-BY-TEXT | udvq5LZ/01 "لأن العمولة تُستحق مع كل دفعة" |
| 9 | fb_cap | quantifier_scope (astra) | Bustan:15 "على ألا يتجاوز مجموع العمولة عن المشروع الواحد 1,500 درهم"; :39 "حولت 1,500 عن أم راشد (السقف)" | 5/5 | 5/5 | NEUTRALISED-BY-TEXT | YAqADbn/01 `min(paid/D('1.05')*D('.05'), D('1500'))` |
| 10 | fb_trial_rate, fb_renewal_scope | retired_identifier_residue (both); rules_stack_not_first_match (astra) | Darb:29 "من اليوم أي شغل نخلصه نحسب لك عليه ثمانية بالمية مب عشرة، حتى الزباين اللي أرسلتهم قبل وما خلصوا" | 5/5 | 5/5 | NEUTRALISED-BY-TEXT: the scope is in the same sentence, and nothing stacks, so the "stacking" label does not fit | gvR7ZRp/01 `if p=='6' and r['تاريخ التنفيذ']>='2027-03-01': rate='0.08'` |
| 11 | fb_survival | nested_exception (fable) | Nukhba clause 7 "وتبقى العمولة مستحقة عن كل زبون أُحيل قبل انتهاء الاتفاق"; :30 "الاتفاق خلص يوم 15" | 5/5 | 5/5 | NEUTRALISED-BY-TEXT | PB3JULz/01 "الإشعار يوم 1/2 أنهى الاتفاق يوم 15/2" |
| 12 | fb_attribution | lexical_proxy (astra) | The deal-log note on row 80 states the conclusion: "حجز بالتلفون وما ذكر عناية العين" | 5/5 | 5/5 | NEUTRALISED-BY-TEXT | YAqADbn/01 `or deal==80` |
| 13 | fb_fleet | lexical_proxy (fable) | deal-log 71: paid 0, "فاتورة آجلة 30 يوم"; Sanaiya:79 "العمولة لما يدفعون" | 5/5 | 5/5 | NEUTRALISED-BY-TEXT | MZRdb6e/01 "النور للمقاولات (فاتورة آجلة)" |
| 14 | fb_logged_value | unflagged_document (fable) | notebook:64 "للتقدير السريع بس … مش هو حساب التسوية". The instruction names the notebook ("دفتري") and says "مش تقديرات" | 5/5 | 5/5 | DESIGN-GAP (the file is flagged) and NEUTRALISED-BY-TEXT | The notebook was displayed 100% in 20/20 steps |
| 15 | fb_ties | rounding_tie_betrayal (fable) | Every agreement, clause 5: "ونصف الدرهم يُجبر للأعلى". The partner payments 149, 125 and 155 are themselves the tie answers. No tie sits on a binary-float edge | 5/5 | 5/5 | DESIGN-GAP (the float-edge claim) and NEUTRALISED-BY-TEXT | j8VFZiB/01: float `int(math.floor(x+0.5))` is still correct |
| 16 | fb_rounding_stage | rounding_stage (astra) | clause 5 "تُحسب عمولة كل صفقة وحدها وتُقرَّب"; the output contract defines `outstanding_aed` as the sum of the integer `commission_aed` values | 5/5 | 5/5 | DESIGN-GAP (the stage is pinned by the contract) | All episodes summed per-deal integers |
| 17 | fb_january | non_observation_rows (both) | notebook:82 "أي عمولة تخص زبون أرسلته قبل 1 فبراير انحسبت وانقبضت"; bank refs "COMM JAN 2027" | 5/5 | 5/5 | NEUTRALISED-BY-TEXT | Astra 5/5 `'JAN' in row['المرجع']` |
| 18 | fb_rtn | non_observation_rows (astra) | bank:22 "BENEFICIARY NAME MISMATCH - REF 0225,RTN"; codes:9 "الحوالة المرجعة تعامل كأنها لم تستلم" | 5/5 | 5/5 | NEUTRALISED-BY-TEXT | Astra 5/5 `elif code=='RTN': received[p]-=…` |
| 19 | fb_typing | surface_variant_identity (astra) | bank:19 "GOLDEN TOUCH TYPING SERVICES,GOOGLE MAPS PROFILE"; notebook:97 explains it | 5/5 | 5/5 | DESIGN-GAP (the trap needs a fuzzy matcher, but Astra's exact full-name dict excludes it by default) and NEUTRALISED-BY-TEXT | Astra 5/5 `'GOLDEN TOUCH AUTO ACC FIXING LLC':'1'`; Fable 4/5 mention the 450 explicitly |
| 20 | fb_cash | unflagged_document (both) | cash_book:5 "درب البر … 420"; Darb:22 "استلمت 420 كاش". The instruction names "دفتر النقدية" and says "(تحويل أو كاش)" | 5/5 | 5/5 | DESIGN-GAP (the file is flagged) and NEUTRALISED-BY-TEXT | The 741 B file was displayed in 20/20 steps |
| 21 | fb_fee_lines | counting_unit_boundary (fable) | courier terms §5 "سطر RAT ليس شحنة جديدة؛ هو رسوم إضافية على شحنة قائمة" | 5/5 | 5/5 | NEUTRALISED-BY-TEXT | All dedupe on the AWB number |
| 22 | fb_per_order | counting_unit_boundary (both) | Plan line 11, 799 bytes into a 25 KB file, under "اقرأ هذا قبل أي شيء" | 5/5 | 5/5 | NEUTRALISED-BY-TEXT | Found 10/10 by grepping the instruction's own phrase (`grep -n "20 درهم\|الربح الحقيقي"`) |
| 23 | fb_input_vat | house_definition (fable) | notebook:85 "تكلفة القطعة عندي = اللي دفعته للمورد عنها شامل الضريبة" | 5/5 | 5/5 | NEUTRALISED-BY-TEXT | Astra 5/5 `D('24')*D('1.05')` |
| 24 | fb_units | counting_unit_boundary (astra) | The statement column "عدد القطع" is 2 on the 178 bundles | 5/5 | 5/5 | SEEN-AND-HANDLED | Astra 5/5 `sum(int(r['عدد القطع']) …)` |
| 25 | fb_campaigns | lexical_proxy (astra) | notebook:86 "أي حملة للمنتجات اسمها يبدأ بكود المنتج" | 5/5 | 5/5 | NEUTRALISED-BY-TEXT | 10/10 `startswith(sku)` |
| 26 | fb_return_date | attribute_not_in_step1 (astra) | step-2 news 8: "على كل شحنة رجعت للمرسل من 1 مارس 2027" | 5/5 | 5/5 | NEUTRALISED-BY-TEXT (by the instruction) | Astra 5/5 `r['تاريخ الحالة']>='2027-03-01'` |
| 27 | fb_cutoff | revision_scope (fable) | The step-2 instruction restates "لحد نهاية يوم الخميس 11 مارس 2027" | 5/5 | 5/5 | NEUTRALISED-BY-TEXT (by the instruction) | 10/10 "سدّد يوم 13 مارس، بعد تاريخ التسوية" |
| 28 | fb_cap_refund | revision_scope (both) | 63,000 − 6,300 = 56,700; ex-VAT ×5% = 2,700, still above the 1,500 cap | 5/5 | 5/5 | SEEN-AND-HANDLED | gvR7ZRp/02 "تعويض أم راشد ما بيغيّر عمولتها" |
| 29 | fb_vat_partner | near_twin_negative (both) | news 1: "اعتباراً من 1 مارس 2027، وكل إيصال طلع منهم من هداك اليوم" | 5/5 | 5/5 | NEUTRALISED-BY-TEXT (by the instruction) | Deal 74 untouched 10/10 |
| 30 | fb_vat_date | attribute_not_in_step1 (both) | Deal 78 service date 2027-03-01 | 5/5 | 5/5 | SEEN-AND-HANDLED | Fable "139 ← 132" |
| 31 | fb_readmission | readmission (both) | news 2 + clause 3 second limb + Jimi VAT gives 1,400 × 12% = 168 | 5/5 | 5/5 | SEEN-AND-HANDLED | MZRdb6e/02 "صارت `due` بعمولة 168" |
| 32 | fb_bounced_cheque | readmission (both) | news 6: the cheque bounced and half is paid; the Rawaa full-payment clause applies | 5/5 | 5/5 | SEEN-AND-HANDLED | 10/10: deal 76 becomes `not_yet_due` |
| 33 | fb_booking_claim | must_not_flag_twin (fable) | clause 3 first limb; deal-log row 89 sent 03-09, served 03-10 | 5/5 | 5/5 | SEEN-AND-HANDLED | j8VFZiB/02 "فينطبق عليه الشق الأول من البند 3 بغض النظر عن حجزه السابق" |

Totals: 22 ids NEUTRALISED-BY-TEXT, 6 SEEN-AND-HANDLED (five of them in step 2), 6 DESIGN-GAP (each also neutralised), 0 NEVER-REACHED.

**Near-misses.** No episode computed a wrong value and then corrected it. The closest calls were unbudgeted:
- **Returned-goods cost (would flip a decision).** 237f3a1a/MZRdb6e/01 computed an alternative "(if RTO cogs lost: 18.0125)" for PH-02, which would turn `keep` into `stop`. It chose 20.59 because courier §4 says "تُعاد البضاعة للتاجر بحالتها". j8VFZiB/01 and pCKdnkd/01 said the same.
- **Voiced judgment call.** 237f3a1a/pCKdnkd/01: "لو حسبت علي الكتبي على تاريخ التنفيذ بدل تاريخ الإرسال لتطلع عمولته 120 بدل 80، بس نص اتفاق أبو سعيد يتكلم عن الزبائن 'اللي ترسلهم'". It recovered on the verb "ترسلهم" (send) in Waha:49.
- **Float arithmetic survived by construction.** Fable used float with `floor(x+0.5)`. Python's bare `round()` would have produced the wrong integer on six ties, but no episode used it on a final value.

**Instruction leaks.**
- Step 1:
  - "سجل الصفقات … سجل الشركاء، محادثات الواتساب مع الشركاء (فيها الاتفاقات)، كشف حسابي البنكي، دفتر النقدية، دفتري، وملفات تجربة المنتجين" lists every authored source, says where the rules live ("the agreements are in the chats"), and names both "unflagged" documents.
  - "بدي أرقام تطلع من الاتفاقات والسجلات نفسها، مش تقديرات" pre-explains fb_logged_value.
  - "حسب قاعدة الـ20 درهم اللي بخطتي" and "الربح الحقيقي للطلب بالمعنى اللي بتستخدمه خططي" supply the exact grep phrase that lands on the plan line.
  - "(تحويل أو كاش) … كعمولة عن إحالات هالفترة" flags cash and excludes January and side-job receipts.
  - "مقرّب لمنزلتين عشريتين (النص يُقرّب للأعلى)" puts a rounding rule in the instruction (doctrine: dead).
  - `outstanding_aed` is defined as a sum of `commission_aed`, which pins the rounding stage.
- Step 2:
  - News 1 and 8 carry their scoping attribute and effective date ("من 1 مارس 2027").
  - "الاتفاقات بمحادثات الواتساب بالمجلد" says again where the rules live.

**Reading-habit levers.**
- fb_ramadan_scope (deep_in_long_document): the market study is 44.9 KB, and the Ramadan row is line 210 of 318, 68% in. It was displayed at most 23% in any step, and the line itself was visible in only 1/20 steps. This was irrelevant: start, end and scope all sit in the 9 KB Waha chat, which was displayed in 20/20 steps.
- fb_logged_value and fb_cash (unflagged_document): both files are named in the instruction and were displayed 20/20.
- The unread bytes (about half the fixture) are the four legacy Arabic plan files (23–45 KB) and their `home/user` duplicates. The one decisive fact in them sits 799 bytes into a plan, under "اقرأ هذا قبل أي شيء" (read this before anything), and every episode reached it by grepping the instruction's own phrase.

**Why the traps did not bite.**
- OBSERVED: every decisive rule sits in a small file that both models read in full in step 1.
- OBSERVED: the partners' own payment messages act as an answer key, confirming the VAT base, the flat fee, Jimi's 12%, the ceramic carve-out, the cap, the 8% renewal and the half-up ties.
- OBSERVED: each change message states its own scope, in general form, in the same sentence: "حتى الزباين اللي أرسلتهم قبل", "السيراميك ما عليه شي", "تُقدَّم على البند 2". Both models read the chats as prose and hand-coded each deal, so Astra's first-match and regex habits never engaged.
- OBSERVED: several levers aim at habits the agents did not show here. No episode used a bare `round()` on a final value; Astra's exact payer dict excludes the typing-office decoy by default; and step 2 is a fresh session in which both models rebuild from sources.
- OBSERVED: the step-2 news text and the output contract carry the deciding attributes (effective dates, return-date scope, cutoff, rounding stage).
- HYPOTHESIS: the only decisions that came near a flip (returned-goods cost 18.01 vs 20.59; referral date vs service date) were unbudgeted, and a single plain sentence settled each one. Making such a decision depend on a fact that no single sentence states might bite. Untested.

### 3.5 a-009 market-research

**Summary.** Both models scored pass@1 1.00, and no lever came close to biting.
- Every deciding rule is a numbered clause in `methodology/protocol_v1.2.md` (45 KB, 303 lines). Step 1 points at it ("under the current edition of our methodology protocol").
- All 20 steps displayed every decisive protocol clause, dossier line and journal line checked (35 normalised line probes over the full model-visible output).
- The fixture also labels most trap items in the data itself: the `kind` and `scope` columns, notes such as "СМЕНА ОХВАТА", "выведено из +19%" and "$13.54 млрд x 62.71", and dossier lines such as "Опубликовано в долларах" and "наш обратный счёт".
- Both models hard-coded the resulting exclusions as literal sets and cited the clause numbers in their write-ups.
- The step-2 instruction restates protocol 8.2(b)'s trigger, names the Yakov re-admission and tells the agent to recompute both states. That disarms the four step-2 levers.

Campaigns: Fable `edb0d0cf`, Astra `033d1ae2` (no voids).

Abbreviations: NBT = NEUTRALISED-BY-TEXT, SAH = SEEN-AND-HANDLED, NRBI = NEVER-REACHED-BUT-IRRELEVANT; "v3" = `ecommerce_data_v3.csv`, "protocol" = `methodology/protocol_v1.2.md`.

| # | budget id(s) | lever (targets) | decisive text (file:line, short quote) | Fable | Astra | class | evidence |
|---|---|---|---|---|---|---|---|
| 1 | F1 | first_match (both) | v3:18-19 `estimate_alt,520 … ПЕРВАЯ публикация` / `estimate,415 … ПЕРЕСМОТР`; protocol:132 (5.1) "действующей считается та, которую сам источник опубликовал последней" | 5/5 | 5/5 | NBT. Partial DESIGN-GAP: the `kind` column already marks the figure in force, and every agent filters `kind=='estimate'`, so first match never runs | 033d1ae2/package__Fk6YUYG/01 `if a['kind']=='estimate'`; edb0d0cf/package__7XPbk2D/01 "uses DI's figure in force, 415, not the first publication of 520" |
| 2 | F2 | house_definition (both) | protocol:172 (7.2) "Ограничения раздела 6 к панели не применяются"; the instruction defines the panel as "every year both … have a figure in force" | 5/5 | 5/5 | NBT (protocol and instruction) | edb0d0cf/7XPbk2D/01 "Panel ignores scope (§7.2)" |
| 3 | F3 | near_twin_negative (both) | v3:24 `DataInsight,2018,…,total,…,СМЕНА ОХВАТА`; protocol:183 (8.2a) | 5/5 | 5/5 | NBT (a capitalised note beside the row) | 033d1ae2/Fk6YUYG/01 `growth = None if r['scope'] != prev['scope']` |
| 4 | F4 | must_not_flag_twin (both) | protocol:186 (8.3) "Других оснований не считать темп нет"; journal entries are marked "Гипотеза … открыто" | 5/5 | 5/5 | NBT (closed list) | edb0d0cf/CmCayFq/01 "open journal items, which under 8.3 do not suspend a growth figure" |
| 5 | F5 | copied_figure (fable) | protocol:180 (8.1) "Темп, объявленный самим источником … в расчёт не берётся"; the instruction defines growth from levels | 5/5 | 5/5 | NBT | All 10 compute growth from register levels |
| 6 | F6 | non_observation_rows (both) | v3:36 note "выведено из +19% на 2015"; dossiers:98 "наш обратный счёт"; protocol:150 (6.4) | 5/5 | 5/5 | NBT | 033d1ae2/Fk6YUYG/01 `derived = {('НАДТ', 2014)}` |
| 7 | F7, F24 | unflagged_document (both); withhold_vs_resolve (astra) | contradictions_2026.md:49 "665 = 760 × 0,875 и 805 = 920 × 0,875" (displayed 20/20); protocol:156 (6.6б) defines relay as a constant multiple | 5/5 | 5/5 | NBT. DESIGN-GAP for the unflagged mechanism: the equality sits in a journal everyone reads, so audit_v3_report.md is not needed. No episode withheld | 033d1ae2/Fk6YUYG/01: exact `Fraction` ratio test, then `assert retransmissions == {'Euromonitor'}` |
| 8 | F8 | interested_artifact_refuted (fable) | dossiers:97 "Опубликовано в рублях" vs audit_v3_report.md:132-133 "2014–2019 НАДТ публиковала в долларах" | SAH 5/5 (saw the audit claim and silently followed the dossier) | NRBI 4/5; SAH 1/5 | SAH / NRBI | edb0d0cf/7XPbk2D/01 "so only НАДТ 2015 enters" |
| 9 | F9 | deep_in_long_document (both) | dossiers:119 "получен сведением опубликованных оценок…"; protocol:155 (6.6а) "(усреднением, сведением, взвешиванием)" | 5/5 | 5/5 | NBT: the dossier uses the protocol's own verb, and protocol:158 points to the dossiers | All 10 hard-code it: `synthesized_sources = {'Gaidar'}` |
| 10 | F10 | non_observation_rows (astra) | v3:38-39 notes "$13.54 млрд x 62.71"; dossiers:99 "Опубликовано в долларах"; protocol 6.4 | 5/5 | 5/5 | NBT | 033d1ae2/wJ7xRnf/01 `converted={('НАДТ',2018),('НАДТ',2019)}` |
| 11 | F11 | lexical_proxy (both) | dossiers:101 "не более 3,8 трлн"; protocol:152 (6.5) names «не более» | 5/5 | 5/5 | NBT (the same phrase appears in the rule and in the data) | edb0d0cf/CmCayFq/01 `bounds={('НАДТ',2021)}  # "не более 3,8 трлн"` |
| 12 | F12 | house_definition (fable) | protocol:148 (6.3) counts total scope only; the archived v1.1 pooled domestic and total | 5/5 | 5/5 | NBT | All filter `scope == 'total'` |
| 13 | F13 | first_match (astra) | v3:73-74 `forecast` 780, then `forecast_rev` 800; protocol:194 (9.2) | 5/5 | 5/5 | NBT (the kind label plus 9.2) | 033d1ae2/Fk6YUYG/01 `latest_date = max(r['published'] …)` |
| 14 | F14 | near_twin_negative (both) | v3:75 DI 2018 forecast `domestic`; protocol:200 (9.5) | 5/5 | 5/5 | NBT | edb0d0cf/7XPbk2D/01 "DI's 2018 forecast is unscored because it was domestic" |
| 15 | F15 | omission_bias (both) | protocol:192 (9.1) lists forecast_lo/hi; :196 (9.3) "сверяется по середине интервала" | 5/5 | 5/5 | NBT | All report the midpoint, 6450 |
| 16 | F16 | fill_the_gap (fable) | protocol:198 (9.4) "если источник не опубликовал собственной цифры … не сверяется"; the decoy 14600 appears only in the archived `ecommerce_data.csv` | 5/5 | 5/5 | NBT | edb0d0cf/7XPbk2D/01 "INFOLine 2025 have no own figure for the target year" |
| 17 | F17 | revision_scope (both), step 2 | protocol:202 (9.6) "Сверка идёт с первой редакцией…"; the instruction says the record "stays in the register as `estimate_alt`" | 5/5 | 5/5 | NBT | edb0d0cf/jcMEsTa/02 "the key catch that protocol 9.6 scores forecasts against the first edition" |
| 18 | F18 | attribute_not_in_step1 (both), step 2 | protocol:184 (8.2б); the instruction echoes the trigger: "announced that it has updated its methodology … It restated no other year" | 5/5 | 5/5 | NBT (the instruction repeats the clause's trigger) | edb0d0cf/CmCayFq/02 "exactly the case in point 8.2(b)" |
| 19 | F19 | interested_artifact_refuted (fable), step 2 | supply_demand_split.md:98 prints the right number, "стал **−1,5%**" | NRBI 5/5 | NRBI 5/5 | DESIGN-GAP: the gap is plain register arithmetic, and the draft prints the right number itself | 0/10 step-2 displays; all 10 output −1.5 |
| 20 | F20 | change_set_counterfactual (astra), step 2 | protocol:146 (6.2) requires "отвечающая одновременно всем условиям пп. 6.3–6.6" | 5/5 | 5/5 | NBT (a closed conjunction) | The Astra break flag is never applied to slots |
| 21 | F21 | unflagged_document (both) | intake_v3.csv:65 (row with no checker); protocol:112 (4.2) "Запись без отметки проверяющего в расчёты не берётся" names the journal and its `checked_by` column | 5/5 | 5/5 | NBT: the protocol names the "unflagged" journal | 033d1ae2/Fk6YUYG/01 "Unverified: 64 YakovPartners 2024 estimate 12600" |
| 22 | F22 | near_twin_negative (astra) | intake:79 checked by its own author; protocol 4.2 "Отметка, которую поставил сам автор записи…" | 5/5 | 5/5 | NBT | All 10 test `checked_by != author` |
| 23 | F23 | lexical_proxy (fable) | intake:47 "предварительные итоги по 11 месяцам; другой цифры за 2014 г. нет" | 5/5 | 5/5 | NBT; effectively a DESIGN-GAP: no rule pushes towards dropping it | 033d1ae2/Fk6YUYG/01 `expected_slots … 2014: (2,683,713)` |
| 24 | F25 | readmission (both), step 2 | step-2 instruction item 3: "The second check of the two Yakov and Partners records for 2024 … was completed by М.С." | 5/5 | 5/5 | NBT (the instruction names the item) | edb0d0cf/CmCayFq/02 "point 4.2 admits it" |
| 25 | F26 | change_set_counterfactual (both), step 2 | the instruction gives "kind estimate, value 14100, scope total … including cross-border" | 5/5 | 5/5 | NBT | 033d1ae2/zhkk2X8/02 "INFOLine adds a scored forecast and widens the 2025 slot" |
| 26 | F27 | copied_figure (both) | supply_demand_split.md:93-98 "стало **13,2 трлн**"; protocol:71 (3.2) "Цифра, упомянутая в рабочем тексте, но не внесённая в реестр, расчётной силы не имеет" | SAH 2/5; NRBI 3/5 | NRBI 5/5 | NBT, plus SAH for Fable | edb0d0cf/7XPbk2D/01 reasoning: "The АКИТ 2025 revision isn't recorded in the register, so per §3.2 it carries no weight" |

Totals:
- 23 of the 26 rows (27 ids) are NBT for both models.
- The exceptions are F8, F19 and F27, which were SAH or NRBI with no exposure to the wrong reading.
- DESIGN-GAP is full for F19 and partial for F1, F7 (as an unflagged lever) and F23.

**Near-misses.** None of substance.
- Fable 7XPbk2D/02 printed `MISMATCH` lines in its own before/after comparison. It recovered by re-comparing numerically: "The mismatch lines are only float-vs-integer formatting in my comparison; the values themselves match the existing page."
- Fable 7XPbk2D/01 headed its summary "Judgment calls the protocol required", but every item cites a clause and none expresses doubt.
- Astra asserts a hand-typed `expected_slots` dict against its own output: self-anchored.

**Instruction leaks.**
- Step 1:
  - "rebuilt from our estimates register exactly as it stands today, under the current edition of our methodology protocol". This names the governing document and edition, disarming the archive traps (F1, F12, F15, F16) and the working-text figure (F27).
  - "(the protocol's «действующая цифра»)" hands over the protocol's term, a ready grep key into section 5.
  - "one row per year in which both АКИТ and DataInsight have a figure in force" pre-answers F2.
  - "the change of the source's own figure in force for that year over its figure in force for the previous year" pre-answers F5.
  - "`fact`, the source's own figure it is scored against" works against filling INFOLine 2025 (F16).
  - "`forecast`, the forecast value as scored" hints at the interval midpoint (F15).
  - "Every percentage is computed from unrounded figures and rounded once, to one decimal place, with halves rounded away from zero." The rounding rule sits in the instruction (doctrine: dead).
- Step 2:
  - The 8.2(b) trigger is restated almost verbatim (F18).
  - "the 19 February record stays in the register as `estimate_alt`" (F17).
  - Every slot-admission attribute of the new INFOLine record is given (F26).
  - "The second check of the two Yakov and Partners records … was completed by М.С." names the re-admitted item and the deciding attribute (F25).
  - "compared with the page's correct values from the register as it stood before them" prescribes the two-state recomputation.

**Reading-habit levers.**
- F7 (unflagged_document):
  - `audit_v3_report.md` (16.8 KB) is not named by the instruction, and its operative content is near the top (lines 17-18, 55-57).
  - It was displayed by Fable 5/5 and Astra 2/5.
  - It was redundant: the same equation is at contradictions_2026.md:49, which was displayed 20/20.
- F21 (unflagged_document): the journal is named by protocol 4.2, together with its `checked_by` column. It was displayed in 19/20 steps; the 20th joined it in code.
- F9 (deep_in_long_document):
  - The dossier paragraph is at line 119 of 213 (19 KB), and the protocol clause at line 155 of 303 (45 KB).
  - Both files were displayed fully in 20/20 steps.
  - There is a shared verb ("сведением") between the rule and the data.
- How the 45 KB protocol was read in full:
  - Astra's first `cat` was always cut by Codex. Every episode then re-read it by line range (`sed -n '125,245p'`, `'1,125p'`, `'245,340p'`).
  - Fable hit the persisted-output preview and re-read with `sed -n` slices or the Read tool. nH7ieR8: "first section was truncated. I'll read it in smaller slices".
  - The instruction names the protocol as governing, so the agents persisted.
- Side effect of the duplicate copies: `home/user/supply_demand_split.md` differs from the root copy in one paragraph. Fable diffed the copies (3/5), and the diff pointed it straight at the 13,2-trn section.

**Why the traps did not bite.**
- OBSERVED: one governing document, named by the instruction, holds every rule as a numbered clause, and both models read it fully in every step, re-reading after truncation. Its closed lists ("всем условиям пп. 6.3–6.6", "Других оснований … нет") block both over-application and invented exclusions.
- OBSERVED: the data carries its own trap labels (`kind`, `scope`, capitalised notes, "Опубликовано в долларах", "не более"). Both models turned them into hard-coded literal sets after one read.
- OBSERVED: decisive facts are duplicated into files that are always read, and the legacy reports print correct answers. Fable pQpid7y/01: "The panel gaps match the figures in the August audit report, which is a useful cross-check."
- OBSERVED: the step-2 instruction pre-explains all four step-2 levers.
- OBSERVED: Fable reads working texts trap-aware: "to identify which old readings to avoid" (7XPbk2D/01), "to spot known traps" (nH7ieR8/01).
- HYPOTHESIS: a reading-habit lever would need the operative fact in an unreferenced document, with no lexical bridge from the protocol and no duplicate in a journal or report. Whether that is compatible with "every rule published" is untested.


---

## 4. Lever outcomes across tasks

Each budget entry is classified once, for both models, by its primary class. "Default-path-correct" counts entries
where the agents' default idiom already gives the graded answer, so only a deviation from it would fail. Those
entries also appear under NBT or DG.

| task | entries | NEUTRALISED-BY-TEXT | SEEN-AND-HANDLED | DESIGN-GAP (primary) | partial design gap | NEVER-REACHED-BUT-IRRELEVANT | default-path-correct (at least) |
|---|---|---|---|---|---|---|---|
| a-013 | 14 | 12 | 1 | 1 | 1 (fb_status_codes) | 0 | 5 |
| a-016 | 23 | 16 | 4 | 3 | 0 | 0 | 8 |
| a-011 | 24 | 21 | 2 | 1 | 1 (fb_campaign) | 0 | 6 |
| a-049 | 34 | 22 | 6 | 6 | 0 | 0 | 4 |
| a-009 | 27 | 25 | 1 | 1 | 3 (F1, F7, F23) | F8 (Astra 4/5), F19 (both), F27 (Fable 3/5, Astra 5/5) | 2 |
| **total** | **122** | **96 (79%)** | **14 (11%)** | **12 (10%)** | **5** | **0 as a primary class** | **at least 25** |

The design gaps are mechanisms the budget claims but the fixture does not implement:
- a "first_match" whose governing row is already first or labelled (a-016 fb_tie_break, a-009 F1);
- a "near twin" that differs in name, slug, type and dates (a-016 fb_referral_twin);
- a "binary-float tie" that is exact in binary (a-049 fb_ties);
- an "unflagged document" that the instruction names (a-049 fb_logged_value, fb_cash);
- a "deep_in_long_document" whose fact is repeated in a 9 KB chat (a-049 fb_ramadan_scope);
- a rounding stage pinned by the output contract (a-049 fb_rounding_stage);
- a heading swap that cannot occur in a long-form export keyed by indicator number (a-011 fb_swap);
- a "copied figure" draft that prints the right number (a-009 F19).

## 5. Near-misses across tasks (Q3)

Across 100 valid steps no graded value was computed wrong and later corrected. Every traceback or assertion failure
was off the graded path:
- a-011 Astra (3 episodes): optional cross-checks against the national extracts.
- a-011 Fable: a `Fraction * Decimal` type error.
- a-049 Astra: a missing `jsonschema` module.

What diverged or nearly diverged:

| task / episode | what happened | what made it recover | budgeted? |
|---|---|---|---|
| a-049 Fable 237f3a1a/MZRdb6e/01 (also j8VFZiB, pCKdnkd) | Computed an alternative PH-02 real profit "(if RTO cogs lost: 18.0125)", which would flip `keep` to `stop` | Courier terms §4 "تُعاد البضاعة للتاجر بحالتها" (goods are returned to the merchant as they are). One plain sentence | No |
| a-049 Fable 237f3a1a/pCKdnkd/01 | "لو حسبت علي الكتبي على تاريخ التنفيذ بدل تاريخ الإرسال لتطلع عمولته 120 بدل 80" (if I counted Ali Al-Ketbi by service date instead of send date, his commission would be 120 instead of 80) | The verb "ترسلهم" ("the ones you send") in the Waha chat | No (scope by referral date was budgeted, but this decoy was not) |
| a-011 Astra 6fb76fd/package__7ubLmSd/02 | Re-coded the annual rule as requiring both "more than 10 behind" AND "below two-fifths"; its step-1 code required only the second | Nothing. Every annual State figure is above 32, so the two codings agree on the data; a State figure under 16.7 would have split them | No |
| a-013 Fable af928e13/47phQiL/01 | Hedged on applying all three fill limits to Reza's extras | "Neither limit was binding" | No |
| a-009 Fable edb0d0cf/7XPbk2D/02 | Its own before/after diff printed `MISMATCH` lines | Re-compared numerically: "only float-vs-integer formatting" | No |
| a-049 Fable j8VFZiB/01, PB3JULz/01, pCKdnkd/01 | Used float arithmetic, with `floor(x+0.5)` and float profit `19.826000000000008` | Every half-dirham tie is exact in binary (`990*.15 == 148.5`), so float half-up is correct; the budget's float-edge claim was not implemented | Yes, as a design gap |

Fable voiced trap reasoning in prose in most episodes ("Galaxy A36 5G at 17 ads stays at 2", "look-alike handle
@vangridio ... not recognised", "Ordinary spreadsheet rounding would show 40.07, 55.62 and 90.62"). Fable also read
legacy working texts with the traps in mind: "to identify which old readings to avoid" (a-009 7XPbk2D/01), "to spot
known traps" (nH7ieR8/01). Astra's prose is one line per step, so its handling is visible only in code. That code
handled every case explicitly, usually as a hard-coded literal set.

Self-verification was structural and self-anchored, as R3 found:
- Fable asserted that its formula reproduces the printed caps.
- Astra asserted hand-typed `expected_slots` dicts, and in step 2 asserted that its recomputed baseline equals its
  own step-1 file.

None of these checks could catch a shared misreading, and there was none to catch.

## 6. Instruction leaks across tasks (Q4)

`levers.HINT_LEXICON` matches 0 times in the 10 step instructions. Their prose before the output contract runs
294-668 words, against the doctrine's 100-250. The leaks are semantic and live mostly in field definitions:

| leak class | tasks | example |
|---|---|---|
| L1 Procedure-shaped baseline for a step-2 diff | a-013, a-016, a-011, a-009 | a-013: "The comparison is between those two applications of our rules (with CSE-06 on the list, and without it), not with whatever numbers were typed into last night's file." a-016: "'Immediately before these two updates' means the position as it stood a moment ago ... after the updates, the three removed posts no longer count" |
| L2 Event text that echoes a clause's trigger | a-016, a-011, a-009, a-049 | a-011: "confirmed in writing that Dahanu block's zero ... is the real position" (copies SOP 3.5(a)). a-009: "announced that it has updated its methodology ... It restated no other year" (protocol 8.2(b)). a-016: "Posts published since the original closing time are being tracked as normal" |
| L3 Governing document, edition or every source class named | a-009, a-011, a-049, a-016 | a-009: "under the current edition of our methodology protocol". a-049: "محادثات الواتساب مع الشركاء (فيها الاتفاقات)" (the WhatsApp chats with the partners, which contain the agreements). a-011 lists every document class |
| L4 Field definition announces a trap category or the deciding attribute | all five | a-016: "A post that counts for two campaigns appears in both lists". a-011: "allowing for whether a higher or a lower figure is better". a-013: "`repriced` — ... whose Torob floor is now different", "All money is in toman" |
| L5 Rule placed in the instruction (doctrine: dead) | a-013, a-016, a-009, a-049 | a-009 and a-049 state half-up rounding. a-049: "`stop` إذا ربحه الحقيقي للطلب أقل من 20 درهم ... `keep` إذا ... 20 درهم أو أكثر" (`stop` if real profit per order is under 20 dirhams, `keep` if 20 or more). a-016: "treat anything still under review as standing". a-013: "never over" |
| L6 Variant or warning pre-resolved | a-011, a-016 | a-011: "Jawhar (Jawahar in NITI's files)", "carried figures under the wrong headings". a-016 pre-converts WIB to UTC |
| L7 Grep key that lands on the decisive sentence | a-049, a-009, a-011 | a-049: "الربح الحقيقي للطلب بالمعنى اللي بتستخدمه خططي" (real profit per order in the sense my plans use it), found 10/10 by `grep -n "20 درهم\|الربح الحقيقي"`. a-009: "(the protocol's «действующая цифра»)" |

**Validity machinery forced two of the leaks** (`verification/repair-log.json`):
- **a-013.** The baseline sentence (L1) answers semantic-review finding obj_s2_qty_changes: "Publish a source-rule
  counterfactual baseline explicitly, or compare against a trusted retained prior submission".
- **a-049.** The `stop`/`keep` definition, with its 20-dirham boundary, answers the `contract.ambiguity:
  undefined-category: 'stop' ... never given a definition` gate.

These are genuine validity requirements. The way they were satisfied, however, restated the rule the lever
(fb_per_order) was meant to hide.

The designer prompt also requires leaks of class L5: "DEFINE EVERY FIELD BY MEANING AND FORMAT ... units, rounding
mode and places" (`pipeline/author/agent_designer.py`, the "THE INSTRUCTION IS THE CONTRACT" block). The doctrine
lists "rules placed in the instruction" as DEAD and wants the rounding stage "stated once in a document, not the
instruction" (`levers.py`, rounding_stage).

---

## 7. Why the traps did not bite (Q5)

### 7.1 The single biggest reason (OBSERVED)

**Every lever was a noticing trap, and noticing cost these agents nothing.**
- The deciding rule was always stated plainly, often naming its own exception or decoy, in a small document that
  every episode read in full before writing any code.
- The trap members were labelled in the data, or sat on the agent's default code path.
- Once read, each rule became one line of transcribed code (a status filter, a `>`, a `timedelta(hours=15)`, a
  literal exclusion set). Transcription did not fail once in 1,220 lever-episodes.

None of the five tasks contains a graded decision that a literal transcription of the published sentences does not
already settle.

The doctrine's levers rest on the agent either not reading the operative document or misreading it (paraphrase of
the `levers.py` recipes). These agents read the whole authored world (§2) and do not misread plain prose. The genuineness rule, "each rule
stated ONCE, in general form, in the document a real organisation would keep it in", was satisfied by writing each
rule as a criterion that already contains its answer: "the latest «م» price", "credited to that partner's
opportunity only", "R lines ... are not further births", "Других оснований не считать темп нет" (there are no other
grounds for not computing the growth rate).

### 7.2 Contributing reasons (OBSERVED unless marked)

1. **The contract encodes the procedure (§6).** Step 2 is the worst case. In four tasks the baseline definition
   tells the agent to recompute both states. In four tasks the event text copies the trigger of the clause it
   activates.
2. **The data and partner messages answer the trap.**
   - Labels sit on trap rows: `kind`, `scope`, "СМЕНА ОХВАТА", "$... x 62.71", "تو لیست ما نیست" (not on our list).
   - The deal-log note in a-049 row 80 states its own conclusion.
   - a-049 partners state 15 of the 26 due commissions verbatim in their payment messages.
   - a-009 legacy reports print the correct panel gaps and the correct -1.5% revised gap.
3. **Default-path-correct lures (§4, at least 25).** A lever bites only if the default idiom gives the wrong
   answer. The doctrine's habit model (Astra first match and exact membership; Fable float `round()`) did not apply,
   because both models hard-coded literal sets after reading every member of small populations. No habitual
   predicate ran on a trap member.
4. **Step 2 is rebuilt from sources (all five tasks).** In the fresh session both models re-derived the before and
   after states and used their step-1 file only as a check. Levers premised on patching the step-1 file had nothing
   to act on.
5. **Hub concentration destroyed independence.** In a-013, 11 of 14 entries live in one 126-line chat; in a-016, 17
   of 23 in one help centre. The doctrine's independence test ("different mechanism, different file, different
   noticing trigger") fails. In a-013 and a-016 a single read neutralises most of the budget, so the nominal entry count
   overstates the independent decisions several times over. The semantic review said so in every task. a-013: "The eight objectives do not represent eight independent
   judgments". a-016: "The many campaign fields are not independent judgments". a-011: "The claim of about twenty
   independent judgments should not be inferred". a-049: "The 19 objectives are not 19 independent professional
   decisions". a-009: "The nine declared decisions are not nine independent reasoning mechanisms".
6. **The reading-habit levers had nothing to hide in (§2.3).**
7. **Pipeline (OBSERVED):** each task's `difficulty_advisories` predicted the outcome. They are advisory by policy,
   and the designer receives no difficulty feedback before the screen ("difficulty feedback will not" come back:
   `pipeline/author/agent_designer.py` AUTHORING_MANDATE: "validity findings may come back for repair, but difficulty
   feedback will not").
8. **HYPOTHESIS: the doctrine's levers are mis-specified against these agents.** In R3 and MSL, the bites came from
   applying a rule on unlabelled evidence where the agent's own realisation of the rule was wrong:
   - exact host membership missing `m.facebook.com`;
   - rounding once at the end where the rule rounds each commission;
   - a threshold left unrounded;
   - a newer second-hand relay chosen over an older first-hand record.

   None of the wave-1 levers had that shape once their rules were written down. The only real divergences in this
   wave were of that shape: the a-011 annual-rule conjunction, and a-049's returned-goods cost. The first went
   unpunished because the data did not discriminate between the two codings.

### 7.3 Can a trap stay genuine (one defensible answer, every rule published) and still defeat these agents?

Suppose every rule is published and a careful literal transcription of all of them gives the graded answer. Then
difficulty can come only from the following routes:

| route | wave-1 evidence | outside evidence |
|---|---|---|
| (a) Failing to find or transcribe a rule (noticing) | 0/1,220: dead | 30/30 warned decoys found (levers.DEAD) |
| (b) Mis-scoping the rule's application on unlabelled, variably-formed evidence (the agent's predicate or reading misses members) | No unlabelled trap members were built. Astra's latent AND-coding shows divergent codings exist | R3: all 5 failing Astra b2b episodes used exact host membership that excluded `m.facebook.com`; S08 vs 508 |
| (c) The default numeric or time stack betraying a correctly transcribed rule | Not built: ties exact in binary, integers only; Fable did use float in a-049 | R3: Astra rounded once at the end and lost 5/5 on business-monetisation; R1: `round(2.625,2)` |
| (d) Establishing a trigger fact by inference across documents (the trigger is a fact to establish, not a label to read) | Not built. Every trigger was stated or labelled | MSL relay vs first-hand authority (Astra 6/6) |
| (e) Composing two sentences in different documents, where neither names the item | Built once inside a single file (a-013 fb_porterage): 10/10 handled | tau2 task_075 (two fee rules, two documents, Fable 5 0/4; R2 P4) |

Routes (b)-(e) keep every rule published and one answer defensible: the rule is plain, and the evidence decides
who it reaches. The wave did not build them, so their effect on these two agents is untested (HYPOTHESIS). Route
(e)'s single wave-1 instance argues it must cross documents, with no lexical bridge between them, to have any chance.

---

## 8. Recommended changes (ranked)

Each item gives the change, where it goes, the evidence, and how to tell whether it worked. Items 1-3 address the
observed main cause. Items 4-9 are cheaper or more speculative.

**1. Make "default-wrong and unlabelled" the admission test for a fragility entry.** Doctrine (`levers.py` PROMPT
and `diagnostics`), designer self-audit, reviewer.
- The entry counts only if both of these hold, with the rule still published:
  - **(i) Default-wrong.** An *idiomatic baseline* gets at least one graded member wrong. That baseline is the
    script a careful agent writes after reading every file: it transcribes each published rule as written, with the
    idioms observed in this wave and in R3:
    - exact equality or slug joins;
    - `dict` last-wins or file order;
    - `>`/`//` as worded;
    - `Decimal` arithmetic with one quantize;
    - `.lower()`;
    - literal sets hard-coded after reading small populations;
    - a full before/after recompute in step 2.
  - **(ii) Unlabelled.** The trap member carries no note, status code named by the rule, comment, capitalised
    marker or adjacent explanation. Its deciding attribute is an ordinary-looking value of a field every row has,
    or a fact established in another document.
- An entry that fails either test is a noticing trap. Wave 1 measured q ~ 0 for those, so the budget should
  count it as zero.
- Evidence: 96 of 122 entries NBT; at least 25 default-path-correct; label examples in §7.2(2). In all five tasks
  the reviewer stated that a competent all-evidence baseline would score full marks, and both models did.
- The current review prompt treats that as "a difficulty advisory, NOT a substantive gap: never require the author
  to cripple it". Keep it non-blocking, but make the designer run the baseline and record, per entry, the member on
  which it is wrong.
- How to tell: on the next screen, every entry that passes this test should show per-check failures above 0 on at
  least one model. If none do, the hypothesis behind routes (b)-(e) is falsified for these agents.

**2. Strip procedure from the contract; satisfy validity without restating the rule.** Designer prompt and a
`check_draft` advisory.
- (a) Step-2 outputs ask for the after-state, not a diff defined as "two applications of our rules". Where a diff is
  essential, the baseline is a controller-filed record of last night's sheet, unlocked at step 2 (step-scoped unlocking
  exists; see a-009's `env.step_isolation` finding) and cited by name. This answers the a-013 reviewer's own
  alternative, "compare against a trusted retained prior submission".
- (b) Step-2 news arrives as raw facts in the requester's or a third party's words. It never reuses the vocabulary
  of the clause it triggers.
- (c) No governing document or edition is named, and the source classes are not enumerated.
- (d) An enum is defined by business meaning that points at the rule, not by restating the threshold. For example,
  "`stop` when the 20-dirham rule in my plan says stop selling", not "< 20 / >= 20". Whether the
  `contract.ambiguity` gate accepts that is untested.
- (e) Remove "rounding mode and places" from DEFINE EVERY FIELD where a fixture policy states the convention. This
  resolves the prompt's own contradiction with levers.DEAD.
- Add a mechanical **trigger-echo lint**: flag any instruction sentence that shares 4 or more consecutive content
  words, or a quoted term, with a `rule_sources` quote of a check it affects. HINT_LEXICON, which found 0 hits, is
  blind to these leaks.
- Evidence: §6. Every task leaks through field definitions; a-013 and a-049 leaked to close validity findings.
- How to tell: the lint is zero, and the semantic review stops reporting "a trap the instruction resolves".

**3. Ban self-naming rules and self-labelling data.** Doctrine (extend DEAD), designer prompt, a lint over
`rule_sources` and trap rows.
- A rule states its positive criterion in general form. It does not name:
  - the decoy column ("the 'Engagements' total ... play no part");
  - the wrong method ("not added up and divided by four");
  - the code to keep, when a legend exists ("the latest «م» price");
  - the excluded item ("تو لیست ما نیست").
- Trap rows carry no explanatory note.
- The lint flags a negation ("not", "never", "no other", "do not apply", "is not treated as") within a few tokens of
  a column name, code or entity that appears on a trap row. It also flags notes on rows that a check's `where`
  clause treats differently from their neighbours.
- Evidence: the examples in §3 and §7.2(2). DEAD already lists "trap labels ... any warned-about decoy (30/30
  found)". The designer moved the warnings into the rule text and the data.
- Caveat (OBSERVED): positive phrasing alone does not create difficulty when the rule is a formula; the Engagements
  decoy is irrelevant once the score is defined. Item 3 matters only in combination with item 1.

**4. Discriminating data for every compound or boundary rule.** Designer, plus a `quality.difficulty_case`
requirement.
- For each compound or boundary rule, include at least one graded member on which each *observed* alternative
  coding gives a different answer:
  - AND vs OR;
  - `>` vs `>=`;
  - per-line vs once-at-end rounding;
  - float `floor(x+0.5)` vs exact half-up, on a real binary edge;
  - first vs latest occurrence;
  - referral date vs service date.
- Take the alternatives from the agents' recorded code, not from author-invented misreadings.
- Evidence: Astra's latent AND-coding in a-011 (7ubLmSd/02) survived only because no annual State figure was under
  16.7. a-049's float users survived because every tie was exact in binary. a-016's tie-break survived because the
  pair was already in file order.
- How to tell: the counterexample for each alternative coding changes a graded value. The pipeline already executes
  counterexamples, so this is a matter of choosing them.

**5. A mechanism-verification gate for budget entries (advisory).** `levers.diagnostics`. Cheap static checks per
lever type:
- `first_match`: the governing occurrence is not first in file order, and no label distinguishes it.
- `near_twin_negative`: the twin shares the name and all but one printed attribute.
- `rounding_tie_betrayal`: at least one tie differs between `float` half-up and exact half-up.
- `unflagged_document`: the file is not named in the instruction, and no other fixture file refers to it by name or
  by a distinctive term.
- `deep_in_long_document`: the file is at least 30 KB, the decisive sentence is past the first 30%, and the fact is
  not duplicated in a smaller file.
- `lexical_proxy`: a grep for the instruction's keywords returns the wrong set.
- `rounding_stage`: the output contract does not define the aggregate as a sum of rounded parts.

Evidence: 12 primary and 5 partial design gaps (14% of entries) would have been flagged before the screen.

**6. Structured lever audit from the reviewer.** `pipeline/review.py`.
- Replace free-text difficulty advisories with a per-entry record: neutralising quote, default-correct (y/n),
  labelled (y/n), instruction echo (y/n), independent trigger (y/n).
- Feed it to hardening attempt 1, which policy already allows.
- Optionally, *if the user approves*, feed it to one non-blocking designer revision before the screen. That is a
  policy change from 2026-09-25/26 and needs an explicit decision.
- Evidence: in every task the advisories predicted the outcome in substance (§0.7).

**7. Write step-2 levers for agents that recompute from scratch.** Doctrine (`attribute_not_in_step1`,
`readmission`, `revision_scope`, `aggregate_propagation`).
- Assume the step-2 agent rebuilds both states from sources. This was observed in all five tasks, and both models
  use the step-1 file only as a check.
- A revision lever then survives only through routes (b)-(e) in §7.3: the event's consequence must be inferred
  from unlabelled evidence. Announcing it in the clause's words (L2) defeats it.
- The doctrine's "Fable re-uses its step-1 file in 94% of step-2 runs" is true here only as verification, never as
  patching.

**8. Spread decisive rules across documents (only together with items 1-3).** Designer.
- At most two decisive rules per document; no "rule dump" message blocks (a-013 chat lines 97-102 are five rules in
  seven minutes).
- A rule's applicability evidence lives in a different document from the rule, with no shared distinctive term.
- Evidence: hub concentration is OBSERVED (§7.2(5)). The benefit is a HYPOTHESIS: these agents read every small file
  anyway, so spreading the rules alone will not create misses. It only stops one read from neutralising many
  entries.

**9. Reading-habit levers only where agents actually skip.** Doctrine (`unflagged_document`,
`deep_in_long_document`).
- The only material these agents skip is long (over 16-30 KB), unnamed, background-looking text:
  - generic trace-origin plans and guides;
  - prompt libraries;
  - national extracts;
  - duplicates.

  Legacy files were displayed in 0-27% of file-steps, against 86-95% for authored files, a-009 aside.
- A decisive fact placed there, with no lexical bridge from the instruction or a hub document and no duplicate
  elsewhere, is the only version of these levers that could bite. The V2 review treats it as published ("location
  is not hiding").
- Whether it bites is untested; R3's small-file numbers did not hold for this wave's authored files, in any of their four
  languages. The
  genuineness risk is that a careful expert must still regard that document as authoritative.
- Pilot this with one A/B pair rather than doctrine-wide.

**10. Recalibrate the doctrine's arithmetic.**
- Replace "q ~ 0.10-0.15 per fragile decision" with the wave-1 measurement: q ~ 0 (0/1,220) for stated-rule,
  read-in-full levers.
- Count only entries that pass items 1 and 5.
- Five real entries are worth more than thirty nominal ones, and wave 1 shows that density built from noticing
  traps cannot move pass@1.

**Suggested measurement plan** (manual hardening, at most 3 attempts per task):
- Take one rich bundle (a-011 or a-049) and screen three revisions 5x2:
  - V1 removes the instruction leaks only (item 2);
  - V2 adds item 3 (self-naming and labels);
  - V3 adds items 1 and 4 (default-wrong, unlabelled members with discriminating data).
- This isolates which change moves per-check failure rates above zero. pass@1 is the target, but per-check rates
  are the informative signal at these levels.

---

## 9. What is verified and what is not

**Verified by execution, read-only:**
- valid and void episode lists and void causes;
- byte identity of each bundle fixture with its screened package;
- per-step reading metrics (Appendix A);
- budget versus non-budget display rates;
- decisive-line visibility, per task, by normalised probes against model-visible output;
- the arithmetic idioms used. Decimal/Fraction appears in every a-009 and a-011 step, every a-049 Astra step,
  every a-013 Astra step 1 and 3/5 Astra step 2; Fable a-013 used integer arithmetic and a-016 needs none. A bare
  `round(` appears in 6 Fable steps, and since every check passed, none of them changed a graded value;
- the HINT_LEXICON scan;
- the repair-log provenance of two leaks.

Every lever classification cites a fixture line and trajectory evidence. The per-task analyses were done by
parallel sub-analyses; spot-checks of quoted fixture lines matched (a-013 chat lines 56-106, a-011 SOP:125, a-016
help:150, a-009 protocol:71/112).

**Not verified or untested:**
- the hidden reasoning of either model (Codex reasoning is encrypted; Fable reasoning is sparse), so "noticed" is a
  lower bound;
- whether any recommended change bites: every item in §8 is a hypothesis except where it says OBSERVED;
- whether the `contract.ambiguity` gate accepts meaning-only enum definitions (item 2d);
- whether decisive facts placed in skipped legacy-style documents survive the semantic review's genuineness test;
- behaviour on binary office formats (none in this wave, as in R3).

---

## Appendix A: per-episode reading behaviour (100 valid steps)

Campaign short ids map to §1.1. "opened" = named in a command or at least 30% displayed. "displayed >=90%" counts
unique files. KB = 1,000 bytes; fixture KB counts identical copies once.

| task | model | campaign | trial | step | files (unique) | opened | displayed >=90% | fixture KB (unique) | displayed KB | % | tool calls (raw / commands) | truncated / persisted obs | wall s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| a-013 | fable | af928e13 | 47phQiL | 01 | 12 (9) | 9 | 5 | 117.0 | 59.4 | 51% | 6 / 6 | 0 / 1 | 158 |
| a-013 | fable | af928e13 | 47phQiL | 02 | 12 (9) | 4 | 4 | 117.0 | 30.3 | 26% | 5 / 5 | 0 / 1 | 85 |
| a-013 | fable | af928e13 | H5cS52S | 01 | 12 (9) | 9 | 5 | 117.0 | 53.2 | 45% | 7 / 7 | 0 / 1 | 142 |
| a-013 | fable | af928e13 | H5cS52S | 02 | 12 (9) | 8 | 5 | 117.0 | 47.6 | 41% | 8 / 8 | 0 / 0 | 144 |
| a-013 | fable | af928e13 | UDhfbup | 01 | 12 (9) | 9 | 5 | 117.0 | 53.5 | 46% | 7 / 7 | 0 / 1 | 145 |
| a-013 | fable | af928e13 | UDhfbup | 02 | 12 (9) | 4 | 4 | 117.0 | 26.9 | 23% | 5 / 5 | 0 / 0 | 89 |
| a-013 | fable | af928e13 | n5uKAxG | 01 | 12 (9) | 9 | 5 | 117.0 | 54.0 | 46% | 7 / 7 | 0 / 1 | 144 |
| a-013 | fable | af928e13 | n5uKAxG | 02 | 12 (9) | 4 | 4 | 117.0 | 29.3 | 25% | 5 / 5 | 0 / 1 | 90 |
| a-013 | fable | af928e13 | pHxDGAw | 01 | 12 (9) | 9 | 5 | 117.0 | 56.0 | 48% | 5 / 5 | 0 / 0 | 112 |
| a-013 | fable | af928e13 | pHxDGAw | 02 | 12 (9) | 7 | 4 | 117.0 | 28.9 | 25% | 6 / 6 | 0 / 0 | 117 |
| a-013 | astra | 57d00ff6 | Y4kj79m | 01 | 12 (9) | 9 | 6 | 117.0 | 75.8 | 65% | 6 / 13 | 1 / 0 | 88 |
| a-013 | astra | 57d00ff6 | Y4kj79m | 02 | 12 (9) | 6 | 5 | 117.0 | 65.4 | 56% | 4 / 6 | 1 / 0 | 66 |
| a-013 | astra | 57d00ff6 | YwZdXEt | 01 | 12 (9) | 9 | 8 | 117.0 | 93.5 | 80% | 6 / 11 | 2 / 0 | 136 |
| a-013 | astra | 57d00ff6 | YwZdXEt | 02 | 12 (9) | 4 | 4 | 117.0 | 26.9 | 23% | 4 / 7 | 0 / 0 | 65 |
| a-013 | astra | 57d00ff6 | ZsaShTd | 01 | 12 (9) | 9 | 6 | 117.0 | 71.1 | 61% | 6 / 10 | 1 / 0 | 98 |
| a-013 | astra | 57d00ff6 | ZsaShTd | 02 | 12 (9) | 7 | 4 | 117.0 | 42.1 | 36% | 4 / 6 | 0 / 0 | 79 |
| a-013 | astra | 57d00ff6 | eEvo8zQ | 01 | 12 (9) | 9 | 5 | 117.0 | 63.0 | 54% | 6 / 11 | 1 / 0 | 141 |
| a-013 | astra | 57d00ff6 | eEvo8zQ | 02 | 12 (9) | 5 | 4 | 117.0 | 39.8 | 34% | 4 / 9 | 0 / 0 | 65 |
| a-013 | astra | 2410d80a | SC8sErk | 01 | 12 (9) | 9 | 7 | 117.0 | 89.7 | 77% | 6 / 13 | 2 / 0 | 72 |
| a-013 | astra | 2410d80a | SC8sErk | 02 | 12 (9) | 7 | 4 | 117.0 | 47.5 | 41% | 5 / 9 | 0 / 0 | 75 |
| a-016 | fable | 8e30b0ce | 37hzGqt | 01 | 12 (11) | 11 | 6 | 112.5 | 74.7 | 66% | 7 / 7 | 0 / 0 | 148 |
| a-016 | fable | 8e30b0ce | 37hzGqt | 02 | 12 (11) | 8 | 6 | 112.5 | 67.1 | 60% | 5 / 5 | 0 / 0 | 131 |
| a-016 | fable | 8e30b0ce | 8GLSTvC | 01 | 12 (11) | 11 | 5 | 112.5 | 57.1 | 51% | 9 / 9 | 0 / 1 | 126 |
| a-016 | fable | 8e30b0ce | 8GLSTvC | 02 | 12 (11) | 6 | 4 | 112.5 | 41.9 | 37% | 6 / 6 | 0 / 0 | 121 |
| a-016 | fable | 8e30b0ce | d87PexB | 01 | 12 (11) | 11 | 6 | 112.5 | 73.3 | 65% | 7 / 7 | 0 / 0 | 149 |
| a-016 | fable | 8e30b0ce | d87PexB | 02 | 12 (11) | 11 | 6 | 112.5 | 68.9 | 61% | 5 / 5 | 0 / 0 | 138 |
| a-016 | fable | 8e30b0ce | gEPgZPF | 01 | 12 (11) | 11 | 6 | 112.5 | 69.7 | 62% | 8 / 8 | 0 / 0 | 128 |
| a-016 | fable | 8e30b0ce | gEPgZPF | 02 | 12 (11) | 8 | 5 | 112.5 | 65.5 | 58% | 6 / 6 | 0 / 0 | 122 |
| a-016 | fable | 8e30b0ce | wQ2bu3d | 01 | 12 (11) | 11 | 5 | 112.5 | 50.1 | 45% | 8 / 8 | 0 / 1 | 164 |
| a-016 | fable | 8e30b0ce | wQ2bu3d | 02 | 12 (11) | 11 | 4 | 112.5 | 46.2 | 41% | 7 / 7 | 0 / 0 | 158 |
| a-016 | astra | 49c71cb7 | sGSK8z5 | 01 | 12 (11) | 11 | 9 | 112.5 | 81.6 | 73% | 6 / 15 | 1 / 0 | 127 |
| a-016 | astra | 49c71cb7 | sGSK8z5 | 02 | 12 (11) | 6 | 5 | 112.5 | 50.1 | 45% | 5 / 11 | 1 / 0 | 71 |
| a-016 | astra | 339c235f | WytivBh | 01 | 12 (11) | 11 | 4 | 112.5 | 73.4 | 65% | 6 / 13 | 1 / 0 | 78 |
| a-016 | astra | 339c235f | WytivBh | 02 | 12 (11) | 11 | 8 | 112.5 | 97.1 | 86% | 5 / 9 | 1 / 0 | 91 |
| a-016 | astra | 339c235f | oiWLcMp | 01 | 12 (11) | 11 | 4 | 112.5 | 62.8 | 56% | 6 / 11 | 1 / 0 | 75 |
| a-016 | astra | 339c235f | oiWLcMp | 02 | 12 (11) | 11 | 8 | 112.5 | 101.6 | 90% | 5 / 12 | 1 / 0 | 87 |
| a-016 | astra | 339c235f | wDbYR4x | 01 | 12 (11) | 11 | 8 | 112.5 | 86.6 | 77% | 6 / 14 | 2 / 0 | 83 |
| a-016 | astra | 339c235f | wDbYR4x | 02 | 12 (11) | 11 | 8 | 112.5 | 105.5 | 94% | 6 / 12 | 2 / 0 | 66 |
| a-016 | astra | 339c235f | yci3wqW | 01 | 12 (11) | 11 | 8 | 112.5 | 103.6 | 92% | 7 / 12 | 2 / 0 | 114 |
| a-016 | astra | 339c235f | yci3wqW | 02 | 12 (11) | 6 | 4 | 112.5 | 44.7 | 40% | 4 / 8 | 1 / 0 | 67 |
| a-011 | fable | 4ba2c45f | JkpX24Q | 01 | 19 (16) | 16 | 13 | 469.9 | 129.4 | 28% | 12 / 12 | 0 / 1 | 145 |
| a-011 | fable | 4ba2c45f | JkpX24Q | 02 | 19 (16) | 16 | 13 | 469.9 | 132.2 | 28% | 12 / 12 | 0 / 2 | 130 |
| a-011 | fable | 4ba2c45f | da6uChv | 01 | 19 (16) | 16 | 13 | 469.9 | 132.2 | 28% | 15 / 15 | 0 / 2 | 185 |
| a-011 | fable | 4ba2c45f | da6uChv | 02 | 19 (16) | 16 | 11 | 469.9 | 93.1 | 20% | 13 / 13 | 0 / 3 | 160 |
| a-011 | fable | 4ba2c45f | kaM9Y2T | 01 | 19 (16) | 16 | 12 | 469.9 | 113.9 | 24% | 18 / 18 | 0 / 2 | 186 |
| a-011 | fable | 4ba2c45f | kaM9Y2T | 02 | 19 (16) | 16 | 13 | 469.9 | 128.3 | 27% | 11 / 11 | 0 / 2 | 166 |
| a-011 | fable | 4ba2c45f | ptDQYh6 | 01 | 19 (16) | 16 | 13 | 469.9 | 133.2 | 28% | 15 / 15 | 0 / 2 | 154 |
| a-011 | fable | 4ba2c45f | ptDQYh6 | 02 | 19 (16) | 16 | 13 | 469.9 | 128.3 | 27% | 14 / 14 | 0 / 2 | 177 |
| a-011 | fable | 4ba2c45f | sKVjhs3 | 01 | 19 (16) | 16 | 13 | 469.9 | 136.0 | 29% | 16 / 16 | 0 / 1 | 214 |
| a-011 | fable | 4ba2c45f | sKVjhs3 | 02 | 19 (16) | 13 | 12 | 469.9 | 101.2 | 22% | 13 / 13 | 0 / 5 | 129 |
| a-011 | astra | 6fb76fd9 | 3UMdjEt | 01 | 19 (16) | 15 | 7 | 469.9 | 94.4 | 20% | 8 / 13 | 2 / 0 | 126 |
| a-011 | astra | 6fb76fd9 | 3UMdjEt | 02 | 19 (16) | 12 | 8 | 469.9 | 83.5 | 18% | 5 / 10 | 2 / 0 | 65 |
| a-011 | astra | 6fb76fd9 | 7ubLmSd | 01 | 19 (16) | 13 | 11 | 469.9 | 102.1 | 22% | 7 / 12 | 1 / 0 | 98 |
| a-011 | astra | 6fb76fd9 | 7ubLmSd | 02 | 19 (16) | 11 | 9 | 469.9 | 88.0 | 19% | 6 / 12 | 1 / 0 | 64 |
| a-011 | astra | 6fb76fd9 | 8QNy3iQ | 01 | 19 (16) | 15 | 9 | 469.9 | 93.9 | 20% | 8 / 13 | 2 / 0 | 145 |
| a-011 | astra | 6fb76fd9 | 8QNy3iQ | 02 | 19 (16) | 9 | 5 | 469.9 | 63.5 | 14% | 6 / 10 | 2 / 0 | 67 |
| a-011 | astra | 6fb76fd9 | 9iM4P7t | 01 | 19 (16) | 14 | 10 | 469.9 | 120.1 | 26% | 9 / 15 | 1 / 0 | 129 |
| a-011 | astra | 6fb76fd9 | 9iM4P7t | 02 | 19 (16) | 10 | 8 | 469.9 | 84.5 | 18% | 6 / 12 | 1 / 0 | 56 |
| a-011 | astra | 6fb76fd9 | K7TWLUg | 01 | 19 (16) | 16 | 7 | 469.9 | 96.4 | 21% | 9 / 15 | 2 / 0 | 210 |
| a-011 | astra | 6fb76fd9 | K7TWLUg | 02 | 19 (16) | 9 | 6 | 469.9 | 76.6 | 16% | 6 / 10 | 1 / 0 | 53 |
| a-049 | fable | 237f3a1a | MZRdb6e | 01 | 25 (21) | 21 | 17 | 211.3 | 105.5 | 50% | 19 / 19 | 0 / 2 | 201 |
| a-049 | fable | 237f3a1a | MZRdb6e | 02 | 25 (21) | 21 | 17 | 211.3 | 103.2 | 49% | 16 / 16 | 0 / 1 | 170 |
| a-049 | fable | 237f3a1a | PB3JULz | 01 | 25 (21) | 20 | 17 | 211.3 | 107.2 | 51% | 16 / 16 | 0 / 2 | 187 |
| a-049 | fable | 237f3a1a | PB3JULz | 02 | 25 (21) | 21 | 17 | 211.3 | 103.0 | 49% | 11 / 11 | 0 / 1 | 173 |
| a-049 | fable | 237f3a1a | j8VFZiB | 01 | 25 (21) | 21 | 17 | 211.3 | 107.7 | 51% | 14 / 14 | 0 / 1 | 232 |
| a-049 | fable | 237f3a1a | j8VFZiB | 02 | 25 (21) | 20 | 17 | 211.3 | 101.8 | 48% | 10 / 10 | 0 / 2 | 169 |
| a-049 | fable | 237f3a1a | pCKdnkd | 01 | 25 (21) | 20 | 17 | 211.3 | 107.8 | 51% | 17 / 17 | 0 / 3 | 206 |
| a-049 | fable | 237f3a1a | pCKdnkd | 02 | 25 (21) | 19 | 17 | 211.3 | 103.0 | 49% | 11 / 11 | 0 / 1 | 177 |
| a-049 | fable | 237f3a1a | udvq5LZ | 01 | 25 (21) | 20 | 17 | 211.3 | 107.0 | 51% | 19 / 19 | 0 / 1 | 184 |
| a-049 | fable | 237f3a1a | udvq5LZ | 02 | 25 (21) | 20 | 17 | 211.3 | 104.2 | 49% | 11 / 11 | 0 / 1 | 163 |
| a-049 | astra | 33bd52eb | uGWpnp5 | 01 | 25 (21) | 20 | 17 | 211.3 | 133.7 | 63% | 8 / 15 | 2 / 0 | 173 |
| a-049 | astra | 33bd52eb | uGWpnp5 | 02 | 25 (21) | 19 | 16 | 211.3 | 110.1 | 52% | 7 / 13 | 3 / 0 | 86 |
| a-049 | astra | aefa433a | P7cggFZ | 01 | 25 (21) | 19 | 17 | 211.3 | 121.0 | 57% | 9 / 15 | 2 / 0 | 179 |
| a-049 | astra | aefa433a | P7cggFZ | 02 | 25 (21) | 19 | 16 | 211.3 | 103.1 | 49% | 7 / 14 | 3 / 0 | 79 |
| a-049 | astra | aefa433a | YAqADbn | 01 | 25 (21) | 21 | 17 | 211.3 | 119.7 | 57% | 11 / 18 | 2 / 0 | 172 |
| a-049 | astra | aefa433a | YAqADbn | 02 | 25 (21) | 20 | 17 | 211.3 | 119.3 | 56% | 8 / 15 | 3 / 0 | 130 |
| a-049 | astra | aefa433a | gvR7ZRp | 01 | 25 (21) | 21 | 17 | 211.3 | 123.9 | 59% | 11 / 18 | 2 / 0 | 272 |
| a-049 | astra | aefa433a | gvR7ZRp | 02 | 25 (21) | 19 | 17 | 211.3 | 116.5 | 55% | 8 / 12 | 2 / 0 | 106 |
| a-049 | astra | aefa433a | oLtTjna | 01 | 25 (21) | 21 | 18 | 211.3 | 139.5 | 66% | 9 / 14 | 1 / 0 | 168 |
| a-049 | astra | aefa433a | oLtTjna | 02 | 25 (21) | 19 | 17 | 211.3 | 108.0 | 51% | 8 / 13 | 2 / 0 | 88 |
| a-009 | fable | edb0d0cf | 7XPbk2D | 01 | 20 (14) | 12 | 9 | 181.8 | 143.0 | 79% | 16 / 16 | 0 / 1 | 189 |
| a-009 | fable | edb0d0cf | 7XPbk2D | 02 | 20 (14) | 5 | 5 | 181.8 | 89.9 | 49% | 8 / 8 | 0 / 2 | 140 |
| a-009 | fable | edb0d0cf | CmCayFq | 01 | 20 (14) | 13 | 9 | 181.8 | 144.2 | 79% | 14 / 14 | 0 / 1 | 189 |
| a-009 | fable | edb0d0cf | CmCayFq | 02 | 20 (14) | 5 | 5 | 181.8 | 89.7 | 49% | 11 / 11 | 0 / 2 | 119 |
| a-009 | fable | edb0d0cf | jcMEsTa | 01 | 20 (14) | 8 | 8 | 181.8 | 128.9 | 71% | 13 / 13 | 0 / 2 | 161 |
| a-009 | fable | edb0d0cf | jcMEsTa | 02 | 20 (14) | 9 | 7 | 181.8 | 122.7 | 67% | 13 / 13 | 0 / 1 | 105 |
| a-009 | fable | edb0d0cf | nH7ieR8 | 01 | 20 (14) | 14 | 10 | 181.8 | 152.4 | 84% | 17 / 17 | 0 / 2 | 168 |
| a-009 | fable | edb0d0cf | nH7ieR8 | 02 | 20 (14) | 8 | 5 | 181.8 | 91.3 | 50% | 10 / 10 | 0 / 0 | 157 |
| a-009 | fable | edb0d0cf | pQpid7y | 01 | 20 (14) | 7 | 7 | 181.8 | 122.7 | 67% | 12 / 12 | 0 / 2 | 162 |
| a-009 | fable | edb0d0cf | pQpid7y | 02 | 20 (14) | 8 | 5 | 181.8 | 93.6 | 51% | 8 / 8 | 0 / 1 | 114 |
| a-009 | astra | 033d1ae2 | Fk6YUYG | 01 | 20 (14) | 5 | 5 | 181.8 | 90.0 | 49% | 8 / 16 | 1 / 0 | 124 |
| a-009 | astra | 033d1ae2 | Fk6YUYG | 02 | 20 (14) | 5 | 5 | 181.8 | 88.6 | 49% | 7 / 10 | 1 / 0 | 84 |
| a-009 | astra | 033d1ae2 | LKPjW4x | 01 | 20 (14) | 6 | 5 | 181.8 | 101.9 | 56% | 8 / 12 | 2 / 0 | 117 |
| a-009 | astra | 033d1ae2 | LKPjW4x | 02 | 20 (14) | 7 | 5 | 181.8 | 89.2 | 49% | 6 / 10 | 1 / 0 | 73 |
| a-009 | astra | 033d1ae2 | Mtbw7LT | 01 | 20 (14) | 5 | 5 | 181.8 | 89.9 | 49% | 7 / 9 | 1 / 0 | 95 |
| a-009 | astra | 033d1ae2 | Mtbw7LT | 02 | 20 (14) | 6 | 5 | 181.8 | 100.6 | 55% | 6 / 11 | 3 / 0 | 80 |
| a-009 | astra | 033d1ae2 | wJ7xRnf | 01 | 20 (14) | 7 | 5 | 181.8 | 94.4 | 52% | 7 / 14 | 2 / 0 | 126 |
| a-009 | astra | 033d1ae2 | wJ7xRnf | 02 | 20 (14) | 6 | 5 | 181.8 | 88.7 | 49% | 5 / 9 | 1 / 0 | 71 |
| a-009 | astra | 033d1ae2 | zhkk2X8 | 01 | 20 (14) | 6 | 5 | 181.8 | 89.9 | 49% | 6 / 8 | 1 / 0 | 96 |
| a-009 | astra | 033d1ae2 | zhkk2X8 | 02 | 20 (14) | 7 | 6 | 181.8 | 104.9 | 58% | 6 / 11 | 2 / 0 | 66 |
