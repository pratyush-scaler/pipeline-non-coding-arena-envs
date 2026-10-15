# LIT-A: Persistent reasoning failures that could transfer to file-based desk work

Survey date: 2026-10-15. Research only. No task tree, tool, key or pool was touched.

## How to read this

**Method.** I ran web searches and then opened the arXiv abstract or HTML of most papers cited below. A few were read only through the abstract text that the search returned; they are marked "via search" in Sources. A number is quoted only if I read it on the paper's page or in its quoted abstract text. Anything else taken from a search-engine snippet or a blog is marked **[unverified]**. If a paper gives only figures and no text numbers, I say so and give no number.

**What counts as relevant.** The failure has to hold for reasoning models (o1/o3/GPT-5.x, Claude 3.7/4.x with thinking, Gemini 2.5/3.x, DeepSeek-R1), and it has to survive an agent that:

- `cat`s every file;
- computes in Python;
- re-checks its own work.

Failures that a script removes (aggregation, update streams, date arithmetic) are downgraded, however large the published drop.

**Rating scale.** The rating is the expected miss rate on the checks routed through the mechanism, when it is built as described:

| rating | expected miss rate |
|---|---|
| high | ≥ 50% |
| medium | 20–50% |
| low | < 20% |

Our lab measured single isolated levers at 180/180 solved. So every rating assumes the mechanism sits inside a real workflow and is interlocked with at least one other lever (see "Interlocks" below).

**Where 2026 evidence exists, it beats older evidence.** Several 2026 papers test Claude Opus 4.6/4.8, Claude Sonnet 4.5, GPT-5.2/5.4/5.5 and Gemini 3.1 with thinking at high or maximum effort. They are the closest published proxies for Fable 5.1 and GPT-6 Astra.

---

## Top 8

| # | Mechanism | Strongest evidence (reasoning model, number) | Fable | Astra | Relation to what we measured |
|---|---|---|---|---|---|
| 1 | **Identity by description, not by key**: a mis-keyed record, a key collision, or one entity under two keys | NoLiMa-Hard, o1: 92.0 at 4K → 78.0 at 8K → 60.1 at 16K → 31.1 at 32K when the link has no literal overlap (2502.05167) | high | high | Generalises the keying slip (both models, often 100%) and the near-twin (a-005) |
| 2 | **The newest version wins by default** when an older version governs the record's date | Old-version accuracy: Claude Opus 4.6 (max) **0.014** vs 0.820 for new-version cases; GPT-5.4 (high) 0.237 vs 0.701 (2608.14610). In-context, value in force on a date: GPT-5.2 75.29, Claude Sonnet 4.5 64.06 (2608.08512) | high | medium | Generalises "edition by real receipt date" (Fable 50%) |
| 3 | **A convention implied only by the governing document's worked figures or tables** (day count, banding/lookup, per-started-unit, line-level rounding) | TaxCalcBench: tax-table misuse in 15–20% of cases, with no gain at higher thinking (Opus 4: 27.45 strict at high, 25.00 at ultrathink) (2507.16126). FinIndices: Claude-Opus-4.8 (thinking) falls 65.61 → 38.85 on the table task without formula hints (2607.28661) | medium | high | Generalises the rounding convention (Astra misses; Fable ~40%), tax-inclusive, and per-pack |
| 4 | **Familiar-procedure recitation**: a plainly recorded fact switches off a standard step | RoR-Bench, original → modified: o1 86.08 → 29.87; o3-mini-high 85.95 → 24.94; R1 86.46 → 22.66; Claude 3.7 (CoT) 80.02 → 25.06 (2504.00509). o-series "overfit to problem framings" (2507.14417) | medium | high | Generalises "item already in hand, do not reorder" (Fable 60%) |
| 5 | **Period caliber**: cumulative YTD vs discrete period figures; stock vs flow | FinIndices, caliber alignment on the table task without hints: Claude-4.5 12.79, GPT-5.4 15.12, Gemini-3.1 23.26. A YTD-baseline error gave 202.25% vs a true 58.49% (2607.28661) | medium | medium | New. Differs from the dead "in thousands" lever because no label flags it |
| 6 | **Abstain when the only available source does not govern** | Reasoning fine-tuning cuts abstention by 24% on average (2506.09038). Rejecting a misleading version with gold context: GPT-5.2 26.73, Claude Sonnet 4.5 14.71 (2608.08512) | medium | medium | New. Pairs naturally with #2 |
| 7 | **Iterated revision**: belief inertia plus collateral damage when a rule is revised twice with different scopes | o3-mini and R1 revise better in a single step but "degrade faster under iteration" than chat models (AGM-Bench, ICLR-2026 workshop; no numbers on page). Belief-R: revision score (BREU) about 50% while basic inference is >75% (2406.19764) | medium | medium | Matches our "changed premise" doctrine. The first direct test (a-321) was weak |
| 8 | **A formal-looking secondary summary that has gone stale** vs the primary instrument | TIDE "context misalignment": the model must reject a confidently stated wrong version, with the correct text supplied. Never exceeds 27.62%; Claude Sonnet 4.5 scores 14.71 (2608.08512) | medium | low–medium | A twist on our "official source wins" observation: both sources are official, and the convenient one is wrong |

Ranks 9–11 are below the table: relative-time anchoring to a document event, conditional or modal statements read as facts, and a decisive fact placed in a non-English file.

---

## 1. Identity by description, not by key (latent association without lexical overlap)

**Definition.** Two records belong together, or apart, because of what they describe, not because of a shared key. The model joins lexically and gets it wrong.

**Evidence**

- **NoLiMa** (Modarressi et al., arXiv **2502.05167**). Needle and question share no keyword: "Yuki lives next to the Semper Opera House" must answer "Which character has been to Dresden?".
  - NoLiMa-Hard (Table 5):

    | Model | Base | 4K | 8K | 16K | 32K |
    |---|---|---|---|---|---|
    | GPT-o1 | 99.9 | 92.0 | 78.0 | 60.1 | 31.1 |
    | GPT-o3 Mini | 98.8 | 52.8 | 36.9 | 25.5 | 18.9 |
    | DeepSeek R1-Distill-Llama-70B | 99.9 | 91.4 | 75.5 | 49.4 | 20.7 |

  - GPT-4o on full NoLiMa falls from a base of 99.3 to 69.7 at 32K.
  - A distractor that contains the literal keyword cuts GPT-4o's effective length to 1K.
  - When the options include a literal match, Llama 3.3 70B two-hop accuracy at 32K jumps from 25.9 to 87.2. Literal overlap is what models lean on.
  - **Reasoning models still fail**, and the effect grows with length.
- **HELEA** (arXiv **2605.28308**, search snippet, **[unverified]** beyond the abstract snippet). When hard negatives share the positive's name, a string-match baseline falls to 0.411 accuracy. This is weak evidence: it is not a frontier-LLM result.
- **Our data.** The keying slip is missed by both models, often 100%. The near-twin identity (a-005) is genuinely below 0.5.

**Transfer recipe (three variants of one mechanism)**

- **(a) Key collision.** A supplier restarts invoice numbering each year, so `INV-0007` appears for both 2025-01 and 2026-01.
  - Files: AP ledger CSV, two invoice texts, the supplier's statement of account.
  - Right answer: two distinct liabilities. The statement lists both; the PO references and line items differ.
  - Default wrong answer: dedupe on `(supplier, invoice_no)` and report one.
- **(b) Key split.** After an ERP migration, SKU `44-180` became `A-5521`.
  - The only link is the manufacturer part number and serial range, sitting in the item master's description field, plus a goods-received note that quotes the old code.
  - Right answer: aggregate both codes for the reorder or stock check.
  - Default wrong answer: two items, so a spurious reorder (or a missed one).
- **(c) Mis-keyed record.** Already measured. Keep it.

**How it differs from the dead levers.**

- There is no hidden trigger remark: the identity evidence sits in core records the model must read anyway.
- There is no decoy document.
- No rule is stated.
- The failure is the join itself.

**Validity risk.** "Same entity" can become a judgement call.

**Anchor.** Require at least two independent descriptive anchors (for example serial number plus delivery address, or amount plus date plus PO), each in a system-of-record file. A blind reader must reach the same pairing with no remaining candidate. Ship an executed counterexample showing that the lexical join gives a different deliverable.

**Rating.** Fable **high**, Astra **high**. The rating rests on our own measurements more than on the papers. Variants (a) and (b) are untested here: a collision may be easier to spot than a mis-key, because the duplicate key is visible.

---

## 2. The newest version wins by default (temporal applicability)

**Definition.** Several versions of a rule, price list or standard exist. The model applies the newest one, even when the record's legally relevant date falls under an older one.

**Evidence**

- **"When Do LLMs Apply the Wrong Law?"** (Huang et al., arXiv **2608.14610**, 2026).
  - Setup: Chinese civil cases, about 200 per run, half pre-Code and half post-Code. Every model ran at its highest reasoning effort.
  - Old-version vs new-version accuracy:

    | Model | Old-version | New-version |
    |---|---|---|
    | Claude Opus 4.6 (max) | **0.014** | 0.820 |
    | GPT-5.4 (high) | 0.237 | 0.701 |
    | Gemini 3.1 Pro (high) | 0.135 | 0.843 |
    | DeepSeek-V3.2 (thinking) | 0.092 | 0.746 |

  - Old→new errors make up 0.69–0.94 of the fault mass.
  - A "strong" hint (non-retroactivity, check whether the facts predate the revision) raises GPT-5.4 only to 0.457 and Qwen3-80B to 0.512.
  - More than half of configurations do worse in reasoning mode.
  - **Caveat:** the paper never says the statute texts are supplied. Its memory probe suggests they are recalled, so this is mainly a parametric default.
- **TIDE** (Sobhani et al., arXiv **2608.08512**, 2026). Bangladesh customs instruments, thinking mode enabled for all models, gold context supplied.

  | Task | GPT-5.2 | Claude Sonnet 4.5 |
  |---|---|---|
  | Temporal Scenario SA (value in force on a query date across two or more instruments) | 75.29 | 64.06 |
  | Event Sorting | 66.23 | 60.05 |
  | Relative-Time QA | 59.66 | 68.03 |

  This is the in-context version of the same failure, with misses around 25–36%.
- **"Asking For An Old Friend"** (Prior, Schultz & Grabmair, arXiv **2605.23497**, ICAIL 2026). Names recency bias (preferring newer provisions when a historical one governs) as one of two temporal failure modes. Its web-search-augmented setting showed a "marked recency bias on historically anchored tasks". The models tested are 5 LLMs from OpenAI, Anthropic and DeepSeek. No numbers on the abstract page.
- **Recency bias in reranking** (Fang et al., arXiv **2509.11353**). Injected dates reverse pairwise preference by up to 25% on average. Larger models attenuate the effect, but "none eliminate it". Models tested: GPT-4o/4 and Llama/Qwen.
- **Our data.** "Which edition applies, by when the record was really received vs its logged date" gave Fable 50%.

**Transfer recipe**

- Files:
  - a supply contract whose body says orders accepted before a price change are invoiced at the price in force on the acceptance date;
  - price list v3 (archived attachment) and price list v4, effective 1 April;
  - an April invoice register;
  - order-acceptance emails or EDI acknowledgements. For 3 of 12 orders these are dated late March.
- Deliverable: an overcharge claim per invoice.
- Right answer: the 3 March-accepted orders are owed v3 prices, so their v4 invoices are overcharged.
- Default wrong answer: v4 applied to every April-dated invoice, so no claim.
- Make the newer version the salient one (the price list "on file"). Leave the older one in an archive.

**How it differs from the dead levers.** The clause is stated, but stated rules are not the lever here. The lever is choosing between two dates of similar authority (invoice date vs acceptance date), pulled by a strong prior toward "current". That is the configuration that bit Fable at 50%. It is not the "current date" clock trap: no "now" is inferred.

**Validity risk.** PO date, acceptance date and dispatch date are all plausible candidates for the governing date.

**Anchor.**

- The clause names exactly one date and where to find it ("the date of the supplier's written order acceptance").
- Exactly one acceptance per order.
- No acceptance falls on the effective date itself.
- The archived v3 is complete for the affected SKUs.

**Rating.** Fable **high**: Claude-family recency is the most extreme in 2608.14610 (0.014), and Fable already misses 50% on our edition variant. Astra **medium**: GPT-5.4 was the least biased model, but still 0.237 on old-version cases.

---

## 3. A convention implied only by worked figures or tables

**Definition.** The governing document fixes a computational convention only through its worked examples or its tabulated values. No rule is stated. The model substitutes the textbook default.

**Evidence**

- **TaxCalcBench** (Column Tax, arXiv **2507.16126**). 51 cases, 4 runs, five thinking levels.

  | Model | Strict | Lenient (±$5) |
  |---|---|---|
  | Gemini 2.5 Pro (best) | 32.35% | 51.96% |
  | Claude Opus 4 (high) | 27.45% | 42.65% |

  - The strict-vs-lenient gap is attributed to one error, in **15–20% of cases**: computing tax with the bracket formula instead of the mandated Tax Table lookup. Example: Opus 4 computed $2,789, $3 off the table value.
  - More thinking does not fix it. Opus 4 scores 25.00% strict at "ultrathink" against 27.45% at "high".
- **FinIndices** (Tong et al., arXiv **2607.28661**, 2026). Table-Index accuracy with formula hints → without:

  | Model | With hints | Without hints |
  |---|---|---|
  | Claude-Opus-4.8 (thinking) | 65.61 | 38.85 |
  | GPT-5.5 (thinking) | 66.88 | 34.18 |
  | Gemini-3.1-Pro | 70.70 | 38.22 |

  When the convention has to come from the document rather than an instruction, accuracy roughly halves.
- **McCoy et al.** (arXiv **2410.01792**). o1 still shows probability sensitivity: shift-cipher accuracy is 47% in the lowest-probability case vs 92% in the highest. Unlikely conventions are executed less reliably.
- **Our data.**
  - Rounding implied by worked figures: Astra misses, Fable ~40%.
  - Tax-inclusive price shown only by an indirect cue: Fable 80%.
  - Per-pack vs per-piece pricing: both models miss.

**Transfer recipe (pick conventions with a strong textbook default)**

- **Day count.**
  - Files: a facility or lease agreement whose Schedule 2 shows only a worked interest figure for the first broken period; repayment notices; a drawdown log.
  - Task: compute interest for four later periods, including a February and a period ending on the 31st.
  - Right answer: the convention reproduced from the example.
  - Default wrong answer: actual/365 (or annual ÷ 12).
  - Illustration: on €240,000 at 6% for 1 Jan → 1 Feb, actual/365 gives 1,223.01, actual/360 gives 1,240.00 and 30/360 gives 1,200.00 (computed).
- **Banded lookup.**
  - Files: a carrier rate card printed as weight bands priced "per started 0.5 kg", and a historic invoice that matches the band value.
  - Default wrong answer: weight × per-kg rate.
- **Line-level vs invoice-level VAT rounding.**
  - A worked invoice in the supplier's terms shows VAT rounded per line.
  - The deliverable needs cent-exact totals over about 10 invoices.
- **Inclusive day counting.** A worked example in the SLA counts both end days ("3–7 March = 5 days").

**How it differs from the dead levers.**

- Nothing is stated, so it is not a stated rule.
- There is no "see note 3" pointer.
- Nothing is flagged in thousands.
- The only path to the answer is reproducing a figure. That is the same structure as our working rounding lever.

**Validity risk.** This is the main risk: several conventions may reproduce the same worked example. 30/360 bond basis and 30E/360 differ only when a period ends on the 31st, and a 31-day period can make actual/365 inclusive collide with something else.

**Anchor.**

- Enumerate every common convention, including inclusive and exclusive ends, in an executed counterexample script.
- Choose worked examples (at least two, one of them a February or a 31st) that exactly one convention reproduces.
- Choose graded periods where the convention changes the cent value.

**Rating.** Fable **medium**, Astra **high**. Both are consistent with our rounding measurement and with Gema et al.: o-series models overfit to familiar framings, while Claude models are less prone to that.

---

## 4. Familiar-procedure recitation (a premise that switches off a standard step)

**Definition.** The situation looks like a routine procedure: reorder, dunning, accrual, reimbursement, freight charge. One plainly recorded fact makes a step inapplicable. The model runs the procedure anyway.

**Evidence**

- **RoR-Bench** (Yan et al., arXiv **2504.00509**). Elementary problems with one phrase changed. Text set, original → modified:

  | Model | Original | Modified |
  |---|---|---|
  | o1-1217 | 86.08 | 29.87 |
  | o3-mini-high | 85.95 | 24.94 |
  | DeepSeek-R1 | 86.46 | 22.66 |
  | Claude 3.7 Sonnet (CoT) | 80.02 | 25.06 |
  | GPT-4.5-Preview | 80.89 | 26.59 |

  - The average drop over 23 models is 51.96 points.
  - A "the problem is correct, read it literally" prompt only partly helps: o1 rises to 41.01.
  - Example: a police officer chasing a thief who "did not notice the officer". The right answer is 100/5 = 20 s; the recited answer is 100/(5−3) = 50 s.
- **Inverse Scaling in Test-Time Compute** (Gema et al., arXiv **2507.14417**). Models: Claude 3.7/4 Sonnet, Opus 4, o3/o3-mini/o4-mini, R1.
  - "OpenAI o-series models resist distractors but overfit to problem framings."
  - On birthday-paradox-framed trivial questions, models launch the paradox machinery. o3's accuracy rises when distractors make the framing less recognisable.
- **MATH-Perturb** (Huang et al., arXiv **2502.06453**). On hard perturbations, o1-mini drops −16.49% and gemini-2.0-flash-thinking −12.9%. Models "blindly apply learned problem-solving skills without assessing their applicability to modified contexts".
- **Our data.** "Item already in hand, do not reorder" gave Fable 60%.

**Transfer recipe (one switching fact per item, in a system-of-record file)**

| Scenario | Switching fact | Right | Default wrong |
|---|---|---|---|
| Min/max reorder run | A goods-received note shows the unit arrived but is not yet posted to stock | no reorder | reorder |
| Dunning run (>30 days overdue → reminder) | A credit-note register shows the invoice cancelled by credit note | no reminder | reminder |
| Expense reimbursement | The card-statement export shows the item paid on the corporate card | €0 owed | reimburse |
| Freight accrual | The carrier's manifest shows two orders consolidated on one waybill | one charge | two charges |

The right answer is usually the *simpler* outcome. RoR modifications mostly make the problem easier, and that is what defeats recitation.

**How it differs from the dead levers.**

- It is not a stated rule: no rule changes, a precondition fact does.
- It is not the bimodal hidden trigger: the fact is a primary record of the same authority as the procedure's inputs, not an incidental remark.

**Validity risk.** The model may argue the fact is unposted or provisional.

**Anchor.** Corroborate with a second independent record. For example, the supplier statement shows a zero balance, or the stock count sheet lists the unit. Then no careful reader can keep the procedure's output.

**Rating.** Fable **medium**, measured 60% on our case. Astra **high**: RoR o3-mini-high scores 24.94 on modified items, and the o-series framing overfit is documented. This is one of the few levers with literature predicting a stronger effect on Astra than on Fable.

---

## 5. Period caliber (cumulative vs discrete; stock vs flow)

**Definition.** A figure's caliber is mistaken: year-to-date cumulative read as the month's value, ending balance used where an average is meant, or an adjacent period's column fetched.

**Evidence**

- **FinIndices** (arXiv **2607.28661**). Uncropped financial statements up to 32K tokens with adversarial traps.
  - Caliber alignment on the table task without hints: Claude-4.5 12.79, Gemini-3.1 23.26, GPT-5.4 15.12.
  - Temporal + caliber without hints: Claude-4.5 37.50, Gemini-3.1 68.75, GPT-5.4 59.38.
  - Logged failures:
    - a model used the prior year's Q3 *YTD* profit as the baseline for a single-quarter growth rate (202.25% vs a true 58.49%);
    - ROA was computed on ending rather than average assets (1.208% vs 1.217%);
    - "incorrect adjacent columns" were fetched "under structural pressure".
  - The paper gives no per-trap error percentages.
- **Our data.** "Figures in thousands flagged by any cross-reference" is dead. A labelled caliber is likely dead too. This mechanism only has a chance when **no label flags it**.

**Transfer recipe**

- Files: a monthly pack. The warehouse system's "Receipts value by period" export is actually cumulative from 1 January, but its column header just says `Period`. Supplier invoices arrive monthly.
- Task: reconcile receipts to invoices per month.
- Anchors that prove the export is cumulative:
  - the January row equals January invoices to the cent;
  - each later row equals the running sum of invoices plus one documented discrepancy;
  - one month carries a credit note that makes the cumulative series dip by exactly that credit, which is impossible for a monthly series of positive receipts.
- Right answer: de-cumulate, giving one real variance.
- Default wrong answer: every month from February on shows a large, growing variance.

**How it differs from the dead levers.** No unit word, no "YTD" label and no cross-reference flag. Only arithmetic reveals the caliber.

**Validity risk.** "Maybe the export is wrong and the variances are real." Rule it out by making the cumulative reading reconcile *exactly*, so the monthly reading leaves unexplained variances that match the running sums.

**Rating.** Fable **medium**, Astra **medium**. **Caution:** a reconciliation deliverable *invites* the model to explain variances, so it may discover the pattern. The bite is likelier when the caliber feeds a downstream figure (a KPI, an accrual) than when it is the object of the reconciliation itself.

---

## 6. Abstain when the only available source does not govern

**Definition.** The files contain a source that looks applicable (the current tariff, a sister product's price, an unapproved draft), but it does not govern some items. The right entry is "not determinable from the files". The model fills in a value from the available source.

**Evidence**

- **AbstentionBench** (Kirichenko et al., arXiv **2506.09038**). 20 LLMs, including o1, s1.1 and R1-Distill-Llama-70B.
  - "Reasoning fine-tuning degrades abstention by 24% on average."
  - Underspecified context and false premises are "persistently challenging".
  - For s1, a larger reasoning budget did not improve abstention, or made it worse.
- **TIDE** (arXiv **2608.08512**). With gold context, rejecting a misleading version scores GPT-5.2 26.73 and Claude Sonnet 4.5 14.71, never above 27.62.
- **FinIndices** builds in an "information deficiency" trap: the model must answer "Insufficient information" when a needed prior report is omitted. The paper gives no per-trap number.
- **MiP-Overthinking** (Fan et al., arXiv **2504.06514**). Reasoning models do not quickly flag a missing premise; they produce much longer answers. The paper reports non-reasoning models flag ill-posed questions faster. Only qualitative claims were read.

**Transfer recipe**

- Files: the 2025 tariff (effective 1 Jan 2025) and a shipment log spanning December 2024 to February 2025. No 2024 tariff anywhere.
- Deliverable schema: every row has `status ∈ {priced, not_priceable}` with a reason code. This is declared neutrally for all rows, not hinted.
- Right answer: the December shipments are `not_priceable`.
- Default wrong answer: price them at the 2025 tariff, either from recency (#2) or from "use what is available".
- Variant: a price for the 500 ml SKU exists; none for the 750 ml. The default wrong answer interpolates or copies.

**How it differs from the dead levers.** The trap is not a hidden fact. The effective date is printed on the tariff. The failure is the reluctance to leave a field empty.

**Validity risk.** This lever carries the most validity risk of the eight. A null answer is only genuine if *no* route to a value exists. Run an executed search over every file for any 2024 price, and have a blind reader confirm. Avoid "close-enough" cases such as an unchanged item whose price plausibly carried over, unless a file says the price changed.

**Rating.** Fable **medium**, Astra **medium**. Both are careful readers, and a schema slot named `not_priceable` primes the check. Interlocking with #2 is what is likely to make it bite.

---

## 7. Iterated revision: belief inertia plus collateral damage

**Definition.** A rule is revised twice with different scopes, for example v2 raises a threshold for everyone and v3 restores it for one category. The model either keeps a retracted value (inertia) or over-extends the latest change to unaffected items (collateral damage).

**Evidence**

- **AGM-Bench** (Jenkins, ICLR 2026 Workshop on Logical Reasoning of LLMs). 2,400 scenarios, seven frontier LLMs including o3-mini and R1.
  - Models satisfy Success and Consistency, but "systematically violate Inclusion (minimal change) and Preservation".
  - Iterated revision shows belief inertia and collateral damage.
  - The reasoning models improve single-step revision "but degrade faster under iteration".
  - The workshop page gives no numbers.
- **Belief-R** (Wilie et al., arXiv **2406.19764**, EMNLP 2024). Models of 6B parameters or more score >75% on basic inference, but the revision score (BREU) "peaks at only around 50%". Models good at updating over-update when no update is warranted.
- **Self-Verification Dilemma** (Long et al., arXiv **2602.03485**). About 85–95% of rechecks in reasoning traces "merely confirm prior reasoning". Models tested: Qwen3-8B, QwQ-32B, gpt-oss-20b, R1-Distill-7B. A premise misapplied early survives the model's own re-check.
- **Our doctrine (CLAUDE.md).** A changed premise that silently invalidates an already-computed result is what the already-hard bundles share. **However**, the first direct test (governing-document conflict added to a-321) moved pass@1 only from 0.88 to 0.80 on one model.

**Transfer recipe**

- Files: an approval policy with three dated revisions.

  | Version | Change |
  |---|---|
  | v1 | second approval above €500 |
  | v2 (1 Mar) | €750 for all categories |
  | v3 (15 May) | back to €500 for "IT equipment" only |

- Also: a claims register spanning January to June, and last quarter's completed review as a precedent document.
- Points are lost two ways: inertia (IT claims after 15 May judged at €750) and collateral damage (non-IT claims after 15 May judged at €500).
- Interlock with #1: which claims are "IT equipment" is decided by the item description, not the cost-centre code.

**How it differs from the dead levers.** Each revision is stated, so on its own this is a stated rule (dead). What bites is a scope that is partial and stacked, scored in **both** directions. Include it only interlocked.

**Validity risk.** The scope wording of v3 must be exact (a category list, not "where appropriate"). The governing date per claim must be unique (claim date, not approval date). Say which, in the policy itself.

**Rating.** Fable **medium**, Astra **medium**. Literature support is moderate (workshop papers, older models). Our own first test was weak.

---

## 8. A formal-looking stale summary vs the primary instrument

**Definition.** A secondary but official-looking digest (a rate summary, a "price passport", a KPI definitions sheet) states a value that a later primary instrument amended. The model follows the digest.

**Evidence**

- **TIDE** (arXiv **2608.08512**). In "Context Misalignment", a misleading preamble states a wrong version and the verified clauses are supplied (ICL).
  - Strict accuracy: GPT-5.2 26.73, Claude Sonnet 4.5 14.71, never above 27.62.
  - With the correct clauses placed *above* the misleading text (RAG setting), accuracy stays at or below 25.09.
  - The paper says models "trust a confident false premise over the authoritative text".
  - Separately: models detect 78.9% of perturbed statements on average, but name the altered field correctly in only 18.6%.
- **CONFLICTS / "DRAGged into Conflicts"** (Cattan et al., arXiv **2506.08500**). Gemini 2.5 Flash Thinking scores 74.2 (vanilla) on the combined Freshness + Misinformation category. That is about 26% wrong even when outdated information is the conflict type.
- **Our data.** When an informal remark contradicts an official source, the models side with the official one. TIDE suggests that when *both* sources are formal, the confidently pre-digested one wins.

**Transfer recipe**

- Files:
  - a finance-team "Duty & surcharge summary 2025" in a formal template, dated 15 Jan;
  - the customs or carrier notice dated 1 March, effective 15 March, amending one line;
  - April shipments.
- Right answer: the amended rate for April.
- Default wrong answer: the summary's rate.

**How it differs from the dead levers.** The summary is not a decoy: it was the governing aid until 15 March and is used correctly for the earlier shipments. It is not an informal remark either.

**Validity risk.** "Which document governs" can be ambiguous.

**Anchor.** The amendment names the exact line and effective date. The summary's own header date precedes the amendment. Nothing indicates the summary was updated afterwards.

**Rating.** Fable **medium**, Astra **low–medium**. TIDE's misleading premise is closer to the query than to a file, so the transfer is uncertain. A governing-document conflict was our weakest measured lever (a-321).

---

## 9. Relative-time anchored to a document event (not "now")

**Definition.** A deadline or effective date is defined relative to a specific document's own date: "10 working days from the date of this notice", "3 months after commissioning". The model anchors on the wrong date, such as the forwarding email or the export date.

**Evidence**

- **TIDE** Relative-Time QA with gold context (anchor date plus offset; the target date is never stated): GPT-5.2 59.66, Claude Sonnet 4.5 68.03.
- **Test of Time** (Fatemi et al., arXiv **2406.09170**). Duration accuracy: GPT-4 16.00, Gemini 1.5 Pro 13.50, Claude-3-Sonnet 15.00. About 21% and 25% of wrong Duration answers (GPT-4, Gemini) were off by exactly one day. These are older non-reasoning models.

**Transfer recipe**

- Files: a supplier's termination notice dated 3 June, forwarded internally on 11 June; a holiday calendar for the supplier's country (non-English file); an SLA whose worked example fixes inclusive counting.
- Right answer: the deadline counted from 3 June in working days, excluding local holidays.
- Default wrong answer: counted from 11 June, or in calendar days, or from the host country's calendar.

**How it differs from the dead levers.** This is *not* the inferred-current-date trap, which Arena feedback flags as overused. The anchor is a named event's date, printed in the files.

**Validity risk.** Avoid "next Friday" style phrases. Use explicit offsets and supply the holiday list.

**Rating.** Fable **low–medium**, Astra **low–medium**. Python handles the arithmetic, so only the anchor choice bites. Reserve for interlocks.

---

## 10. Conditional or modal statements read as settled facts

**Evidence.** Basmov, Goldberg & Tsarfaty (arXiv **2404.06283**; ChatGPT, GPT-4, LLaMA 2, Mixtral). Models are "much more prone to error when dealing with modal and conditional contexts", and in them "often fail to separate the text from their internal knowledge". The abstract has no numbers, and there is no reasoning-model evidence.

**Recipe.** Minutes say "we would extend terms to 60 days if Q2 volume exceeds 10,000 units". The volume report shows 8,400, so terms stay at 30. The default wrong answer is 60.

**Validity.** Both the condition and its outcome must be in the files.

**Rating.** Low / low. Reasoning models evaluate a salient conditional. This is close to a stated rule.

## 11. The decisive fact sits in a non-English file

**Evidence.** MLNeedle (Hengle et al., arXiv **2408.10151**, NAACL 2025). Performance is lowest when the needle is in a language outside the English family and in the middle of the context. Only older and smaller models were tested.

**Rating.** Low / low. Fable and Astra read major languages fluently. Use non-English only as realistic texture for #2, #4 and #9, not as the lever.

---

## Interlocks (single levers are dead in our lab)

- **#2 + #6:** the newer tariff is present and the governing older one is absent, so the right entry is `not_priceable`. Recency pulls toward pricing, and abstention reluctance pushes the same way.
- **#1 + #2:** a mis-keyed acceptance email decides which price version an order falls under. The identity hop feeds the date hop.
- **#3 + #7:** the convention changes mid-period (an amended schedule's new worked example implies a different rounding or day count). Old items keep the old convention.
- **#4 + #1:** the switching fact (a goods-received note or credit note) refers to the item by its pre-migration code.
- Route **several graded checks** through each interlock (CLAUDE.md: pass@1 counts full success), and keep the affected population small.

---

## Looks promising, but the evidence says reasoning models now solve it (or a script does)

- **Irrelevant "NoOp" clauses (GSM-NoOp).** The 2024 drops were real (arXiv 2410.05229: o1-preview 94.9 → 77.4; GPT-4o 95.2 → 63.1). A 2026 re-audit (Sturb, LessWrong, 5 June 2026, not peer-reviewed) found audited NoOp drops of **0–2 pp** for Claude Opus 4.6, Haiku 4.5 and GPT-4o once ambiguous items were removed: only 117 of 945 distractors were truly irrelevant, κ = 0.32. Gema et al. show Opus 4 falling only from about 100% to 85–90% on Misleading Math. This is consistent with our "decoys dead".
- **Context vs parametric conflict (ClashEval, arXiv 2404.10198).** Prior bias, meaning a model keeps its own wrong belief when the context is right, is 0.021 for Claude Opus and GPT-4o and 0.037 for Gemini 1.5. Models follow the file. The exception is the entrenched "current law" default (#2).
- **Literal needle retrieval and lost-in-the-middle.** With a literal match, frontier models are near-perfect (NoLiMa base scores 98.8–99.9). Only the latent-association variant (#1) survives.
- **Two-hop curse (arXiv 2411.16353) and reversal curse (arXiv 2309.12288).** Both are parametric. Berglund et al.: "if 'A is B' appears in-context, models can deduce the reverse relationship." Our agents reason over facts in files.
- **Premise order (Chen et al., arXiv 2402.08939, ICML 2024).** A >30% drop for pre-reasoning models. I found no reasoning-model replication, and agents re-read and sort.
- **Long-context aggregation (Oolong, arXiv 2511.02817).** GPT-5, Claude Sonnet 4 and Gemini 2.5 Pro score below 50% at 128K. A replication reports a regex reaching about 100% when labels are present **[unverified, non-peer-reviewed]**. Breadth is dead in our lab, and a script grinds it out.
- **Proactive interference over update streams (PI-LLM, arXiv 2506.08184).** The decline is log-linear, and chain of thought does not help. But structured update logs are parsed by script, and top-tier models held relatively high accuracy at 400 updates.
- **Stated-rule application, including non-cumulative fees (RuleArena, arXiv 2412.08972).** o1-preview's airline accuracy is only 0.54 / 0.37 / 0.21 (zero-shot L1/L2/L3), and models add both overweight and oversize fees where only the higher applies. Our 650/650 says stated rules are dead for Fable and Astra.
- **Self-correction blind spot (arXiv 2507.02778).** The 64.5% rate is for 14 *non-reasoning* open models. The paper notes RL-trained models learn to correct. Keep only the design consequence: author the trap into the first reading (see #7).
- **Anchoring (arXiv 2505.15392).** The abstract says reasoning offers some mitigation. Per a search snippet **[unverified]**, 22–61% of questions were anchored and reasoning models were "relatively mild".
- **Hindsight neglect and other Inverse Scaling Prize tasks (arXiv 2306.09479).** GPT-4 reversed hindsight neglect. This is recalled from the GPT-4 technical report (arXiv 2303.08774) and was **not re-opened** in this survey.
- **Date arithmetic and time zones.** Test of Time shows weak Duration scores (13.5–16.0) for non-reasoning models. A script removes the arithmetic; only the *convention* or *anchor* survives (#3, #9).

## Searched, but found no reasoning-model evidence

- Implicit units and scale. Only older work exists (NUMCoT arXiv 2406.02864; DimEval arXiv 2312.17532), on GPT-4-era models.
- DD/MM vs MM/DD locale ambiguity.
- Subtotal rows causing double counting.
- Negation in reasoning models.
- Over-application of instruction hierarchy to legitimate in-file amendments (Wallace et al., arXiv 2404.13208, covers GPT-3.5 robustness only).
- Generics read as universal statements (arXiv 2508.13718; search snippet only: 28 LLMs, CoT often *degrades* strong models on defeasible reasoning **[unverified]**).

Our own measurements are the only evidence for per-pack and tax-inclusive pricing. Treat them as stronger than anything in this list.

## Model-family pattern worth exploiting

- **Claude-family:** the most extreme recency default (Opus 4.6: 0.014 on old-version law), the weakest at rejecting a confident wrong version (Sonnet 4.5: 14.71 in TIDE), and the most distractible under long reasoning (Gema et al.). Points Fable toward **#2, #8, #4**.
- **OpenAI o-series / GPT-5.x:** "overfit to problem framings" (Gema et al.), heavy recitation losses (RoR: o3-mini-high 24.94), and our rounding result. Points Astra toward **#3, #4**.
- Both families: **#1** (measured) and **#6**.

## Sources (opened on arXiv or the venue page unless marked "via search")

- Inverse Scaling in Test-Time Compute (Gema et al.): arXiv 2507.14417
- RoR-Bench (Yan et al.): arXiv 2504.00509
- MATH-Perturb (Huang et al.): arXiv 2502.06453
- Embers of autoregression in o1 (McCoy et al.): arXiv 2410.01792
- Reasoning or Reciting (Wu et al.): arXiv 2307.02477 (abstract only, no numbers used)
- TaxCalcBench (Column Tax): arXiv 2507.16126
- FinIndices (Tong et al.): arXiv 2607.28661
- When Do LLMs Apply the Wrong Law? (Huang et al.): arXiv 2608.14610
- TIDE, "Time Present and Time Past" (Sobhani et al.): arXiv 2608.08512
- Asking For An Old Friend (Prior et al.): arXiv 2605.23497 (abstract only)
- LexKairos: arXiv 2608.09106 (abstract only; no numbers used)
- Recency bias in LLM reranking (Fang et al.): arXiv 2509.11353
- AbstentionBench (Kirichenko et al.): arXiv 2506.09038
- MiP-Overthinking (Fan et al.): arXiv 2504.06514 (via search summary)
- NoLiMa (Modarressi et al.): arXiv 2502.05167
- ClashEval (Wu, Wu & Zou): arXiv 2404.10198
- FaithEval (Ming et al.): arXiv 2410.03727. Inconsistent-context accuracy is 0.944 for Claude 3.5 Sonnet and 0.932 for GPT-4o, so contradiction *detection* is not the weak point.
- CONFLICTS (Cattan et al.): arXiv 2506.08500
- AGM-Bench (Jenkins): ICLR 2026 workshop page iclr.cc/virtual/2026/10017503
- Belief-R (Wilie et al.): arXiv 2406.19764 (abstract via search)
- DeltaLogic (Dhanda): arXiv 2604.02733 (small models only)
- Self-Verification Dilemma (Long et al.): arXiv 2602.03485
- Self-Correction Bench (Tsui): arXiv 2507.02778
- GSM-Symbolic / GSM-NoOp (Mirzadeh et al.): arXiv 2410.05229
- Revisiting GSM-Symbolic (Sturb, LessWrong, 2026-06-05; not peer-reviewed)
- PI-LLM (Wang & Sun): arXiv 2506.08184
- RuleArena (Zhou et al.): arXiv 2412.08972
- Oolong (Bertsch et al.): arXiv 2511.02817 (abstract via search)
- Test of Time (Fatemi et al.): arXiv 2406.09170
- Hypothetical statements in reading comprehension (Basmov et al.): arXiv 2404.06283
- MLNeedle (Hengle et al.): arXiv 2408.10151 (via search summary)
- Two-hop latent reasoning (Balesni et al.): arXiv 2411.16353
- Reversal curse (Berglund et al.): arXiv 2309.12288
- Instruction hierarchy (Wallace et al.): arXiv 2404.13208
- Anchoring with synthetic data (Huang et al.): arXiv 2505.15392
- Premise order (Chen et al.): arXiv 2402.08939 (via search summary)
