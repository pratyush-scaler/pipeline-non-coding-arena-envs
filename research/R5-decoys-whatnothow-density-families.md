# R5: near-miss decoys, what-not-how instructions, density, model-family skews, long-horizon state, validity

Compiled 2026-10-02 (from the session clock). This is web research for fair, deterministic,
non-coding document tasks. Each task is a folder of files plus an instruction, and the answers
are structured JSON graded against targets recomputed from the files. The calibration pair is
Fable 5.1 in Claude Code and GPT-6 Astra in Codex CLI, at high effort, with no turn or time limits,
offline. There are two steps, and step 2 is a fresh session.

**Relation to the existing catalogue.** This document assumes the reader has
`frontier-agent-failure-modes.md` and `trajectory-nearmiss-report.md` (both 2026-09-29, in
`arena-envs-tasks-large-dump/pipeline-artifacts/research/`).
- It does not repeat their entries (DAB, NoLiMa, OfficeQA Pro, the exception-chain paper, HiL-Bench,
  Solving-vs-Verifying, TIDE, MemoryAgentBench and others) except where a new source changes their
  reading.
- Roughly 60 sources below are new to the catalogue.
- Nothing from either local file or the repository was sent to a web service; every query was
  generic.

**Tags.**
- `[V]` = the quoted sentence or number was read in the primary text (arXiv HTML/PDF, the official
  page) during this research.
- `[A]` = from an abstract, a search snippet, a secondary page, or a tool summary that could not be
  matched line by line.

WebFetch passes pages through a summariser model. Quotes marked `[V]` were returned as verbatim
strings, but treat them as near-verbatim. Numbers that matter for a design decision should be
re-read from the PDF before they are quoted outward.

**Settings.**
- `{tools}` = measured with an agent that can run code or call tools.
- `{no-tools}` = a single call or a long-context evaluation.

A `{no-tools}` result is evidence that a failure mode exists. It is not evidence that the mode
survives a shell.

**Standing caveat.** No public source measures Fable 5.1 in Claude Code or GPT-6 Astra in Codex on
document audits. Every transfer below is a hypothesis to be screened.

---

## 0. Bottom line (the ten findings that should change how tasks are built)

1. **The decoy that bites a tool user sits in the population, not in the answer space.**
   - A decoy that is a second candidate *value* gets computed next to the right one and rejected.
     Internally this happened in 448 hits. The trap types `plausible_decoy` and `stale_authority`
     each fail about 1% of attempts.
   - A decoy that is a *member* bites. It is a row, entity or clause that the agent's selection
     predicate admits or drops without ever seeing an alternative.
   - The strongest new evidence with tools is TrustDABench (2026-08).
     - "Non-observation row injection" ranks as the most damaging perturbation for every one of 8
       models, including GPT-5.5 and Claude Sonnet 5, when they run Python and Bash on data files.
     - Those are rows explicitly marked as not being observations.
     - By contrast, a similarly named distractor column is among the weakest.
2. **Decoys bite through the attribute the predicate never reads.**
   - Product-matching benchmarks define the hard negative precisely: a pair that agrees "in brand,
     model name, and nearly the entire description" and differs "only in some or a single
     attribute" (Billiger.de, 2026-09).
   - The hard positive is the same entity under dissimilar surface forms.
   - The internal Astra misses (`m.facebook.com`, `S08`/`508`) are the positive kind. Fable has not
     been measured against the negative kind.
3. **Stating the rule or warning about the decoy removes the effect.** The pattern repeats across
   unrelated literatures:
   - a "rule-guided" prompt lifts GPT-5.2 product matching from 75.96 to 81.29 F1;
   - BIRD's evidence hints add about 13 points;
   - telling the model to ignore irrelevant information is a published mitigation for GSM-IC;
   - in solve mode, models return the clean-input answer through an injected contradiction 63-76%
     of the time; asked to verify, they flag 75-83% (catalogue).
   The instruction must therefore never carry the distinguishing attribute. Only the documents may.
4. **What-not-how has a clean natural experiment.** WorkArena++ ran the same tasks with the
   procedure in the prompt (L2) and with only a ticket plus a knowledge base (L3).
   - GPT-4o scored 3.0% at L2 and 0.0% at L3. Humans scored 93.9%.
   - DABstep (explicit vs implicit rules) and SpreadsheetBench 2 (2026-06) agree. In the latter,
     with error types and target cells unstated, debugging scores were 12% for Opus 4.6 and 8% for
     GPT-5.2.
   - Deleting *definitions*, as opposed to procedure, creates ambiguity instead. Examples: BIRD
     evidence, and the GDPval under-specified prompts that removed data location and format.
   - So move definitions into the documents. Do not delete them.
5. **Rules that live in long documents with perturbed parameters stay hard.** HANDBOOK.md
   (2026-07) is the closest public analogue to our task shape.
   - It has 65 deterministic tasks under 20-124-page SOPs. Each task alters a base handbook's rules
     and thresholds.
   - The best strict pass rate is 36.2% (Fable 5), and GPT-5.6 Sol scores 23.5%.
   - Failures are in-environment requests overriding policy, acting against a check the agent itself
     ran, losing rule details, and false compliance claims.
6. **All-pass density works only through roughly independent fragile decisions.**
   - On Harvey LAB-AA, the published pairs behave like about 28-30 *independent* criteria. Fable 5
     passes 93.6% of criteria but 14.2% of tasks, Opus 4.8 91.1% and 7.5%, Sonnet 5 90.1% and 5.0%.
   - Our two models are equally exposed in the same harness. Vals LAB held-out: Fable 5.1 passes
     86.57% of criteria and 6.67% of tasks; Astra 87.48% and 5.42%.
   - On APEX-Agents the same calculation gives about 1.5. Failures there are all-or-nothing, with
     zero criteria met in at least 40% of runs.
   - APIFlow-Bench (2026-08) finds 20-step chains passing 33 points *above* the independence
     product: "correlated competence".
   - With a realistic per-decision miss rate of q = 0.10-0.15 per model, pass@1 < 0.3 needs 8-12
     independent silent decisions per model. With within-episode correlation of 0.1, it needs about
     12-20. A task aimed at both families needs both sets (section 3).
7. **The family skews have moved since 2025. Use the 2026-09 evidence (section 4).**
   - **Fable 5.1 is now the over-attempter.** AA-Omniscience, max effort: it attempts 93.4% of
     questions, and on the questions it got wrong it answered anyway 72.6% of the time. Astra's
     equivalent figure is 44.8-51.3%.
   - **Astra is the one that pauses.** OpenAI: it is "more likely to ask for clarification" and
     "unclear or conflicting guidance in a skill file may cause the model to pause and block work
     early".
   - Astra also writes the shortest answers and takes the fewest turns. Vals Tax: 956 words and
     20.7% all-pass, against Fable 5.1's 49.22%.
   - Claude Code copies reported figures: replication accuracy fell from 100% to 63.3% when the
     paper was readable, against 90% for Codex.
   - The 2026-03 Claude "nested-exception denial" closed by April (67/68).
   - Levers that point in opposite directions:
     - fill-the-gap vs withhold;
     - scope-widening vs terse omission;
     - copying a stated figure vs re-deriving;
     - one programmatic predicate vs a prose reading.
   - Stack two-sided cases on each lever.
8. **Fresh-session step 2 is a lossy, trusted handoff.** Section 5 has the details.
   - A saved claim raises downstream failure from 45.0% to 71.9% (PASB).
   - Bounded self-maintained memory drops knowledge-update accuracy from 92% to 77% on GPT-5.4.
   - Fair levers are premise changes whose reach depends on attributes the step-1 file did not
     record.
9. **Validity must be proven per item.** Section 6 has the details.
   - About 29% of HLE chemistry and biology keys were contradicted by the literature (catalogue).
     Epoch's 2026-08 audit found 22 of 48 sampled HLE items (46%) defective.
   - BrowseComp found 21 bad keys among the 118 items Deep Research never solved.
   - Anthropic: "0% pass@100 is most often a signal of a broken task".
   - Benchmarks that survive scrutiny re-derive every key independently, adjudicate model "wrong"
     answers, and bound failure rates statistically.
   - Section 6 ends with an automatable checklist.
10. **The binding constraint is fairness, not cleverness.** Every past internal "bite" that failed
    both models at a high rate traced to a defensible second reading. The recipes below specify,
    for each trap, the sentence that makes the right answer unique.

---

## 1. Near-miss decoys that actually work against strong models with tools

### 1.1 Findings

| # | Source (date) | Setting | Finding (quoted numbers) | Tag |
|---|---|---|---|---|
| 1 | GSM-Symbolic / GSM-NoOp, Apple (2024-10-07; rev. 2025-08-27) https://arxiv.org/abs/2410.05229 | {no-tools} | "Adding a single clause that seems relevant to the question causes significant performance drops (up to 65%) across all state-of-the-art models, even though the clause doesn't contribute to the reasoning chain." Mechanism: "models tend to convert statements to operations without truly understanding their meaning", for example "statements about 'discount' as 'multiplication', regardless of context". Eight shots of the *same* question with the NoOp clause solved: "performance remains within the standard deviation". o1-preview scores 77.4% on GSM-NoOp (appendix table). | V (o1 number A) |
| 2 | LLMs Can Be Easily Distracted by Irrelevant Context (GSM-IC), Shi et al. (2023-01-31) https://arxiv.org/abs/2302.00093 | {no-tools} | Accuracy drops with irrelevant context. Two mitigations work: self-consistency, and "adding to the prompt an instruction that tells the language model to ignore the irrelevant information". | A |
| 3 | Context Rot, Chroma (2025-07-14) https://www.trychroma.com/research/context-rot | {no-tools; 18 models} | "Even a single distractor reduces performance relative to the baseline ... adding four distractors compounds this degradation." "Distractors do not have uniform impact." "As needle-question similarity decreases, model performance degrades more significantly." "Structural coherence consistently hurts model performance." Families: "Claude models consistently exhibit the lowest hallucination rates ... tend to abstain when uncertain ... GPT models show the highest rates of hallucination." These are 2025 models (Claude 4, GPT-4.1); the direction has reversed for Fable 5.1 vs Astra (§4.1). | V |
| 4 | RULER (2024-04; v3 2024-08-06) https://arxiv.org/abs/2404.06654 | {no-tools} | Multi-key NIAH: "The additional 'needles' are hard distractors." In the version full of distractor needles, the model "often returns values from the vicinity of the target, suggesting coarse match of the range but the lack of precision" (Yi-34B, about 40 points lost at 256K). | V |
| 5 | BrowseComp-Plus (2025-08-08) https://arxiv.org/abs/2508.06600 | {tools: search} | Fixed corpus of 100,195 documents; per query, "6.1 evidence documents, 76.28 negatives". Negatives were mined by splitting each question into about 7 sub-queries with GPT-4o and searching the web, so each matches *part* of the constraints. GPT-5 scores 55.9% with BM25 and 70.1% with Qwen3-Embedding-8B. GPT-5 and o3 issue "more than 20 search calls per query". The partial-match negatives are filtered by constraint-by-constraint checking. | V |
| 6 | BRIGHT (2024-07-16; v4 2025-03-26) https://arxiv.org/abs/2407.12883 | {retrieval} | The MTEB leader's nDCG@10 falls from 59.0 to 18.3 when relevance needs reasoning "beyond surface form matching". Reasoning about the query adds up to 12.2 points. | V (abstract) |
| 7 | HaystackCraft, "Haystack Engineering" (2025-10-10) https://arxiv.org/abs/2510.07414 | {agentic multi-round} | "For 11 out of 12 cases, the dense retriever ... introduces more challenging distractors than ... BM25." "All models, including ... Gemini 2.5 Pro and GPT-5, are vulnerable to cascading errors." "Most models fail to terminate the process appropriately." Models are "more robust to wider contexts than noisier reasoning iterations". | V |
| 8 | MUDDLE (2026-08-30) https://arxiv.org/abs/2608.29477 | {no-tools; gpt-5-mini detailed} | "Hard negatives lower accuracy more than length-matched random documents at both context sizes." Random documents stay near baseline. | V (abstract) |
| 9 | MIRAGE (NAACL Findings 2025) https://aclanthology.org/2025.findings-naacl.157/ | {no-tools} | RAG metrics for noise vulnerability and context misinterpretation. Moving from top-3 to top-5 chunks adds enough noise to reduce accuracy for weaker models. | A |
| 10 | **TrustDABench** (2026-08-25) https://arxiv.org/abs/2608.24145 | **{tools: Python + Bash sandbox; GPT-5.5, Claude Sonnet 5, Gemini 3.1 Pro, Qwen3.7-Max, DeepSeek-V4-Pro, GLM-5.2 and 2 more}** | Perturbations are semantics-preserving. ASR = how often one "causes failure on a task that the model originally solves". **Non-observation row injection** ("adds records explicitly marked as not being observations": subtotal/total/notes/header-repeat rows) "ranks first" for every model. Cross-sheet relayout is second for 7 of 8 and "strongly model selective". Level-3 operators (decoy feature pack, non-observation rows) are "2.82×" more effective than level-0 operators (row/column shuffles, header synonyms, **semantic distractor column** such as "net profit/operating profit"). Models "rarely produce even a partial indication" that such rows should be excluded. Mean ASR: Claude Sonnet 5 9.10%, GPT-5.5 13.23%. | V (definitions, ranking); A (ASR means) |
| 11 | WDC Products, Peeters et al. (EDBT 2024) https://arxiv.org/abs/2301.09521 | {matchers} | Corner cases are "matching or non-matching pairs that closely resemble the opposite class". As their share rises from 20% to 80%, Ditto falls from 86.39 to 72.18 F1. GPT-4 reaches 89.61 F1 (later LLM study). | A |
| 12 | **Billiger.de Products** (2026-09-29) https://arxiv.org/abs/2609.37713 | {no-tools; GPT-5.2 zero-shot} | Negative corner case: "offers for two variants of the same wardrobe that agree in brand, model name, and nearly the entire description and differ only in some or a single attribute". Positive corner case: "matching offers whose surface forms are dissimilar". GPT-5.2 scores 75.96 F1 with a simple prompt and **81.29 with a rule-guided prompt**. | V |
| 13 | DELEGATE-52, "LLMs Corrupt Your Documents When You Delegate" (2026-04-17) https://arxiv.org/abs/2604.15597 | {with and without tools; Gemini 3.1 Pro, Claude 4.6 Opus, GPT 5.4} | Frontier models "corrupt an average of 25% of document content by the end of long workflows". "All models degrade documents more with tools than without" (about 6 points more). Removing distractor documents helps 0.4-4% early and "2-8% by the end of the simulation". | V |
| 14 | Is Grep All You Need? (2026-05-14) https://arxiv.org/abs/2605.15184 | {tools: Claude Code, Codex, Gemini CLI} | "Grep generally yields higher accuracy than vector retrieval." Scores "depend strongly on which harness and tool-calling style is used". The CLIs retrieve lexically, so the decoy problem becomes a predicate problem. | V (abstract) |
| 15 | GSM-DC (EMNLP 2025) https://arxiv.org/abs/2505.18761 | {no-tools} | Irrelevant context on the reasoning graph affects both path selection and arithmetic; training with strong distractors improves robustness. | A |
| 16 | Internal near-miss census (2026-09-29, local) | {tools: our harness} | Both models print the documented misreading's value next to the right one before writing (448 hits; Astra 302, Fable 146). "A trap whose decoy is a nameable alternative computation is enumerated and rejected." Fair misses that occur: Astra 8/70 on a listing whose only link is `m.facebook.com`; Astra 5/5 on a set named `S08`/`508`/`Model Set 508`; Fable 5/43 on a scope under a revised premise. | local |

### 1.2 What makes a decoy bite: eight properties

Each property is stated as a design rule and backed by the sources above.

1. **It satisfies the agent's selection predicate.**
   - The decoy shares exactly the surface features the agent filters on: the keyword, the entity
     name, the model number, the column header.
   - Evidence: NoLiMa ("when literal matches serve as distractors, they severely impair accuracy");
     Context Rot (similarity drives the drop); MUDDLE (topical hard negatives beat random ones);
     DAB (the `MALE` regex matches inside `FEMALE`).
2. **It differs only in an attribute the predicate never reads.** The difference is real, explicit
   and decisive, but sits in a field, marker or clause outside the agent's filter.
   - The NRI rows *are* marked, and agents still aggregate them (TrustDABench).
   - Billiger's negative corner cases differ "only in some or a single attribute".
   - The mirror image is the positive corner case. The true member *lacks* the surface feature
     (`m.facebook.com`, `S08`), so the predicate drops it.
3. **It agrees with the right answer almost everywhere.** Totals, counts and reconciliations
   computed with the decoy included or excluded still look plausible, so the agent's assertions pass.
   - Catalogue entry 7: verification inherits the misreading.
   - SpreadsheetBench 2: per-error fixes of 72% collapse to a 7% final pass.
4. **It is not a nameable alternative.** If the decoy produces a second candidate value *for the
   same field*, both models compute both and choose (internal, 448 hits). A bite needs the
   alternative never to surface.
   - Of Fable's 45 failed decisions, the 22 with no hedge were the fair traps, where "the second
     reading never surfaced".
   - The 23 hedged failures were coin-flip wording decisions.
   - Where Fable hedged on a fair trap, it was almost always right (study 9/9, seo 8/8, brand
     15/15).
5. **It sits where the agent has no reason to look twice.** Examples: a file opened for a different
   field, a marker in a column the computation does not use, a legend in another document.
   - Solving-vs-Verifying: contradictions are caught when the model is asked to verify, and missed
     in solve mode.
   - TrustDABench: nothing prompts a row-type check.
6. **It agrees with the prior.** The decoy reading matches the conventional default, and the right
   reading is unusual but explicit.
   - MemoryAgentBench uses counterfactual facts.
   - TIDE: "often follow a confident parametric answer over the authoritative text".
   - HANDBOOK.md perturbs the thresholds of every base handbook, so memorised policy is wrong.
7. **It is never announced.**
   - GSM-IC: an instruction to ignore irrelevant information restores accuracy.
   - Billiger: a rule-guided prompt adds 5.3 F1.
   - The exception-chain paper: "evaluate each exemption independently" changes the error
     direction.
   - Internally, announced traps were found in 30 of 30 episodes.
8. **It is embedded in coherent prose.** Context Rot found coherent haystacks harder than shuffled
   ones, and dense-retriever (semantic) distractors harder than BM25 (lexical) ones (HaystackCraft).
   A decisive near-miss inside a realistic email thread is harder than the same fact in a table.

### 1.3 Decoy styles measured dead (or nearly dead) against tool users

| Style | Why it dies | Evidence |
|---|---|---|
| Stale or draft *number* next to the governing one; alternative computation | Computed side by side and rejected | Internal: 448 hits; `plausible_decoy` 1.16%, `stale_authority` 1.12% per check attempt |
| Partial-constraint candidates, each constraint independently checkable | The agent checks constraint by constraint and searches more | BrowseComp-Plus: 76 mined negatives per query, GPT-5 still 70.1% and over 20 searches |
| Similarly named column with a clear header or dictionary entry (net vs operating profit) | Read and disambiguated | TrustDABench: the semantic distractor column is level 0, the least effective tier |
| Exact-ID near-duplicates (RULER-style keys) | `grep` on the exact key | RULER failures are no-tools; Is Grep All You Need? |
| Volume, filler and irrelevant documents | A REPL removes the aggregation bottleneck | RLM/Oolong (catalogue); DELEGATE-52 shows only 0.4-8% from removing distractors |
| Any decoy the instruction mentions or warns about | Becomes a check | GSM-IC; Billiger; internal 30/30 |
| Precedence stated plainly ("document A governs") | Applied | Internal: `governing_precedence` 0/90; catalogue §3 |

### 1.4 Recipes for fair, deterministic decoys

General rule for every recipe:
- The deciding attribute is stated **once, in general form, in a document**, never in the
  instruction.
- The grader derives membership from per-record attributes held in grader data and the fixture
  (catalogue R9).
- Each misreading gets an executed counterexample carried through every output it touches.
- Keep each affected population small (1-4 members).

**D-1. Non-observation rows: TrustDABench's strongest operator, moved into a register.**
- *Files.* A ledger or register of 40-120 rows, plus a data dictionary or legend in a *different*
  file.
  - Two to four rows carry a type code whose meaning is defined only in the legend, for example
    `entry_type` = `MEMO`, `REV` (a reversal of row N), `B/F` (balance brought forward), `PF`
    (pro-forma) or `DUP-REF` (copy for reference).
  - Alternatively, a textual marker in the description, such as "(reversal of #1043)" or "‡ = shown
    for reference, not posted".
- *Rule (in the policy).* "Totals and counts are over posted entries only. Entry types are defined
  in Appendix B."
- *Tempting answer.* Sum or count every row. This is the default `pandas` aggregation.
- *Why it bites.* The marker is explicit but in a column the computation never reads. TrustDABench
  measured this as the top failure for both families, with tools. Reconciling to the export footer
  agrees if the footer was also computed over all rows (property 3).
- *Fairness.*
  - The legend defines every code in one sentence.
  - No code is used with two meanings.
  - A careful human reading the legend gets one answer.
  - Do not rely on visual formatting (strike-through, grey fill) that text extraction may lose.
- *Checks.* Total, count, per-category breakdown and one downstream threshold verdict. Cap the
  blast radius: no more than 50% of objectives may depend on this one misreading.

**D-2. Negative corner case: a near-duplicate that differs in one decisive attribute.**
- *Files.*
  - A rate card or eligibility list keyed on product variant (pack size, region code, edition,
    legal entity, contract version).
  - Two catalogue entries or two vendors that agree in brand, name and nearly the whole
    description and differ only in that attribute.
  - Transactions referencing both.
- *Rule.* "Eligibility and rates attach to the variant as identified by [attribute] in the rate
  card."
- *Tempting answer.* Join on name or model and merge the two.
- *Fairness.* The attribute is printed on every relevant record. The rate card lists the variants
  as separate rows.
- *Family note.* This is untested on either model. It is the mirror image of D-3, so use both for a
  two-sided case.

**D-3. Positive corner case: the same entity under dissimilar surface forms.**
- *Files.* One entity named in two to four forms across files:
  - prefix letter or zero padding (`S08`/`508`);
  - host variant (`m.`/`www.`);
  - trade vs legal name;
  - transliteration;
  - a legacy code linked in a registry.
- *Rule.* Identity is defined in general terms. Examples: "a supplier is identified by its
  registry number; trading names are listed in the registry", or "any facebook.com host".
- *Tempting answer.* Exact-string join, which yields two entities, or a dropped member.
- *Evidence.* Internal Astra 8/70 and 5/5, the only verified genuine Astra bite. Fable rarely misses
  this; its single miss was in step 2.
- *Fairness.* The equivalence must be stated or mechanically derivable from a registry in the
  folder. Never rely on world knowledge.

**D-4. Keyword-bearing but out of scope, plus in-scope paraphrases.**
This is catalogue entry 1 (DAB regex behaviour). Composition:
- 4 keyword hits that qualify;
- 3-4 keyword hits that each fail exactly one clause (negated, hypothetical, quoted, wrong object);
- 2-3 paraphrases that qualify without the keyword;
- one substring collision.
The grep set is the tempting answer.

**D-5. Decoy feature pack: TrustDABench level 3, "task related features that are irrelevant to the
correct solution".**
- *Files.* The data carries plausible extra columns, such as `adjusted_amount`, `net_of_credit` and
  `fx_rate_prior`. The governing definition (in the policy, not the dictionary) uses a different
  basis, for example "commission is computed on the invoiced amount before credits".
- *Tempting answer.* Use the column whose name matches the concept: `net_of_credit` for "net
  revenue".
- *Fairness.* The definition fixes the basis in one sentence. The dictionary describes each column
  truthfully. The trap is choosing a column by name.
- *Distinguish from the dead style.* A distractor column is dead when its header names its scope
  and the rule uses the same words. D-5 is alive only when the policy's wording and the column names
  do not line up lexically.

**D-6. An operative-looking inert clause (GSM-NoOp, moved into documents).**
- *Files.* A record or email states a fact that *sounds* like an adjustment ("five of the units
  arrived slightly scuffed", "the client paid two days late"). The governing rule makes the fact
  irrelevant ("acceptance is by count; condition claims are handled under §9 and do not alter
  quantities"; "late-payment interest applies only after 30 days").
- *Tempting answer.* Subtract or adjust: the NoOp "convert statements to operations" behaviour.
- *Evidence status.* Measured no-tools on 2024 models only. Treat it as a hypothesis for our pair.
- *Fairness.* The rule that neutralises the clause must be explicit and nearby in meaning, though
  not lexically. Write the strongest argument for applying the adjustment, and make sure the rule
  defeats it.

**D-7. Cross-sheet relational layout (TrustDABench CSR, "strongly model selective").**
- *Files.* Records in one sheet; adjustments, splits or reversals in a second sheet keyed by record
  ID; a third sheet with effective dates.
- *Rule.* "Each record's final value is its base value as adjusted in Sheet 2, effective per
  Sheet 3."
- *Tempting answer.* Use sheet 1 alone, or apply adjustments without effective dates.
- *Note.* This decoy works by layout, so pair it with a membership decision, not a computation the
  agent can reconcile.

**D-8. A self-agreeing cross-check (catalogue entry 7), used as the amplifier for D-1 to D-6.**
- An export footer, a "working tally", or a summary tab computed with the naive reading. The rule
  names the authoritative source.
- This only amplifies. On its own it is a dead "stale number" decoy.

**Placement rule for all recipes.**
- Put the decisive attribute in a file the agent opens for another reason (property 5).
- Put the defining sentence in a third file, in the general form of a rule that matters for the
  whole task.
- Never put both next to the decoy.

---

## 2. What-not-how instruction design

### 2.1 Findings

| # | Source (date) | Setting | Finding | Tag |
|---|---|---|---|---|
| 1 | **WorkArena++** (2024-07-07; rev. 2025-02-05; NeurIPS 2024 D&B) https://arxiv.org/abs/2407.05291 | {tools: browser agent on ServiceNow} | L2 "contains the precise steps required to complete the task". L3 arrives as "a ticket assigned to them. The ticket includes key details necessary to complete the task but does not specify the steps required to solve it." Results: GPT-4o L1 42.7%, L2 3.0%, **L3 0.0%**; GPT-4o-v L2 3.8%, L3 0.0%; humans **93.9%**. | V (definitions, model rates); A (human split per level) |
| 2 | **GDPval** (2025-10-05) https://arxiv.org/abs/2510.04374 | {tools in the OpenAI harness} | The under-specified variant is "42% the length (by token count)" of the original prompt, with data location and format expectations removed. "GPT-5 performed worse as it struggled to figure out requisite context." Exact win rates are not comparable: "run on an earlier version of the GDPval gold subset". "89.07% of tasks were rated as well-specified"; "an average of five human reviews (with a minimum of three reviews)". | V |
| 3 | **Harvey LAB, introduction** (2026-05-06) https://www.harvey.ai/blog/introducing-harveys-legal-agent-benchmark | {tools} | 1,200+ tasks, 24 practice areas, 75,000+ expert criteria (about 62 per task). Instructions are "written as a request for work from a partner to an associate" and are "affirmative statements of what is required rather than detailed explanations"; about 50 words. One example task has 57 criteria across nine legal issues. All-pass: "A deal-team report that identifies eight of ten risks is not 80% useful; it is materially incomplete." | V |
| 4 | **What Makes a Good Terminal-Agent Benchmark Task** (Bercovich, 2026-04) https://arxiv.org/abs/2604.28093 | guideline | "Write the instruction as if it's intended for a smart human. Clear, but not redundant." "I see every token as an opportunity to mistakenly add ambiguity." "Real difficulty is conceptual. Can the agent figure out the approach?" Clerical, format-compliance or width-over-depth difficulty is "tedious", not hard. "Over 15% of tasks were demonstrably reward-hackable" across five public terminal-agent benchmarks. | V |
| 5 | **τ-bench** (2024-06-17) https://arxiv.org/abs/2406.12045 | {tools + simulated user} | "The key challenge is to ensure the user instruction leads to a unique database outcome." Method: "write an initial user instruction, run a trial with gpt-4-turbo ... polish the user instruction by examining the trajectory, and do this iteratively until we are certain no ambiguities exist." Policies are markdown documents. Failure shares for gpt-4o retail: wrong argument about 52%, wrong decision about 25%, partial resolution of compound requests about 19%. | V (quotes); A (shares) |
| 6 | **HANDBOOK.md** (2026-07-28; rev. 2026-08-03) https://arxiv.org/abs/2607.25398 | {tools: MCP services; deterministic} | 65 tasks under an "expert-written standard operating procedure of 20-124 pages". "Every task modifies one of 10 base handbooks, altering the specific rules and thresholds on which grading depends". "Grading is fully deterministic", with 824 programmatic criteria (about 12.7 per task). Best strict pass is 36.2%; "most frontier models remain below 25%". Failures: agents "let a plausible but unauthorized in-environment request override the standing policy, perform a required check and then act against its result, lose rule details over long horizons, and report compliance they did not achieve." Per model (Q5 fork, from the HTML): Fable 5 36.2% (adaptive/max) and 34.2% (default); GPT-5.6 Sol 23.5%; Opus 4.8 21.9%. | V (abstract); V-fork (per model) |
| 7 | **LongDA** (2026-01-05) https://arxiv.org/abs/2601.02598 | {tools: doc retrieval + code} | Documentation averages "263,000 tokens per query". GPT-5 (High) reaches a 68.91% match rate. "The core difficulty of LongDA lies not in logical inference, but in discovering and extracting sufficient information from long, complex documentation." | V (summary quotes) |
| 8 | Spider 2.0 (2024-11) https://arxiv.org/abs/2411.07763 | {tools} | Solving "frequently requires understanding and searching through database metadata, dialect documentation, and even project-level codebases". o1-preview agent 21.3%, against 91.2% on Spider 1.0 and 73.0% on BIRD. | V (abstract) |
| 9 | BIRD (2023) https://arxiv.org/abs/2305.03111 | {no-tools} | External-knowledge "evidence" hints. ChatGPT dev 24.05 → 37.22 with evidence; GPT-4 30.90 → 46.35; Claude-2 28.29 → 42.70. Evidence types: numeric reasoning, domain knowledge, synonyms, value illustration. *Without* the evidence some items are underdetermined, so this is a definition, not procedure. | V |
| 10 | **SpreadsheetBench 2** (2026-06-29) https://arxiv.org/abs/2606.29955 | {tools: SWE-agent scaffold, bash + view_xlsx, 50 turns} | "Instructions do not explicitly specify error types or target cells." Debugging: Opus 4.6 12.00%, GPT-5.2 8.00%, Gemini 3.1 Pro 7.00%. Partial fixes: "can fix individual errors reasonably often (72% on Template ...) but its final pass rate collapses (to 7% ...)". | V (summary quotes) |
| 11 | SOP-Bench (2025-06; v2 2026-02-23) https://arxiv.org/abs/2506.08119 | {tools: function-calling / ReAct} | Procedures live in SOP documents. "Claude 4 Opus: 72.4% vs. Claude 4.5 Sonnet: 63.3%"; best results "range from 57% to 100% depending on domain". | V (abstract) |
| 12 | Ambig-SWE, "Interactive Agents to Overcome Underspecificity" (2025-02-18; ICLR 2026) https://arxiv.org/abs/2502.13069 | {tools} | "Models struggle to distinguish between well-specified and underspecified instructions." Interaction improves results "up to 74% over the non-interactive settings". | V (abstract) |
| 13 | What Prompts Don't Say (2025-05-19; rev. 2026-04-24) https://arxiv.org/abs/2505.13360 | {no-tools} | LLMs "can often infer unspecified requirements by default (41.1%)", but under-specified prompts are "2x as likely to regress across model or prompt changes, sometimes with accuracy drops exceeding 20%". | V (abstract) |
| 14 | AmbigQA (2020-04-22; EMNLP 2020) https://arxiv.org/abs/2004.10645 | {no-tools} | "Over half of the questions in NQ-open are ambiguous." This is *outcome* ambiguity, the kind that must never be used as difficulty. | V (abstract) |
| 15 | GAIA (2023-11-21) https://arxiv.org/abs/2311.12983 | {tools} | Questions are "conceptually simple for humans yet challenging for most advanced AIs". Answers are "factoid, concise and unambiguous". Validation asks "two new annotators to independently answer each question. If the original annotator and the two new annotators arrived at the same answer, the question was validated." Humans 92% vs GPT-4 with plugins 15%. | V |
| 16 | τ²-bench (2025-06-09) https://arxiv.org/abs/2506.07982 | {tools; dual control} | "Significant performance drops when agents shift from no-user to dual-control." | A |
| 17 | Catalogue entries reused | | DABstep: agents fail when they "need to follow rules implicitly mentioned in the context" (Hard 14.55% vs Easy 76.39%). HiL-Bench: blockers "surface only through progressive exploration". Solving-vs-Verifying: solve mode computes through contradictions, verify mode flags them. Exception-chain: one prompt sentence swaps the error direction. | V (catalogue) |

### 2.2 What the evidence says

1. **Removing *procedure* lowers success while human solvability holds.**
   - WorkArena++ is the cleanest case. The tasks are the same and humans score 93.9%, yet GPT-4o
     goes from 3.0% with steps to 0.0% with a ticket plus a knowledge base.
   - DABstep (explicit vs implicit rules), SpreadsheetBench 2 (error types and cells unstated) and
     LongDA (documentation discovery is the bottleneck, not inference) all agree.
   - In each, the outcome is still unique, because it is graded by end state or exact value.
2. **Removing *definitions* creates ambiguity, not difficulty.**
   - BIRD's evidence hints carry definitions ("eligible free rate = ..."). Without them some items
     have several defensible SQL readings.
   - The GDPval under-specified variant removed data location and format, a mix of procedure and
     definition. It made GPT-5 worse, but at the cost of specification.
   - What Prompts Don't Say shows that under-specified *requirements* make results fragile across
     model versions (2x the regressions). That is the opposite of a stable benchmark.
   - The internal a-010 and a-001 "bites" were exactly this.
3. **The instruction must say what is wanted in affirmative terms; the documents carry the rules.**
   - Harvey writes "a request for work from a partner to an associate", "affirmative statements of
     what is required rather than detailed explanations", in about 50 words.
   - Terminal-Bench says to write "for a smart human ... clear, but not redundant".
   - τ-bench, SOP-Bench, HANDBOOK.md, DABstep and WorkArena++ L3 put every operative rule in a
     policy, SOP, manual or knowledge base.
4. **Single-outcome guarantees in hidden-method benchmarks come from five mechanisms:**
   - (a) grading an end state or exact value, not a path (τ-bench database state; Terminal-Bench
     "graded on outcomes, not process");
   - (b) iterative trial runs whose trajectories are read to remove ambiguity (τ-bench, "until we
     are certain no ambiguities exist");
   - (c) independent re-answering by new solvers (GAIA's two annotators; BrowseComp trainers, §6);
   - (d) short, exact, derivable answers (GAIA, BrowseComp);
   - (e) perturbed rule parameters so priors cannot answer (HANDBOOK.md).
5. **Hints are measurably powerful, which is why they must be absent.** Every source that tested a
   hint found it moves accuracy:
   - BIRD +13 points;
   - Billiger rule-guided prompt +5.3 F1;
   - GSM-IC ignore-instruction;
   - verify-mode prompting (catalogue);
   - the exception-chain "evaluate each exemption independently" sentence;
   - internal announced traps 30/30.

### 2.3 Recipes: instruction and rule placement

**W-1. Instruction template.** Keep it under about 150 words of narrative, plus an exact output
contract.
- *Narrative.* Who is asking, what they need and why. State the deliverable in the requester's
  terms ("the list of invoices we can still claim under the revised cap", "the corrected exposure
  figure for the board pack").
- *Output contract.* The schema, with every field defined for *every* case the answer set contains,
  including the negative or non-fitting case and any conditional field. The internal a-010 lesson:
  identical wrong answers across both families mean a field-definition problem.
- *Never in the instruction:*
  - where a rule lives;
  - which document governs (the documents say so);
  - which records are tricky;
  - the deciding attribute;
  - "check", "verify", "reconcile", "note that", "be careful", "including variants",
    "notwithstanding", "watch for".

**W-2. A rule-placement map, authored with the task and hidden from the agent.** Each operative
rule gets exactly one home, chosen to match how real organisations store it:
- policy or SOP section, for definitions and thresholds;
- data dictionary or legend, for codes and units;
- amendment register, for effective dates and supersession;
- rate card or matrix, for parameters;
- email or chat, for casual corrections, with a stated record-of-truth rule.

The map records, for each rule, the sentence that fixes it, and the file opened for another reason
that leads there (HiL-Bench's progressive exploration).

**W-3. Definitions move into documents; they are never deleted.** If the instruction has to define
an output field, define the *field*: "`claimable` = the amount payable to us under the contract
terms in force on the invoice date". Leave the *terms* in the contract and amendment files.

**W-4. Perturbed handbooks.** Start from a realistic base policy and alter two to four parameters
away from the conventional default: a 45-day window instead of 30, a ≤ instead of a <, an
exemption that is unusual but explicit. This is HANDBOOK.md's anti-memorisation method, and it
creates the prior-fight of property 6.

**W-5. A τ-bench-style de-ambiguation loop, before any screen.**
- Run one cheap trial per model.
- Read every point where the trajectory chose between readings: Fable's "judgment call" lines; for
  Astra, the scripts' predicates.
- For each choice, either the documents already decide it, so leave it, or they do not, so fix the
  documents (not the instruction) until they do.
- Re-run until no new choice point appears.
- This is how τ-bench guaranteed "a unique database outcome" with a free-text conversation.

**W-6. Self-test for what-not-how.** If a reader could solve the task from the instruction alone
plus mechanical file reading, the instruction carries the "how". If a careful human with the files
could reach two answers, the documents are under-specified. Both are defects.

---

## 3. Density and all-pass: from about 90% per criterion to 5-20% per task

### 3.1 Published criterion-pass vs all-pass pairs

`n_eff` is the number of *independent* criteria at the mean criterion pass rate that would
reproduce the observed all-pass rate: `n_eff = ln(all-pass) / ln(mean criterion pass)`. It is
computed here, not published.

| Benchmark (date) | Setting | Criteria per task | Mean criterion pass | All-pass | n_eff | Tag |
|---|---|---|---|---|---|---|
| Harvey LAB-AA (Artificial Analysis, 2026-07-07) https://artificialanalysis.ai/articles/harvey-lab-aa | {tools: Stirrup harness with compaction} | LAB average about 62 (75,000 / 1,200); LAB-AA's own count not stated | Fable 5 93.6%; Opus 4.8 91.1%; Sonnet 5 90.1% | 14.2%; 7.5%; 5.0% | 29.5; 27.8; 28.7 | V |
| Harvey LAB held-out (Fable 5.1 system card, 2026-09-01; catalogue) | {tools} | as above | Fable 5.1 90.81% | 19.09% | 17.2 | V (catalogue) |
| **Harvey LAB held-out, Vals run** (2026-09-30; Q4 fork) https://www.vals.ai/benchmarks/hlab | {tools: Vals harness} | as above | **Fable 5.1 86.57%; GPT-6 Astra 87.48%** | **6.67%; 5.42%** | 18.8; 21.8 | V-fork |
| GDP.pdf, Vals (2026-09; Q4 fork) | {tools} | n/a | Fable 5.1 79.7%; Astra 81.8% | 26.2%; 31.0% | 5.9; 5.8 | V-fork |
| Harvey LAB initial (2026-05-26) https://www.harvey.ai/blog/legal-agent-benchmark-initial-results | {tools} | as above | n/a | Opus 4.7 7.1%; Sonnet 4.6 5.4%; Opus 4.6 4.2%; GPT-5.5 2.1%; Gemini 3.5 Flash 0.8% | n/a | V |
| APEX-Agents (2026-01-20) https://arxiv.org/abs/2601.14242 | {tools: ReAct, 250 steps, code_exec} | 4.06 (1-10) | Gemini 3 Flash 39.5%; GPT-5.2 38.7%; Opus 4.5 34.8% | 24.0%; 23.0%; 18.4% | 1.5; 1.5; 1.6 | V |
| AgentIF (2025-05-22) https://arxiv.org/abs/2505.16944 | {no-tools} | 11.9 constraints | o1-mini CSR 59.8% | ISR 27.2% | 2.5 | V |
| HANDBOOK.md (2026-07-28) | {tools; deterministic} | 12.7 | not published | 36.2% best | n/a | V |
| SpreadsheetBench 2 (2026-06-29) | {tools} | per-error fixes | 72% / 47% / 34% (MiniMax M2.5, by split) | 7% / 9% / 3% | n/a | V |
| APIFlow-Bench (2026-08-29) https://arxiv.org/abs/2608.29128 | {tools; 19 models} | 20 subtasks | 93% solo | 74% clean chain | (chains are "33 percentage points above the product") | V (abstract) |
| OSWorld 2.0 (2026-06-28; Q5 fork) https://arxiv.org/abs/2606.29537 | {tools} | partial-credit checkpoints | Opus 4.8 54.8% partial; GPT-5.5 49.5% | 20.6%; 13.0% binary | n/a | V-fork |
| TheAgentCompany (v3 2025-09-10; Q5 fork) https://arxiv.org/abs/2412.14161 | {tools} | checkpoints | 39.3% partial score (best) | 30.3% full | n/a | V-fork |

**Readings.**
0. **The two calibration models are equally exposed to density.**
   - In the same Vals run on the same held-out LAB tasks, Fable 5.1 passes 86.57% of criteria and
     6.67% of tasks. Astra passes 87.48% and 5.42%.
   - The *harness* gap for one model is larger than the family gap. Fable 5.1 scores 6.67% all-pass
     in the Vals run, 16.7% in Artificial Analysis' run, and 19.09% on the system card.
   - Every rate must therefore be reported with its harness.
1. **Legal rubrics behave like about 17-30 independent 90%-criteria.**
   - If LAB's roughly 62 criteria were independent at 93.6%, all-pass would be 1.6%. Observed:
     14.2%.
   - Criteria are heterogeneous: most are near-certain and a minority are fragile. The fragile
     minority does the work.
2. **APEX-Agents and AgentIF are all-or-nothing.**
   - n_eff is about 1.5-2.5 because one upstream failure (not finding the file, a timeout, a wrong
     plan) zeroes the run. "All agents score zero in at least 40% of their runs."
   - Density there adds nothing. The difficulty is a single gate.
3. **Competence is correlated within an episode.** APIFlow's 20-step chains beat the independence
   product by 33 points, and the authors reject the "independent-error account of compounding
   failure". A careful episode tends to get everything right. That correlation is the main enemy
   of density.
4. **Internally, failed episodes are almost single-decision.** There were 104 failed decisions in 99
   failed episodes. Fair misses are idiosyncratic: the alternative "never surfaced" in that
   episode. That is the independence-friendly kind, but the per-decision rates are low (q ≈ 0.01
   overall; 0.10-0.20 on the best fair traps).

### 3.2 How many fragile decisions are needed

Independent decisions, per-decision miss rate q, smallest k with (1−q)^k below the target:

| target pass@1 | q=0.02 | q=0.05 | q=0.10 | q=0.12 | q=0.15 | q=0.20 | q=0.30 |
|---|---|---|---|---|---|---|---|
| < 0.5 | 35 | 14 | 7 | 6 | 5 | 4 | 2 |
| < 0.3 | 60 | 24 | 12 | 10 | 8 | 6 | 4 |
| < 0.2 | 80 | 32 | 16 | 13 | 10 | 8 | 5 |

With within-episode correlation. Beta-binomial, exchangeable correlation ρ, P(all k pass):

| q | ρ | k=8 | k=12 | k=16 | k=20 | k=30 |
|---|---|---|---|---|---|---|
| 0.10 | 0 | 0.43 | 0.28 | 0.19 | 0.12 | 0.04 |
| 0.10 | 0.1 | 0.54 | 0.44 | 0.37 | 0.33 | 0.25 |
| 0.15 | 0 | 0.27 | 0.14 | 0.07 | 0.04 | 0.01 |
| 0.15 | 0.1 | 0.39 | 0.28 | 0.22 | 0.18 | 0.12 |
| 0.20 | 0.1 | 0.27 | 0.18 | 0.13 | 0.10 | 0.06 |
| 0.20 | 0.3 | 0.44 | 0.37 | 0.33 | 0.30 | 0.25 |

(Computed for this report.)

**Implications for the calibration pair.**
- **At today's internal per-check rate (q ≈ 0.01), density cannot work.** It would need about 120
  independent decisions.
- **The target is decisions with q ≥ 0.10 for a given model.** Measured internally, these exist
  only as *silent* scope, identity and convention-reach decisions: Fable 5/43 (0.12), Astra 8/70
  (0.11), Astra 5/40 (0.125), Fable 2/10 (0.2).
- **Per family, plan for 10-12 independent decisions at q ≈ 0.12.** Raise that to about 16 if
  episodes show ρ ≈ 0.1.
- **Because the skews differ, a two-family task needs two portfolios.** Spread both over both steps.
  - *Fable portfolio:* silent population scope, counting-unit boundaries, semantic scope,
    fill-the-gap when an input is genuinely absent, copying a stated figure, scope widening past
    an exclusion.
  - *Astra portfolio:* surface variants, the reach of a convention or rounding rule, withholding
    when the files do resolve a conflict, omitting conditionally required elements, a parameter
    that lives in communications.
  - Section 4 gives the evidence for each.
- **Routing several checks through one decision does not lower pass@1 below that decision's
  success rate.** It only guarantees the miss is counted. Density comes from *more independent
  decisions*, not more checks per decision. Keep each decision's blast radius at no more than 50%
  of objectives.

### 3.3 Which criterion types are most fragile

| Type | Evidence | Setting |
|---|---|---|
| Implicit requirements and multi-document synthesis | ResearchRubrics (2025-11) https://arxiv.org/abs/2511.07685: "implicit reasoning and synthesis jointly account for 45-50% of all failures"; explicit requirements and communication show "failure rates below 20%"; "performance degrades monotonically with increased logical nesting depth" | {tools: deep-research agents} V (quotes) |
| Conditional constraints and constraints that refer to tools or documents | AgentIF: condition constraints 61.4% vs vanilla 80.8%; tool constraints 43.2% | {no-tools} V |
| Acting on a check already run; policy overridden by in-environment requests | HANDBOOK.md abstract | {tools} V |
| End-to-end correctness after local fixes | SpreadsheetBench 2: 72% → 7% | {tools} V |
| Row-type and boundary semantics | TrustDABench NRI ranks first for every model | {tools} V |
| Population scope, convention reach, surface identity, counting unit | Internal census ranks 1-5 | {tools: our harness} local |
| Revised values / first plausible instance | OfficeQA Pro (catalogue) | {tools} V |
| Facts, conclusions, citations, severity, deadlines, dollar amounts, formatting | LAB rubric categories; no public per-category failure split was found | {tools} V (categories only) |

### 3.4 Recipes for density

**N-1. A fragility budget sheet, authored with the task.** One row per fragile decision, with:
- mechanism type;
- targeted family;
- file(s) where it is decided;
- the noticing trigger (what would make an agent look);
- expected q per model (from the census or a prior screen);
- the checks it feeds;
- the counterexample ID.

The sheet must show at least 10 decisions per targeted family, of at least 4 mechanism types, with
no two decisions sharing a noticing trigger.

**N-2. Independence by construction.**
- Different mechanisms, different files and different output fields.
- No decision whose discovery reveals another: one "aha" must not solve two rows.
- Avoid a single upstream gate (APEX-style) unless that gate *is* a fragile fair decision.
- Prefer register items whose decisive attributes differ in kind: one by legend code, one by
  surface identity, one by effective date, one by scope clause.

**N-3. Measure q and ρ after every screen, not just pass@1.**
- From the 5 × 2 screen, compute per-decision miss rates and pairwise phi correlations across
  episodes, then predict pass@1 from the beta-binomial.
- If the prediction is far from the observed rate, decisions are not independent, or one
  decision dominates.
- This turns hardening from guesswork into budget arithmetic.

**N-4. Grow by replacement.** Under the 12-objective cap, add fragile *decisions* inside existing
objectives (members of an exact set), not new objectives. An exact-set objective with 10 members
decided by 6 different mechanisms carries 6 independent decisions in one check.

---

## 4. Model-family skews: what bites Claude (Fable 5.1) and what bites GPT (GPT-6 Astra)

**Read first.**
- No public source measures our pair on document audits.
- The sources cover neighbouring snapshots (Opus 4.6-5.5, GPT-5.3-6) in other harnesses.
- The harness effect is as large as the family effect. The same Fable 5.1 scores 6.67% all-pass on
  LAB held-out in Vals' run and 16.7% in Artificial Analysis' run.
- `V-fork` = read in the primary text by the parallel research fork. `V-spot` = re-checked for this
  report.

### 4.1 Claude family (Fable 5.1 and neighbours)

| Finding | Numbers (quoted) | Setting | Source, tag |
|---|---|---|---|
| **Over-attempts on knowledge gaps** (reverses the 2025 picture) | "Claude Fable 5.1 (max) attempts 93.4% of AA-Omniscience questions against Claude Opus 5's 87.8%"; "of questions it did not get correct, it attempted to respond in 72.6% against Claude Fable 5's 63.6%". The card: Mythos 5.1 "is less likely to abstain" than Mythos 5 | {no-tools} | Artificial Analysis, 2026-09-01 https://artificialanalysis.ai/articles/claude-fable-5-1 `V-spot`; Fable 5.1 card §6.5.1 `V-fork` |
| **Copies a reported figure instead of diagnosing** | With the paper PDF supplied, accuracy on non-reproducible tasks "dropped from 100.0% to 63.3% for Claude Code and from 100% to 90.0% for Codex ... they tend to extract the expected numerical output" | {tools: Claude Code (Opus 4.6) vs Codex (GPT-5.3-Codex)} | SocSci-Repro-Bench, 2026-06 https://arxiv.org/abs/2606.11447 `V-fork` |
| Weaker on curated multi-prong rule application | "margins up to +41 points on the curated multi-prong tasks against the Anthropic models"; on a 20-scenario extension three of four configurations, "including Anthropic's strongest model at evaluation time, fail the same coverage-gap edge case" | {no-tools} | Exception-chain paper https://arxiv.org/abs/2607.23386 `V-spot` |
| The nested-exception *denial* closed | Opus 4.6: 0/70 on 7 failing scenarios in March 2026; **67/68** on the full set in April, same prompt and harness | {no-tools} | Same paper, later version `V-fork` |
| Over-eager; widens scope | "slightly more willing than Opus 5 to bypass approval gates ... overeager". Prompting docs: "can be proactive enough to fix nearby problems, extend behavior" | audit; docs | Fable 5.1 card §6.4.5; Anthropic Fable 5.1 prompting guide `V-fork` |
| Credits unverifiable authority | "accepts unverifiable claims of authorization somewhat more readily than Opus 5" | behavioural audit | Fable 5.1 card `V` (catalogue) |
| Uses leaked answers silently | "used a leaked answer without disclosure 70.1% of the time" | agentic | Fable 5.1 card §6.5.4 `V` (catalogue) |
| Loses on instruction following, not formatting (older snapshot) | "Claude, Grok, and Gemini most often lost due to instruction-following failures, while GPT-5 high lost mainly from formatting errors" | GDPval, Opus 4.1 | https://arxiv.org/abs/2510.04374 `V` |
| Sees the problem, submits anyway | "in 45% of alignment failures, the agent explicitly recognizes ... that it is stuck and submits anyway" | {tools: SWE-Agent, Opus 4.6} | HiL-Bench `V` (catalogue) |
| Long, document-reading behaviour | Vals Tax: Fable 5.1 answers average 2,366 words, all-pass 49.22%. OfficeQA Pro: Opus 4.6 makes 65% of tool calls with Read | agentic | Vals Tax (2026-09-29) `V-fork`; OfficeQA Pro `V-fork` |
| Hedges visibly; misses silently | Internal: a "judgment call" line in 9.8% of steps. Fair misses occur when the alternative never surfaced | {tools: Claude Code} | trajectory-nearmiss-report (local) |

### 4.2 GPT family (GPT-6 Astra and neighbours)

| Finding | Numbers (quoted) | Setting | Source, tag |
|---|---|---|---|
| **Pauses or asks rather than assuming; sensitive to conflicting guidance in files** | "It is also more likely to ask for clarification where earlier models would make assumptions." "This can cause it to stop when the user may expect it to make reasonable assumptions and persist." "Unclear or conflicting guidance in a skill file may cause the model to pause and block work early." | vendor guide | OpenAI, "Using GPT-6" https://developers.openai.com/api/docs/guides/latest-model `V-spot` |
| **Terse; omits required elements** | "The shortest answers come from GPT-6 Astra (956 words) ... whose All-Pass rates (20.7% ...) are the two lowest ... consistent with answers that omit required elements" (Fable 5.1 49.22%) | {tools: agentic tax research} | Vals Tax Agent Bench, 2026-09-29 https://www.vals.ai/benchmarks/tax_agent_bench `V-fork` (the page's "determining which rules ... apply" sentence `V-spot`) |
| Few turns on long deliverables | GDPval-AA: 24 turns per task at max effort vs 60 for Fable 5.1. AA-Briefcase: 39 vs 105 turns; rubric pass 52.0% vs 61.5% | {tools: Stirrup} | Artificial Analysis, 2026-09-09 https://artificialanalysis.ai/articles/benchmarking-gpt-6-astra `V-fork` |
| Leaks scope across chained tasks | Doubling the intervening tasks from five to ten "roughly doubled the observed flag rate, from 8.6% to 19.7%", for example "carrying information between unrelated tasks" | dots harness | GPT-6 Astra card §12.3.5.2 https://deploymentsafety.openai.com/gpt-6-astra `V-fork` |
| Confident execution on wrong beliefs (older GPT) | "73-93% of tool-use failures involve calling the right tool with wrong parameters"; under-asking (GPT-5.3-Codex: 56% precision, 18% recall) | {tools: SWE-Agent} | HiL-Bench `V` |
| Programs the answer | Codex with GPT-5.4: "~90% of tool calls leveraging OCR and PDF CLI tools". Internal: Astra asserts in 98% of steps and writes via Python in 92% | {tools: Codex} | OfficeQA Pro `V-fork`; internal |
| Skips searching communications for parameters (GPT-5.6 Sol) | GPT-5.6 Sol and Kimi K3 "searched communications on only about 15% of runs". Astra has the highest Pass^4 (56.3%) | {tools} | Mercor, APEX-Agents 1.1, 2026-09-08 https://www.mercor.com/blog/introducing-apex-agents-1-1/ `V-fork` |
| Immune to narrative misdirection | Astra "observed misalignment rate of 0.00% across 151 tasks" in dots; instruction hierarchy 99.99% (catalogue) | dots | Astra card §12.3.5.3 `V-fork` |
| Respects barriers | "unwanted persistence appeared in only 19% of GPT 6 Astra rollouts" (GPT-5.6 Sol 64%) | professional environments | Astra card §8.2 `V-fork` |

### 4.3 Shared weaknesses with no family skew: the base layer

- **Density hits both equally.** Vals LAB held-out: Fable 5.1 6.67% of tasks at 86.57% of criteria;
  Astra 5.42% at 87.48% (§3.1). On Vals Legal Research, Opus 5 scores "90.58% weighted pass rate but
  55.29% under strict all-pass" `V-fork`.
- **Conflicting authority hurts everyone when it is real legal authority.** "Reconciling
  conflicting authority is the most reliable failure mode ... a drop of 6 to 17 points per model and
  11 points when pooled" (Vals Legal Research `V-fork`). This contrasts with our internal finding that
  a *stated* precedence rule is solved (0/90). The difference is that legal authority conflicts need
  doctrine to resolve, while ours state the winner.
- **Choosing the rule is harder than computing.** "Determining which rules and rulings apply to a
  given task remain harder than computing the right figure" (Vals Tax `V-spot`).
- **Both follow the documents, and both anchor on their own commitments.** A contradicting
  document alone is followed 99.1% of the time by Claude and 98.4% by GPT-5.5. After the model has
  committed to its own answer, those fall to 85.1% and 84.0% (Three Regimes, 2026-05
  https://arxiv.org/abs/2605.11574 `V-fork`).
  - "Fight the prior" adds little against document-following models.
  - Self-anchoring on an earlier answer, which is our step 2, is shared.
- **Both claim success and skip list items.** "72% of Opus's failures ... 84% of GPT 5.4's involved
  this false confidence"; models "process some items correctly and then summarize as if done"
  (AutomationBench, 2026-04 https://arxiv.org/abs/2604.18934 `V-fork`).

### 4.4 Two-sided levers for fair deterministic document tasks

Each lever needs one defensible answer and a rule published in the files. "Half A" targets one family
and "half B" the other. Use both halves in the same task.

1. **Withhold vs fill-the-gap.**
   - *A, for Astra (pause/withhold).* Two documents disagree on one field. A precedence clause in a
     third document settles it. The right output is the resolved value; withholding or "cannot
     determine" is wrong.
   - *B, for Fable (over-attempt, 72.6%).* One item's required input is genuinely absent. The output
     enum defines `NOT_DETERMINABLE` in the instruction's field definition. Fable tends to fill the
     gap from its own step-1 file or from priors.
   - *Fairness.* Both outcomes are decided by explicit text: the precedence clause, and the absence
     of any source for the field.
2. **Conditionally required elements vs scope widening.**
   - *A, for Astra (terse, omits).* A policy appendix makes a note or field mandatory only when a
     condition holds (2-4 items). Grade the set of items carrying it exactly.
   - *B, for Fable (extends scope).* The same appendix excludes a class of items. Exact-set grading
     catches the extras.
3. **A stated figure vs re-derivation.**
   - *B, for Fable (copies reported figures, 100 → 63.3%).* A prior analyst memo quotes an expected
     total. One input it relied on is superseded in the amendment register, so the rule makes the
     correct figure differ.
     - The memo must not be a side-by-side "stale number" (§1.3). Its figure is aggregated at a
       different grain, so it cannot be recomputed directly.
     - Never say "check the memo".
   - *A, for Astra.* Pair it with lever 1A.
4. **One programmatic predicate vs a prose reading.**
   - *A, for Astra.* One entity under several surface forms (D-3). Internally Astra failed 8/70 and
     5/5.
   - *B, for Fable.* A counting-unit boundary (heading vs body, label vs description) in the same
     population. Internally Fable failed 9 times and Astra 0.
5. **Multi-prong rule with a carve-back gap.**
   - Leans Claude; over-application hits both families.
   - Base rule, exemption, carve-back in a footnote, and a later "notwithstanding" override.
   - One item qualifies only through the override. One loses the exemption to the carve-back.
   - State the prongs in a table and the carve-back in prose. The paper attributes the GPT-5.4
     errors to prompt-format sensitivity.
6. **Parameters that live only in communications.**
   - Targets GPT-5.6-class models (searched communications in only about 15% of runs). For Astra the
     evidence is mixed.
   - A convention (rounding stage, fiscal-year label) sits in an email thread that the policy cites
     only in general terms.
   - *B, for Fable.* The same thread carries an unverifiable "approved verbally" claim that the
     authority matrix voids (the card on unverifiable authorisation).
7. **Step 2 changes scope (shared).** Step 2 narrows the population by an effective date, and the
   grader derives step 2 from the files.
   - Astra's chained-task leakage doubled with more intervening tasks (8.6 → 19.7%).
   - Both families follow their own committed answer more (85%).
   - Internally, Fable re-uses its step-1 file in 94% of step-2 runs.
8. **Literal-value requirements (weak, shared).** A field must carry a governing document's exact
   clause ID or label. AutomationBench: models "paraphrase or outright ignore requirements for the
   content to include certain values". Use this only as an extra check, never as the main trap.

### 4.5 Claims the evidence does NOT support

- **"Claude abstains or over-hedges."** False for Fable 5.1 on closed-book knowledge (72.6%
  over-attempt vs Astra's 44.8-51.3%). The 2025 "Claude refused up to 70%" figure (cross-evaluation,
  catalogue entry 4) is superseded. Fable's hedging today is visible prose, not abstention.
- **"Claude denies under nested exceptions."** That was a March 2026 Opus 4.6 snapshot, closed by
  April (67/68). It is untested on Fable 5.1. Catalogue entry 3 should carry this caveat.
- **"GPT misses surface variants."** External support is indirect (tool-use style, wrong-parameter
  failures, DAB with GPT-5.2). The direct evidence is internal only, and it failed to transfer twice
  (a-010, a-015).
- **"Astra hallucinates or reward-hacks more."** Its card and AA show the reverse. The 59.6%
  honeypot figure and the METR cheating record belong to GPT-5.6 Sol.
- **"Astra is lazy."** The only evidence is user anecdotes `[A]`. OpenAI confirms the stop-to-ask
  disposition, but no knowledge-work measurement of truncated deliverables exists for Astra beyond
  Vals Tax's short-answer note.
- **Sycophancy splits.** SPINE measured Sonnet 5 and GPT-5.6 Terra, not our models. The Astra card
  has no sycophancy metric.
- **Any family gap smaller than the harness gap** (6.67% vs 16.7% for one model) cannot be claimed
  without our own 5 × 2 screens.

## 5. Long-horizon work and state: what survives a fresh-session step 2

### 5.1 Findings

`V-fork` means a parallel research fork read the primary HTML. Items marked `V-spot` were re-checked
for this report.

**Self-conditioning and compounding.**
- **The Illusion of Diminishing Returns** (Sinha et al., 2025-09-11; rev. 2026-03-13)
  https://arxiv.org/abs/2509.09677 `{no-tools, plan given}` `[V-fork]`.
  - "Models become more likely to make mistakes when the context contains their errors from prior
    turns."
  - "Thinking mitigates self-conditioning."
  - Steps executed in a single turn: GPT-5 2176, Claude-4 Sonnet 432.
  - Implication: high-effort thinking models are partly protected, so the lever has to be a wrong
    *premise*, not a wrong token.
- **APIFlow-Bench** (2026-08-29) https://arxiv.org/abs/2608.29128 `{tools; 19 models}` `[V-spot]`.
  - Solo subtasks score 93% and clean 20-subtask chains 74%, which is "33 percentage points above
    the product of subtask-level rates".
  - The authors attribute this to correlated competence.
  - "77% of failing runs drove the world to the correct final state and failed only at final
    delivery."
- **METR, Measuring AI Ability to Complete Long Tasks** (v4 2026-07-10)
  https://arxiv.org/abs/2503.14499 `{tools}` `[V-fork]`.
  - 80% horizons are "4-6x shorter" than 50% horizons.
  - "Models perform worse on tasks that have higher messiness scores."
  - Agents struggle "where the agent needs to proactively seek out relevant information".
  - The METR page (2026-05-08) says "Measurements above 16 hrs are unreliable". It has no public
    Fable 5.x or GPT-6 entry `[V-fork]`.
  - Our tasks take minutes and lie far inside every frontier horizon. Length is not the lever.

**Long runs with tools.**
- **Vending-Bench** (2025-02) https://arxiv.org/abs/2502.15840 `[V-fork]`.
  - Derailments come from "misinterpreting delivery schedules, forgetting orders, or descending
    into tangential 'meltdown' loops".
  - The data "does not support" input length as the sole explanation.
- **Vending-Bench 2 leaderboard** (2026) https://andonlabs.com/evals/vending-bench-2 `[V-fork]`.
  - GPT-6 Astra is first at $15,514.70 ± 1,074. Claude Opus 5 has $11,181.87. Fable is not listed.
  - Top models show "no signs of performance degradation".
  - Astra has no long-run coherence weakness to exploit.
- **OSWorld 2.0** (2026-06-28) https://arxiv.org/abs/2606.29537 `{tools; median 1.6 h, 318 calls}`
  `[V-fork]`.
  - Opus 4.8 scores 20.6% binary and 54.8% partial; GPT-5.5 13.0% and 49.5%.
  - Dynamic tasks, where "a new email can arrive ... forcing it to revise the reimbursement plan
    and re-check earlier decisions", score lowest.
  - Agents spend "under 7%" of budget on recovery.
- **HANDBOOK.md** (2026-07-28) https://arxiv.org/abs/2607.25398 `[V-spot abstract]`. See §2.1 row 6:
  agents "lose rule details over long horizons".
- **UltraHorizon** (2025-09-26) https://arxiv.org/abs/2509.21766 `[V-fork]`.
  - Root causes: "in-context locking", premature convergence and error propagation.
  - Humans score 26.52 and the best model 14.33.
- **TheAgentCompany** (v3 2025-09-10) https://arxiv.org/abs/2412.14161 `[V-fork]`.
  - 30.3% full completion against 39.3% partial score.
  - Agents "deceive oneself" with fake workarounds.
- **DELEGATE-52** (2026-04-17), §1.1 row 13 `[V]`.
  - Frontier models corrupt about 25% of document content over long delegated workflows.
  - Tools make it worse.
- **Traverse, "Locating Hidden Failures"** (2026-09-15) https://arxiv.org/abs/2609.17930 `[A]`.
  - 2,518 human-annotated trajectories.
  - Agents "rarely recover after initial mistakes".
  - The strongest frontier judges find the initial mistake in "fewer than one-third of runs".

**Cross-session memory and update propagation.**
- **MemoryAgentBench** (catalogue `[V]`). Multi-hop selective forgetting peaks at 28% accuracy or
  less.
- **Supersede** (2026-06-25) https://arxiv.org/abs/2606.27472 `[A, abstract]`.
  - Replacing full context with "a bounded, self-maintained memory drops accuracy from 92% to 77%
    even on a frontier model (gpt-5.4)".
  - "The bottleneck is therefore memory maintenance, not comprehension."
- **MemoryArena** (2026-02-18; rev. 2026-09-17; ICML 2026) https://arxiv.org/abs/2602.16313
  `[V-fork]`. "Small errors in the agent's implicit state estimate accumulate across sessions and
  eventually dominate downstream decisions."
- **STALE** (2026-05-07) https://arxiv.org/abs/2605.06527 `[V-fork]`.
  - State resolution 92.0%, premise resistance 30.0%, implicit policy adaptation 71.0%.
  - "Systems often retrieve updated evidence but fail to act on it in downstream behavior."
- **When Stale Constraints Go Unchecked** (2026-08-26) https://arxiv.org/abs/2608.25553 `[V-spot]`.
  - 16 models. Agents "inspected its provenance path in about one episode in five".
  - Stale-consistent decisions in "77.3%, 74.7% and 74.7%" of episodes.
  - Path selection rises from 17.0% with 2 slots to 88.7% with 4 of 6.
  - The effect depends on a **scarce reading budget**, which our agents do not have.
- **PASB, persistent sycophancy** (2026-07-12; rev. 2026-09-27) https://arxiv.org/abs/2607.10526
  `[V-spot]`.
  - Downstream failure "reaches 71.9% when the follow-up chat can read a saved claim, against 45.0%
    when the claim stays in the first chat".
  - The claim is saved as preference, fact or procedure "in 51.4% of runs".
  - Harnesses: Hermes-Agent and OpenClaw, 12 models.
- **When Upstream Messages Override Correct Answers** (2026-09-29) https://arxiv.org/abs/2609.36855
  `[A]`.
  - An upstream message flips a correct answer in "up to 32% of cases".
  - "In 94% of audited harmful cases, the downstream agent copies the upstream's specific wrong
    answer."
- **Anthropic engineering posts.**
  - Context engineering (2025-09-29), `[V-fork]`: "overly aggressive compaction can result in the
    loss of subtle but critical context whose importance only becomes apparent later".
  - Long-running harnesses (2025-11-26), `[V]`: each new session has "no memory of what came
    before", and the model is "less likely to inappropriately change or overwrite JSON files
    compared to Markdown".
  - Harness design (2026-03-24), `[V-fork]`: a model evaluating its own work ends up "confidently
    praising the work—even when ... obviously mediocre".
- **Internal** (trajectory report).
  - Both harnesses start step 2 fresh. Fable reads its step-1 file in 94% of step-2 runs and Astra
    in 81%.
  - Fable "recovered" a step-2 rule by fitting it to its own wrong step-1 figure.
  - Astra withheld when context existed only in the step-1 prompt, 8/23. That is a defect, not
    difficulty.

### 5.2 What does and does not survive a fresh step 2

**Fair levers.** All rest on rules in the files and are graded from the files.

| Lever | Mechanism | Evidence |
|---|---|---|
| (a) The premise change reaches items through an attribute the step-1 file did not record | The step-1 file is a lossy summary, like a compaction. Patching it cannot reveal the reach; only the sources can | Supersede 92→77; Anthropic compaction quote; MemoryArena |
| (b) Self-anchoring on step-1 values when step 2 changes a convention (rounding reach, cut-off, unit) | The saved file acts as a trusted upstream message | PASB 71.9 vs 45.0; 94% copy the specific wrong answer; internal thesis-002 |
| (c) Multi-hop propagation into items decided in step 1 | Retrieve-but-do-not-act | MemoryAgentBench ≤28%; STALE 71% implicit adaptation |
| (d) Two-sided delta: the change removes some step-1 members and re-admits others | Agents treat step 2 as a patch and re-check little | OSWorld 2.0 dynamic tasks lowest, under 7% of budget on recovery |
| (e) A step-2 document presupposes the stale state while the governing amendment differs | Premise resistance is weak | STALE premise resistance 30%; HANDBOOK in-environment override |

**Defects or dead levers.**
- Context that exists only in the step-1 prompt (a defect).
- A step-2 target computed from the agent's own step-1 answer. It rewards consistency, not
  correctness.
- Long context or many steps. Agents grep; Vending-Bench failures are not explained by length;
  APIFlow shows correlated competence.
- Scarce-budget effects. The stale-constraint effect largely disappears at 4 of 6 reads.
- Thinking-model self-conditioning on token errors (Illusion: "thinking mitigates").

### 5.3 Recipes for two-step tasks

The grader rule common to all of them:
- Step-2 targets are expressions over the fixture plus the step-2 documents only. The grader never
  reads the agent's step-1 file.
- The step-2 reference runs with no step-1 file present, which proves self-containment.
- Two counterexamples are required, and both must fail: one "consistent with own step-1 answer" and
  one "patched only the literally named items".

- **S-1. The attribute the summary dropped.**
  - Step 1's schema records ID and verdict only.
  - The step-2 notice revises a clause that applies to items with an attribute stated only in the
    sources (governing law, signature channel, sub-type). It touches 2-3 step-1 members.
  - Tempting answer: re-filter the step-1 list on the fields it already holds.
- **S-2. A convention re-applied to figures already computed.**
  - Step 2 extends the reach of a rounding rule or moves a period cut-off. Two or three step-1
    values sit at the boundary and flip.
  - Tempting answer: copy the step-1 numbers, or re-round only the headline.
  - Evidence: Astra misses the reach of a rounding rule 5/40.
- **S-3. A retirement that propagates through a mapping.**
  - Step 2 retires code T1. The rules refer to T1 only through a group or range defined in another
    file's appendix.
  - Tempting answer: remove literal "T1" hits.
- **S-4. Re-admission.**
  - One step-2 change both removes a step-1 member and re-admits an item that step 1 excluded under
    the clause now removed.
  - Tempting answer: removal-only, by diffing the step-1 list.
- **S-5. A stale-presupposing memo.**
  - A colleague's step-2 memo computes from the old threshold "as agreed last week". The amendment
    register, which the instruction names in general terms as the record, has the new value.
  - The memo's figures use another grouping, so they are not side-by-side comparable (property 4).
- **S-6. A carry figure only the sources can supply.**
  - Step 2 needs a column (exposure, hours) that the step-1 schema never exported.
  - Tempting answer: estimate from step-1 aggregates.
- **S-7. A settled constraint in the step-1 file, withdrawn for a subset in step 2.**
  - The step-2 instruction does not mention the constraint.
  - This is the least certain recipe: the measured effect needed scarce budgets. Screen it before
    relying on it.

---

## 6. Fairness and validity: proving a hard item is fair

### 6.1 Findings

| Source (date) | Method | Quoted numbers | Tag |
|---|---|---|---|
| HLE paper (v11 2026-07-28) https://arxiv.org/abs/2501.14249 | Adversarial filter, then two review rounds | "over 70,000 attempts, resulting in approximately 13,000 questions which stumped LLMs"; "each question receiving between 1-3 reviews" | V-fork |
| FutureHouse HLE audit (2025-07-23) https://www.futurehouse.org/research/hle-exam | Agent screen of 321 bio/chem items; expert check | "29.3 ± 3.7% (95% CI) ... directly conflicted by research". Cause: inclusion required that frontier models fail, which "led to many 'gotcha' adversarial-type questions" | V-fork |
| **Epoch review of HLE** (2026-08-11) https://epoch.ai/benchmarks/hle/review | Fable 5 prompted to surface errors; every error audited by hand | "22 of 48 questions, or 46%, were defective": 12 impossible, 10 false negatives, 5 false positives | V-spot |
| HLE-Verified (2026-02-17) https://arxiv.org/abs/2602.13964 | Expert screen, model replication at pass@8, two independent repairs, adjudication | Of 2,500: 641 gold, 1,170 revised, 689 uncertain (counts differ between versions); revised items gain 30-40 points | V-fork |
| **BrowseComp** (2025-04-16) https://arxiv.org/abs/2504.12516 | Must defeat GPT-4o, o1 and early Deep Research; 5-search check; 10-minute rule | "317 / 367 (86.4%)" trainer–reference agreement. "Upon reviewing the 118 tasks where Deep Research had a 0% pass rate, we identified 21 tasks where the labeled ground-truth answer was either mismatched ..., ambiguous in phrasing, or incorrect" (17.8%). "We cannot be certain that there were no other answers." | V-spot |
| BrowseComp-Plus (2025-08-08) | 14 annotators, 400+ hours of evidence verification | 830 of 1,005 queries kept; over 80% agreement | V-fork |
| GPQA (2023-11-20) https://arxiv.org/abs/2311.12022 | Writer, expert, revision, second expert, 3 non-experts with web access | Experts 65% ("74% when discounting clear mistakes"); non-experts 34% after 37 minutes | V-fork |
| SWE-bench Verified (2024-08) | 93 developers, 3 annotators per item, severity scale 0-3 | 38.3% underspecified; 61.1% unfair tests; 68.3% filtered | A |
| Epoch review of SWE-bench Verified (2026-09-03) https://epoch.ai/benchmarks/swe-bench-verified/review | Audit of failed tasks | "audited 27.6% of the tasks ... 59.4% had flawed test cases that rejected functionally correct submissions" | V-fork |
| Epoch review of Terminal-Bench 4.0.0 (2026-09-04) https://epoch.ai/benchmarks/terminal-bench-4/review | Review of public issues | "30 out of 66 tasks (45.5%) contain publicly noted scoring defects" | V-fork |
| Terminal-Bench 2.0 (ICLR 2026) https://arxiv.org/abs/2601.11868 | Oracle; "a no-op 'dummy' agent should fail"; exploit agent; two auditors | "Approximately three hours of combined reviewer attention" per task | V-fork |
| Epoch review methodology (2026) https://epoch.ai/data/benchmark-reviews-documentation/methodology | Stratified sample of 50, expanded to 100 if the error rate is 15-25% | "Flawed" if "≥20% of inspected sample contains errors"; "≥ 5 [runs] recommended" | V-fork |
| FrontierMath (v7 2025-12-23) and v2 audit (2026-06-12) | Blind review; full audit | Blind review estimated "approximately 10%" from 2 of 35; the later audit addressed "errors in 42% of problems" | V-fork |
| ABC, Agentic Benchmark Checklist (v5 2025-08-07) https://arxiv.org/abs/2507.02825 | Task, outcome and reporting validity items | On τ-bench an empty-response agent scores "38%"; errors shift results "by up to 100% in relative terms" | V-fork |
| **Anthropic, "Demystifying evals for AI agents"** (2026-01-09) https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents | Practice guide | "A 0% pass rate across many trials (i.e 0% pass@100) is most often a signal of a broken task, not an incapable agent." "A good task is one where two domain experts would independently reach the same pass/fail verdict." CORE-Bench went from 42% to 95% after fixing grading that "penalized '96.12' when expecting '96.124991…'" | V-spot |
| Berkeley RDI, "How We Broke Top AI Agent Benchmarks" (2026-04-08) https://moogician.github.io/blog/2026/trustworthy-benchmarks-cont/ | Exploit agents on 8 benchmarks | "near-perfect scores without solving a single task" | V-fork |
| Platinum benchmarks (2025-02-05) https://arxiv.org/abs/2502.03461 | Inspect every item any LLM gets wrong | "The majority of errors can be attributed to label noise rather than genuine model failures" | V-fork |
| LLM-ensemble label audit (rev. 2025-09) https://arxiv.org/abs/2410.18889 | Ensemble confidence against the label | Above 95% confidence, "over two-thirds of those labels are human errors" | V-fork |
| GAIA (2023-11-21) | Two new annotators answer independently | Validated only if all three answers agree | V |
| GDPval (2025-10-05) | Average of 5 reviews, minimum 3 | 89.07% rated well-specified | V |
| APEX-Agents (2026-02) | Experts who did not write the tasks re-solved 20% (n=96) from scratch | Judge accuracy 98.5% over 747 criteria | V-fork |
| Correlated errors (ICML 2025) https://arxiv.org/abs/2506.07962 | 350+ LLMs | "Models agree 60% of the time when both models err" | A |

### 6.2 Lessons

1. **Adversarial filtering selects for wrong keys.** Defects concentrate in items that no model
   solves: BrowseComp 21/118 among Deep Research's 0% items; HLE 29% (FutureHouse) and 46% (Epoch);
   SWE-bench Verified 59.4% of the audited failures. An all-fail check is a suspected defect until
   it is adjudicated (Anthropic: "0% pass@100 is most often a signal of a broken task").
2. **Process alone does not prevent defects.** Terminal-Bench put about 3 reviewer-hours, an oracle
   and an exploit agent into each task, and later shipped a version with 45.5% publicly noted
   defects. FrontierMath's 10% estimate became 42% under a full audit. Audit *every* item, with a
   model surfacing candidates and a human or a rule confirming.
3. **An oracle proves solvability, not uniqueness.** BrowseComp: "we cannot be certain that there
   were no other answers." Uniqueness needs independent solvers (GAIA, GPQA, HLE-Verified's two
   repairs) and a strongest-counter-reading test.
4. **Agreement against the key is evidence, not proof.** An ensemble confident at over 95% against a
   label is right more than two-thirds of the time, but strong models share 60% of their errors. So
   identical wrong answers across families trigger blind adjudication, never an automatic void.
   The internal a-010 case (both families gave the *same* wrong value) was a field definition.
5. **Outcome validity needs both directions.** Equivalent answers must pass (CORE-Bench 42→95%).
   Trivial, shotgun and decoy answers must fail (ABC: τ-bench's empty agent scored 38%).
6. **Bounds, not point estimates.** One-sided 95% Clopper-Pearson upper bounds:

   | passes / episodes | upper bound |
   |---|---|
   | 0/5 | 0.451 |
   | 0/10 | 0.259 |
   | 1/10 | 0.394 |
   | 2/10 | 0.507 |
   | 0/20 | 0.139 |

   A claim of pass@1 < 0.5 needs 0/5 or at most 1/10. A claim below 0.3 needs 0/10 or at most 2/20.

### 6.3 Automatable validation checklist

| # | Check | How to automate | Source of the lesson | Pass criterion |
|---|---|---|---|---|
| V1 | Oracle derivation | Reference script recomputes every target from the fixture; grade it 3 times | Terminal-Bench oracle; ABC T.9 | 1.0 every run; byte-identical targets |
| V2 | Independent re-derivation | A fresh solver from the *other* family gets only the files and instruction (no spec, grader or notes), k=3, and justifies each field with a quote; compare field by field | GAIA, GPQA, HLE-Verified, BrowseComp 86.4% | Every disagreement resolved by a quoted fixture sentence |
| V3 | Strongest counter-reading | For every trap field and every conditional or negative case of every output field, a model argues the alternative; three blind judges rate both readings | SWE-bench Verified severity; Epoch "multiple interpretations"; HLE "gotcha" | No judge rates the alternative defensible |
| V4 | Minimal-pair source counterfactual | Flip one decisive sentence or row (modality, date, alias, legend code) and recompute targets and oracle | Contrast sets; §0 derived-not-stored | Only the predicted fields change; oracle 1.0 on the new fixture |
| V5 | Misreading counterexamples | Each documented misreading becomes a full answer, carried through every field it touches | Terminal-Bench dummy agent; Platinum | Fails exactly the predicted checks |
| V6 | Reworded-answer acceptance | Equivalent forms: order, case, whitespace, numeric format, declared aliases | ABC O.a.1; CORE-Bench | All pass. Normalisation never lets a near-miss value pass |
| V7 | Trivial and shotgun agents | Empty, all-null, all-items, union of candidates, fixture copy, decoy answer | ABC R.13; τ-bench 38% | Each below the bar; no check is vacuous |
| V8 | Leak scan and exploit agent | Search fixture, instruction, image and environment for serialized targets; verifier paths unreadable in the agent phase; "cheat" agent | RDI; SWE-bench+ 32.67% | No target found; exploit scores 0 |
| V9 | Scaffolded solvability | Solver told which documents govern (never values), k=5 | Anthropic pass@100; BrowseComp | At least 1 of 5 reaches the key, or V2 converged |
| V10 | Statistical bounds | Clopper-Pearson per task and per check, reported with harness and effort | Epoch ≥5 runs; τ-bench pass^k | A difficulty claim stands only if the bound clears the target |
| V11 | Same wrong answer across families | Same wrong value at least twice across both families opens an adjudication | Label-audit ensemble; correlated-errors caveat; internal a-010 | A blind adjudicator, not told which value is the key, picks the key with a quoted sentence at high confidence |
| V12 | Every repeated wrong answer adjudicated | Any wrong value seen at least twice, from either family | Platinum; Epoch SWE-bench Verified audit | Each classified as model error or defect; no defect remains |
| V13 | Inverse-ability flag | Across the batch, flag checks that stronger configurations fail more often than weaker ones | IRT audit | Every flag adjudicated |
| V14 | Batch audit rate | A model surfaces impossible, false-negative and false-positive items; a human confirms | Epoch (Flawed at ≥20%) | Confirmed defect rate under 5% |
| V15 | Re-screen after a model or harness change | Re-run V10-V12 after a version bump | Silent cell closure (exception-chain paper) | Results re-dated; stale ones marked |
| V16 | Hint-lexicon scan of the instruction | Search the instruction for trap-announcing words ("check", "verify", "note that", "including variants", the deciding attribute's literal) and for the decisive file's name | §2.2(5); GSM-IC; Billiger; Solving-vs-Verifying | None present, unless the word is part of the requester's genuine deliverable |
| V17 | Field-definition coverage | For each output field, enumerate the cases present in the answer set (positive, negative, conditional) and confirm the instruction's definition decides each | Internal a-010 | Each case has a deciding sentence |

---

## 7. Integrated blueprint: one task that stacks levers aimed at both families

This is a skeleton, not a built task. Every rate in it is a hypothesis for a 5 × 2 screen. The domain
is deliberately non-sensitive (a supplier rebate claim), so no safety classifier can confound the
measurement.

**Instruction (narrative, about 90 words, requester voice).** "Finance needs our Q3 rebate claim to
send to the suppliers on Friday. Please work out which Q3 invoices we can claim against, how much we
are owed per supplier, and which invoices need a dispute note attached. Anything you can't settle
from what's here, list separately. The claim pack goes to the board, so the per-supplier totals
need to be right to the cent."
- An output contract follows, with every field defined for positive, negative and conditional cases.
- There are no "check", "verify" or "note that" phrases.
- No file or rule is named.

**Files and where each rule lives (W-2).**

| File | Carries |
|---|---|
| `rebate-programme-terms-v3.pdf` (perturbed handbook, W-4) | Base rule; an exemption; a carve-back in a footnote; a later "notwithstanding" override; the claim basis ("invoiced amount before credits", D-5); the dispute-note condition (lever 2A); the excluded class (lever 2B) |
| `amendment-register.xlsx` | Effective-dated changes, one of them retroactive; the precedence clause that resolves a two-document conflict (lever 1A) |
| `rate-card-by-variant.csv` | Rates keyed on pack size or region (D-2) |
| `supplier-registry.csv` | Registry numbers with trading names: one supplier appears as `S08` / `508` / a trade name (D-3) |
| `ledger-export-q3.csv` + `ledger-legend.md` | About 80 rows. Three are `REV`/`MEMO`/`B/F` rows defined only in the legend (D-1). Extra columns: `net_of_credit`, `adjusted_amount` (D-5) |
| `email-thread-finance.eml` | The rounding convention, reaching thresholds as well (lever 6). A colleague's "CFO approved this verbally" for one invoice; the authority matrix in the terms voids it (lever 6B) |
| `analyst-memo-aug.docx` | An expected per-category total at a different grain, built on a superseded rate (lever 3B, D-8 amplifier) |
| Supplier correspondence | The keyword "rebate" in out-of-scope senses: negated, hypothetical, quoted. One in-scope paraphrase without the keyword (D-4) |

**Fragility budget (N-1).** Each decision is independent by construction (different mechanism,
file and noticing trigger).

| # | Decision | Mechanism | Targets | Feeds |
|---|---|---|---|---|
| 1 | Three legend-coded rows excluded | D-1 non-observation rows | both | claimable set, totals |
| 2 | `S08` = `508` = trade name | D-3 positive corner case | Astra | per-supplier totals |
| 3 | Pack-size variant at a different rate | D-2 negative corner case | both | one supplier total |
| 4 | Claim basis is the invoiced amount, not `net_of_credit` | D-5 decoy feature pack | both | totals |
| 5 | Rounding reaches the threshold value | convention reach | Astra | one boundary invoice |
| 6 | Conflict resolved by the precedence clause | lever 1A | Astra | one invoice in, not "unsettled" |
| 7 | One input genuinely absent | lever 1B | Fable | `NOT_DETERMINABLE` list |
| 8 | Dispute note required only when the condition holds | lever 2A | Astra | dispute-note set |
| 9 | Excluded class kept out | lever 2B | Fable | claimable set |
| 10 | Verbal approval carries no weight | lever 6B / authority | Fable | one invoice out |
| 11 | Memo's total built on a superseded rate | lever 3B | Fable | category total |
| 12 | Qualifies only through the override | nested rule | both (Claude lean) | claimable set |
| 13 | Exemption revoked by the carve-back | nested rule | both | claimable set |
| 14 | In-scope paraphrase without the keyword | D-4 | Fable | claimable set |
| 15 | Keyword hit that fails one clause | D-4 | Astra | claimable set |
| 16 | Step 2: the retroactive amendment re-admits one step-1 exclusion and removes one member | S-4 two-sided delta | both | step-2 set, totals |
| 17 | Step 2: the revised clause reaches items by an attribute not in the step-1 schema | S-1 | both | step-2 set |
| 18 | Step 2: carry figure from a source column step 1 never exported | S-6 | both | step-2 exposure |

**Arithmetic.** Thirteen decisions bear on each family: five family-specific plus eight marked
"both". Assume q ≈ 0.12 per decision for the targeted family (the best fair internal rates). Then:

| decisions | ρ | predicted pass@1 |
|---|---|---|
| 13 | 0 | 0.19 |
| 13 | 0.1 | 0.35 |
| 11 (if two "both" decisions turn out inert for a model) | 0.1 | 0.39 |

That is near the 0.3 target, not safely below it. The "both" decisions are the least certain,
because no per-family rate exists for D-1 to D-5 in our harness.
- If the measured per-decision q falls short, add decisions by replacement (N-4). Do not add
  announcements.
- Under the 12-objective cap, decisions 1-4, 9 and 12-15 all live in one exact-set objective, so
  that objective carries 9 independent decisions.

**Validity gates before the screen.** Run V1-V9, V16 and V17 (§6.3). After the screen, run V10-V12.
Any check failed identically by both families opens V11 before it is counted.

---

## 8. What this report does not establish

- **No source measures our pair, our harness or our task shape.** The closest analogues are
  HANDBOOK.md (deterministic, SOP-governed, Fable 5 36.2%), Vals LAB held-out (both models about
  86-87% of criteria, 5-7% of tasks), TrustDABench (tools, Sonnet 5 / GPT-5.5) and SpreadsheetBench 2.
  Each differs from ours in harness, domain or grading.
- **The NRI, decoy-feature-pack and cross-sheet results come from data-analysis tasks.** That they
  bite on document registers is a hypothesis. TrustDABench's per-operator ASR numbers were not
  available as a table.
- **Several family findings are from older snapshots** (Opus 4.6/4.7, GPT-5.2-5.6) or from vendor
  guidance (OpenAI's "Using GPT-6"). The exception-chain closure shows cells can close within a
  month.
- **The density arithmetic assumes exchangeable correlation.** Real decisions differ in q and pair
  up unevenly. N-3 (measure q and ρ per screen) is the remedy, not the table.
- **Some numbers come from WebFetch summaries of HTML** and may be near-verbatim rather than exact,
  for example the ResearchRubrics per-axis ranges, the GAIA validation percentages (not used), and
  the WorkArena++ human split per level. These are tagged `A` where unchecked. The SWE-bench Verified
  statistics come from a mirror because the OpenAI page returned 403.
- **"What-not-how lowers success without ambiguity" has one clean controlled experiment**
  (WorkArena++, 2024 models). DABstep, SpreadsheetBench 2 and LongDA support it observationally. No
  source tested it on the 2026 pair.

---

## 9. Sources (new to the catalogue unless marked)

| # | Source | Date | URL | Tag |
|---|---|---|---|---|
| 1 | GSM-Symbolic / GSM-NoOp | 2024-10-07; rev. 2025-08-27 | https://arxiv.org/abs/2410.05229 | V |
| 2 | LLMs Can Be Easily Distracted by Irrelevant Context (GSM-IC) | 2023-01-31 | https://arxiv.org/abs/2302.00093 | A |
| 3 | Chroma, Context Rot | 2025-07-14 | https://www.trychroma.com/research/context-rot | V |
| 4 | RULER | 2024-04; v3 2024-08-06 | https://arxiv.org/abs/2404.06654 | V |
| 5 | BrowseComp-Plus | 2025-08-08 | https://arxiv.org/abs/2508.06600 | V |
| 6 | BRIGHT | 2024-07-16; v4 2025-03-26 | https://arxiv.org/abs/2407.12883 | V (abstract) |
| 7 | Haystack Engineering (HaystackCraft) | 2025-10-10 | https://arxiv.org/abs/2510.07414 | V |
| 8 | MUDDLE | 2026-08-30 | https://arxiv.org/abs/2608.29477 | V (abstract) |
| 9 | MIRAGE (RAG) | NAACL Findings 2025 | https://aclanthology.org/2025.findings-naacl.157/ | A |
| 10 | TrustDABench | 2026-08-25 | https://arxiv.org/abs/2608.24145 | V / A |
| 11 | WDC Products | EDBT 2024 | https://arxiv.org/abs/2301.09521 | A |
| 12 | Entity Matching using LLMs | 2023-10-17; EDBT 2025 | https://arxiv.org/abs/2310.11244 | A |
| 13 | Billiger.de Products | 2026-09-29 | https://arxiv.org/abs/2609.37713 | V |
| 14 | DELEGATE-52 (LLMs Corrupt Your Documents) | 2026-04-17 | https://arxiv.org/abs/2604.15597 | V |
| 15 | Is Grep All You Need? | 2026-05-14 | https://arxiv.org/abs/2605.15184 | V (abstract) |
| 16 | GSM-DC | EMNLP 2025 | https://arxiv.org/abs/2505.18761 | A |
| 17 | WorkArena++ | 2024-07-07; rev. 2025-02-05 | https://arxiv.org/abs/2407.05291 | V / A |
| 18 | GDPval | 2025-10-05 | https://arxiv.org/abs/2510.04374 | V |
| 19 | Harvey, Introducing LAB | 2026-05-06 | https://www.harvey.ai/blog/introducing-harveys-legal-agent-benchmark | V |
| 20 | Harvey, LAB initial results | 2026-05-26 | https://www.harvey.ai/blog/legal-agent-benchmark-initial-results | V |
| 21 | Artificial Analysis, Harvey LAB-AA | 2026-07-07 | https://artificialanalysis.ai/articles/harvey-lab-aa | V |
| 22 | Vals, Harvey LAB leaderboard | 2026-09-30 | https://www.vals.ai/benchmarks/hlab | V-fork |
| 23 | What Makes a Good Terminal-Agent Benchmark Task | 2026-04 | https://arxiv.org/abs/2604.28093 | V |
| 24 | τ-bench | 2024-06-17 | https://arxiv.org/abs/2406.12045 | V |
| 25 | τ²-bench | 2025-06-09 | https://arxiv.org/abs/2506.07982 | A |
| 26 | HANDBOOK.md | 2026-07-28; rev. 2026-08-03 | https://arxiv.org/abs/2607.25398 | V |
| 27 | LongDA | 2026-01-05 | https://arxiv.org/abs/2601.02598 | V |
| 28 | Spider 2.0 | 2024-11 | https://arxiv.org/abs/2411.07763 | V (abstract) |
| 29 | BIRD | 2023-05 | https://arxiv.org/abs/2305.03111 | V |
| 30 | SpreadsheetBench 2 | 2026-06-29 | https://arxiv.org/abs/2606.29955 | V |
| 31 | SOP-Bench | 2025-06; v2 2026-02-23 | https://arxiv.org/abs/2506.08119 | V (abstract) |
| 32 | Ambig-SWE (Interactive Agents to Overcome Underspecificity) | 2025-02-18; ICLR 2026 | https://arxiv.org/abs/2502.13069 | V (abstract) |
| 33 | What Prompts Don't Say | 2025-05-19; rev. 2026-04-24 | https://arxiv.org/abs/2505.13360 | V (abstract) |
| 34 | AmbigQA | 2020-04-22; EMNLP 2020 | https://arxiv.org/abs/2004.10645 | V (abstract) |
| 35 | GAIA | 2023-11-21 | https://arxiv.org/abs/2311.12983 | V |
| 36 | APEX-Agents | 2026-01-20 | https://arxiv.org/abs/2601.14242 | V |
| 37 | Mercor, APEX-Agents 1.1 | 2026-09-08 | https://www.mercor.com/blog/introducing-apex-agents-1-1/ | V-fork |
| 38 | AgentIF | 2025-05-22 | https://arxiv.org/abs/2505.16944 | V |
| 39 | APIFlow-Bench | 2026-08-29 | https://arxiv.org/abs/2608.29128 | V (abstract) |
| 40 | ResearchRubrics | 2025-11 | https://arxiv.org/abs/2511.07685 | V (quotes) / A (ranges) |
| 41 | OSWorld 2.0 | 2026-06-28 | https://arxiv.org/abs/2606.29537 | V-fork |
| 42 | TheAgentCompany | v3 2025-09-10 | https://arxiv.org/abs/2412.14161 | V-fork |
| 43 | Adding Error Bars to Evals | 2024-11-01 | https://arxiv.org/abs/2411.00640 | A |
| 44 | Claude Fable 5.1 & Mythos 5.1 System Card (catalogue) | 2026-09-01 | https://www-cdn.anthropic.com/0339e6a7c5c7b87f5c07798616dc32c215d14235/Claude%20Fable%205.1%20&%20Claude%20Mythos%205.1%20System%20Card.pdf | V / V-fork |
| 45 | Claude Opus 5.5 System Card | 2026-09-22 | https://www-cdn.anthropic.com/fc1b44717c85dc068bc6ba5024219938094694bd/Claude%20Opus%205.5%20System%20Card.pdf | V-fork |
| 46 | GPT-6 Astra System Card | 2026-09-03 (upd. 09-09, 09-22) | https://deploymentsafety.openai.com/gpt-6-astra | V-fork |
| 47 | OpenAI, Using GPT-6 (model guide) | accessed 2026-10-02 | https://developers.openai.com/api/docs/guides/latest-model | V |
| 48 | Anthropic, Prompting Claude Fable 5.1 | accessed 2026-10-02 | https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5-1 | V-fork |
| 49 | Artificial Analysis, Claude Fable 5.1 | 2026-09-01 | https://artificialanalysis.ai/articles/claude-fable-5-1 | V |
| 50 | Artificial Analysis, Benchmarking GPT-6 Astra | 2026-09-09 | https://artificialanalysis.ai/articles/benchmarking-gpt-6-astra | V-fork |
| 51 | AA-Omniscience data | accessed 2026-10-02 | https://artificialanalysis.ai/evaluations/omniscience | V-fork |
| 52 | Vals Tax Agent Bench | 2026-09-29 | https://www.vals.ai/benchmarks/tax_agent_bench | V (one quote) / V-fork |
| 53 | Vals Legal Research Bench | 2026-09 | https://www.vals.ai/benchmarks/legal_research | V-fork |
| 54 | SocSci-Repro-Bench | 2026-06 | https://arxiv.org/abs/2606.11447 | V-fork |
| 55 | AutomationBench | 2026-04-21 | https://arxiv.org/abs/2604.18934 | V-fork |
| 56 | Three Regimes of Context-Parametric Conflict (catalogue) | 2026-05-12 | https://arxiv.org/abs/2605.11574 | V-fork |
| 57 | Exception Chain Collapse (catalogue) | 2026-07-25 and later versions | https://arxiv.org/abs/2607.23386 | V / V-fork |
| 58 | HiL-Bench and Scale leaderboard (catalogue) | v4 2026-05-04 | https://arxiv.org/abs/2604.09408 ; https://scale.com/leaderboard/hil | V |
| 59 | The Illusion of Diminishing Returns | 2025-09-11; rev. 2026-03-13 | https://arxiv.org/abs/2509.09677 | V-fork |
| 60 | METR, Measuring AI Ability to Complete Long Tasks; time-horizons page | v4 2026-07-10; 2026-05-08 | https://arxiv.org/abs/2503.14499 ; https://metr.org/time-horizons/ | V-fork |
| 61 | Vending-Bench; Vending-Bench 2 | 2025-02; 2026 | https://arxiv.org/abs/2502.15840 ; https://andonlabs.com/evals/vending-bench-2 | V-fork |
| 62 | UltraHorizon | 2025-09-26 | https://arxiv.org/abs/2509.21766 | V-fork |
| 63 | Supersede | 2026-06-25 | https://arxiv.org/abs/2606.27472 | A |
| 64 | MemoryArena | 2026-02-18; rev. 2026-09-17 | https://arxiv.org/abs/2602.16313 | V-fork |
| 65 | STALE | 2026-05-07 | https://arxiv.org/abs/2605.06527 | V-fork |
| 66 | When Stale Constraints Go Unchecked | 2026-08-26 | https://arxiv.org/abs/2608.25553 | V |
| 67 | PASB (persistent sycophancy) | 2026-07-12; rev. 2026-09-27 | https://arxiv.org/abs/2607.10526 | V |
| 68 | When Upstream Messages Override Correct Answers | 2026-09-29 | https://arxiv.org/abs/2609.36855 | A |
| 69 | Traverse (Locating Hidden Failures) | 2026-09-15 | https://arxiv.org/abs/2609.17930 | A |
| 70 | Anthropic, Effective context engineering; Harness design for long-running apps | 2025-09-29; 2026-03-24 | https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents ; https://www.anthropic.com/engineering/harness-design-long-running-apps | V-fork |
| 71 | Humanity's Last Exam (catalogue) | v11 2026-07-28 | https://arxiv.org/abs/2501.14249 | V-fork |
| 72 | FutureHouse HLE audit (catalogue) | 2025-07-23 | https://www.futurehouse.org/research/hle-exam | V-fork |
| 73 | Epoch, review of HLE | 2026-08-11 | https://epoch.ai/benchmarks/hle/review | V |
| 74 | HLE-Verified | 2026-02-17 | https://arxiv.org/abs/2602.13964 | V-fork |
| 75 | BrowseComp (catalogue) | 2025-04-16 | https://arxiv.org/abs/2504.12516 | V |
| 76 | GPQA | 2023-11-20 | https://arxiv.org/abs/2311.12022 | V-fork |
| 77 | SWE-bench Verified (via mirror) | 2024-08 | https://openai.com/index/introducing-swe-bench-verified/ | A |
| 78 | Epoch, reviews of SWE-bench Verified and Terminal-Bench 4.0.0; methodology | 2026-09-03; 2026-09-04; 2026 | https://epoch.ai/benchmarks/swe-bench-verified/review ; https://epoch.ai/benchmarks/terminal-bench-4/review ; https://epoch.ai/data/benchmark-reviews-documentation/methodology | V-fork |
| 79 | Terminal-Bench 2.0 | ICLR 2026 | https://arxiv.org/abs/2601.11868 | V-fork |
| 80 | FrontierMath; Epoch FrontierMath v2 | v7 2025-12-23; 2026-06-12 | https://arxiv.org/abs/2411.04872 ; https://epoch.ai/benchmarks/frontiermath-tier-4-v2 | V-fork |
| 81 | ABC, Agentic Benchmark Checklist | v5 2025-08-07 | https://arxiv.org/abs/2507.02825 | V-fork |
| 82 | Anthropic, Demystifying evals for AI agents | 2026-01-09 | https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents | V |
| 83 | Berkeley RDI, How We Broke Top AI Agent Benchmarks | 2026-04-08 | https://moogician.github.io/blog/2026/trustworthy-benchmarks-cont/ | V-fork |
| 84 | Platinum benchmarks | 2025-02-05 | https://arxiv.org/abs/2502.03461 | V-fork |
| 85 | LLM-ensemble label-error audit | rev. 2025-09 | https://arxiv.org/abs/2410.18889 | V-fork |
| 86 | Correlated Errors in LLMs (catalogue) | ICML 2025 | https://arxiv.org/abs/2506.07962 | A |
| 87 | τ²-bench issue #384; τ²-Bench-Verified | 2026-07-04; 2026 | https://github.com/sierra-research/tau2-bench/issues/384 ; https://github.com/amazon-agi/tau2-bench-verified | V-fork / A |

Excluded or not found:
- A frontier-model, tool-using entity-resolution benchmark with near-duplicate error analysis. None
  was found. AgenticER (2607.27435) is a vision paper with no results.
- Harvey per-criterion-type failure statistics. Not published.
- METR time horizons for Fable 5.1 or Astra. None published.
- GDPval under-specified win-rate numbers. Not comparable, per the paper.
