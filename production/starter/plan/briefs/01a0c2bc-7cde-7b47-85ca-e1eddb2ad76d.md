# Trap plan: 01a0c2bc-7cde-7b47-85ca-e1eddb2ad76d

Domain: manufacturing returns and repair logistics
Projected free share: 0.37 (decisive weights 25, 21, 17 of 100; fillers <= 5 points each come out of the free share)

Author with `production/briefs/AUTHOR-BRIEF-B8.md`; mode details are in `production/traps/TRAP-LIBRARY.md`.
These are TARGETS: build each mode only where this seed's material supports it naturally; if one does not
fit, swap in another library mode of a different family and say why in the hand-back.

| role | mode | name | family | status | aimed at | weight | why |
|---|---|---|---|---|---|---|---|
| lead | T2 | Convention fixed only by worked figures in the governing document | convention_inference | promising | both | 25 | promising; pooled miss 16%; already planned 2x |
| decisive | T3 | Quantity basis cued only on or about the record (tax-inclusive, per pack) | quantity_basis | proven | both | 21 | proven; pooled miss 65%; already planned 4x |
| decisive | T12 | Line transposition settled by first-hand descriptions | record_reversal | proven | both | 17 | proven; pooled miss 62%; already planned 2x |

## authoring/traps.json skeleton (schema b8/premises/1)

```json
{
 "schema": "b8/premises/1",
 "premises": [
  {
   "id": "P1",
   "decisive": true,
   "template": "T2",
   "aimed_at": "both",
   "family": "<B6 premise family>",
   "mechanism": "<code>",
   "step": "01-task",
   "checks": [
    "<check id>"
   ],
   "resolving_quote": {
    "file": "<file>",
    "text": "<verbatim>"
   },
   "anchors": [
    {
     "file": "<other file>",
     "text": "<verbatim>"
    },
    {
     "file": "<third file>",
     "text": "<verbatim>"
    }
   ],
   "default_technique": "<the parser/sort/join that gives the wrong answer>",
   "interlocks_with": [],
   "misreading": "<the realistic wrong reading>",
   "target_q": 0.4,
   "grounded_in": "<session::msg>"
  },
  {
   "id": "P2",
   "decisive": true,
   "template": "T3",
   "aimed_at": "both",
   "family": "<B6 premise family>",
   "mechanism": "<code>",
   "step": "01-task",
   "checks": [
    "<check id>"
   ],
   "resolving_quote": {
    "file": "<file>",
    "text": "<verbatim>"
   },
   "anchors": [
    {
     "file": "<other file>",
     "text": "<verbatim>"
    },
    {
     "file": "<third file>",
     "text": "<verbatim>"
    }
   ],
   "default_technique": "<the parser/sort/join that gives the wrong answer>",
   "interlocks_with": [],
   "misreading": "<the realistic wrong reading>",
   "target_q": 0.4,
   "grounded_in": "<session::msg>"
  },
  {
   "id": "P3",
   "decisive": true,
   "template": "T12",
   "aimed_at": "both",
   "family": "<B6 premise family>",
   "mechanism": "<code>",
   "step": "01-task",
   "checks": [
    "<check id>"
   ],
   "resolving_quote": {
    "file": "<file>",
    "text": "<verbatim>"
   },
   "anchors": [
    {
     "file": "<other file>",
     "text": "<verbatim>"
    },
    {
     "file": "<third file>",
     "text": "<verbatim>"
    }
   ],
   "default_technique": "<the parser/sort/join that gives the wrong answer>",
   "interlocks_with": [],
   "misreading": "<the realistic wrong reading>",
   "target_q": 0.4,
   "grounded_in": "<session::msg>"
  }
 ],
 "coverage_checks": [],
 "leak_allow": []
}
```

## The modes

### T2: Convention fixed only by worked figures in the governing document

- **Status:** promising
- **Family:** convention_inference
- **Aimed at:** both
- **Clock trap:** no
- **Aliases:** CV.round, CV.method, convention from worked figures
- **Pooled misses:** Fable 439/2670 (16%), Astra 252/2065 (12%)
- **Loopholes:** L-default, L-absorb, L-shield

The governing text states what to compute but not how to round, count or bound it; only its worked figures (or a filed record of the same procedure) fix the convention: truncate vs half-up, which end of a range, whether the arrival day counts. The default applies the ordinary convention (round(), half-up, plain mean). This mode now covers every convention set by worked figures, as authors template it; rounding and truncation are its strongest sub-shape. Measured here (build_evidence.py, 2026-10-15): final 10x2 pooled Fable 185/970, Astra 129/950; all stages Fable 439/2670, Astra 252/2065 (AMBIGUOUS/DEFECT units excluded); without unaudited >=90% units, final Fable 137/920, Astra 114/900. Audited GENUINE in 10 task(s). Status promising: short of proven: no model with pooled final rate >= 0.2 at n >= 20; not dead (some model above 0.05 or n < 20).

**Recipe**

- *record:* the governing rule states the quantity and its precision but not the convention
- *anchors:* worked figures in the governing document itself, or in a same-procedure filed record the rule points to; for Astra exactly one discriminating figure outside the entry that defines the graded rate
- *withheld:* no sentence names the convention ('truncate', 'cut', 'count the arrival day')
- *dials:*
  - the number and placement of discriminating figures: one figure gave Astra about 100% in several builds; two gave anywhere from 3/15 to 14/15
  - a figure inside the entry that defines the graded rate kills it for Astra
  - keep non-discriminating figures (both conventions agree) as cover
- *conservation:* graded figures must discriminate under every upstream answer the solver could give (grade on the solver's own list)
- *shields:* the task's own other content must not act as a competing example set, or the audit must show it is not governing (deck titles)

**Proof obligations (authoring/validate.py)**

- discrimination: solve.py shows each plausible convention fails at least one worked figure, and exactly one fits all
- placement: every worked figure sits in the governing text or a same-module filed record (eco-guard 2.1.0 fix)
- additivity: the default convention fails exactly this premise's checks
- census: deliverables diffed against the reference to separate convention misses from cascades

**Hazards**

- worked figures in documents the rule does not govern make it AMBIGUOUS: eco-guard 2.1.0 P3 (sheets from another year and module), brightwater 1.3.0 P3 ('within' promises outside the site-promise rule)
- the idiom 'to one decimal place' reads as ordinary rounding: profile 2.1.0-2.4.0 P5 shipped GENUINE-soft
- one discriminating figure is GENUINE-soft at best: deck 2.8.0 P4, gst 1.7.0 P2
- a cascade from an upstream answer graded against the reference: gst 1.3.0 P2 DEFECT (convention missed 0/30 once fixed)
- a token nobody can settle (a spaced em dash counted or not as a word): moot 2.1.0 P10 AMBIGUOUS
- a competing example set inside the task (the deck's own v3 titles cited as precedent): deck 2.3.0 and 2.8.0 disclosures

**What killed it**

- a worked figure inside the entry that defines the graded rate: profile 2.5.0 P5 Astra 14/15 to 0/5, never recovered in 2.6-2.8
- figures one division away from the graded case: coloring spine 0/30 in every form
- a stated precedent clause: kibo 2.1.0 P4 (5/5 to 0/5)
- one figure for Fable: 18/200 misses in the 45-task pass

**Trace signals**

- the user corrects a rounding or a count the assistant computed
- a style guide or procedure with examples but no explicit rounding rule
- filed earlier reports that show the house convention

**Domains**

- financial reporting and board decks
- tax workbooks
- survey and lab results sheets
- service charters
- publishing specifications

**Example.** A house style gives figures over one million in millions with one decimal; its one discriminating worked example shows 2,480,000 as 2.4 million (half-up would give 2.5), so the graded figures must be cut, not rounded.

**Measured here**

| task | version | premise | stage | Fable missed | Astra missed | audit |
|---|---|---|---|---|---|---|
| a_f0_ats-embedded-screening-register | 1.1.0 | P1 | final | 0/10 | 0/10 |  |
| a_f0_ats-embedded-screening-register | 1.1.0 | P4 | final | 0/10 | 0/10 |  |
| a_f0_ats-embedded-screening-register | 1.5.0 | P1 | final | 0/10 | 0/10 |  |
| a_f0_ats-embedded-screening-register | 1.5.0 | P4 | final | 0/10 | 0/10 |  |
| a_f0_ats-embedded-screening-register | 1.7.0 | P1 | final | 0/10 | 0/10 |  |
| a_f0_ats-embedded-screening-register | 1.7.0 | P4 | final | 2/10 | 0/10 | GENUINE |
| a_f0_ats-embedded-screening-register | 1.7.1 | P1 | final | 0/10 | 0/10 |  |
| a_f0_ats-embedded-screening-register | 1.7.1 | P4 | final | 0/10 | 0/10 | GENUINE |
| a_f0_lassa-kap-results-sheet | 1.1.0 | P2 | final | 0/10 | 0/10 | BLIND-1.0 |
| a_f0_lassa-kap-results-sheet | 1.1.0 | P4 | final | 5/10 | 3/10 | BLIND-1.0 |
| a_f1_brightwater-spec-qa | 1.3.0 | P3 | final | 10/10 | 10/10 | AMBIGUOUS |
| a_f1_brightwater-spec-qa | 1.3.0 | P4 | final | 0/10 | 9/10 | GENUINE |
| a_f1_brightwater-spec-qa | 1.5.0 | P3 | final | 8/10 | 0/10 |  |
| a_f1_brightwater-spec-qa | 1.5.0 | P4 | final | 0/10 | 0/10 |  |
| a_f1_brightwater-spec-qa | 1.6.0 | P3 | final | 10/10 | 1/10 |  |
| a_f1_brightwater-spec-qa | 1.6.0 | P4 | final | 10/10 | 10/10 |  |
| a_f1_coloring-book-retitle-audit | 2.2.0 | P3 | final | 0/10 | 0/10 |  |
| a_f1_coloring-book-retitle-audit | 2.2.0 | P4 | final | 0/10 | 0/10 |  |
| a_f1_coloring-book-retitle-audit | 2.2.0 | P6 | final | 0/10 | 0/10 |  |
| a_f1_coloring-book-retitle-audit | 2.2.0 | P7 | final | 0/10 | 0/10 |  |
| a_f1_coloring-book-retitle-audit | 2.2.0 | P9 | final | 0/10 | 0/10 |  |
| a_f1_coloring-book-retitle-audit | 2.3.0 | P3 | final | 0/10 | 0/10 |  |
| a_f1_coloring-book-retitle-audit | 2.3.0 | P4 | final | 0/10 | 0/10 |  |
| a_f1_coloring-book-retitle-audit | 2.3.0 | P6 | final | 0/10 | 0/10 |  |
| a_f1_coloring-book-retitle-audit | 2.3.0 | P7 | final | 0/10 | 0/10 |  |
| a_f1_coloring-book-retitle-audit | 2.3.0 | P9 | final | 0/10 | 0/10 |  |
| a_f1_coloring-book-retitle-audit | 2.5.0 | P3 | final | 0/10 | 0/0 |  |
| a_f1_coloring-book-retitle-audit | 2.5.0 | P4 | final | 0/10 | 0/0 |  |
| a_f1_coloring-book-retitle-audit | 2.5.0 | P6 | final | 0/10 | 0/0 |  |
| a_f1_coloring-book-retitle-audit | 2.5.0 | P7 | final | 0/10 | 0/0 |  |
| a_f1_coloring-book-retitle-audit | 2.5.0 | P9 | final | 0/10 | 0/0 |  |
| a_f1_council-video-index | 1.2.0 | P4 | final | 0/10 | 0/10 |  |
| a_f1_council-video-index | 1.2.0 | P5 | final | 9/10 | 5/10 | AMBIGUOUS |
| a_f1_council-video-index | 1.4.0 | P4 | final | 0/10 | 0/10 |  |
| a_f1_council-video-index | 1.4.0 | P5 | final | 9/10 | 9/10 | GENUINE-soft |
| a_f1_gst-workbook-answer-key | 1.3.0 | P2 | final | 0/10 | 6/10 | DEFECT |
| a_f1_gst-workbook-answer-key | 1.4.0 | P2 | final | 0/10 | 0/10 |  |
| a_f1_gst-workbook-answer-key | 1.4.1 | P2 | final | 0/10 | 0/10 |  |
| a_f1_gst-workbook-answer-key | 1.7.0 | P2 | final | 0/10 | 8/10 | GENUINE |
| a_f1_home-bp-diary-summary | 2.2.0 | P2 | final | 0/10 | 0/10 |  |
| a_f1_home-bp-diary-summary | 2.2.0 | P4 | final | 3/10 | 0/10 | GENUINE |
| a_f1_home-bp-diary-summary | 2.2.1 | P2 | final | 0/10 | 0/10 |  |
| a_f1_home-bp-diary-summary | 2.2.1 | P4 | final | 2/10 | 0/10 | GENUINE |
| a_f1_home-bp-diary-summary | 2.9.0 | P2 | final | 10/10 | 4/10 | UNCONFIRMED |
| a_f1_home-bp-diary-summary | 2.9.0 | P4 | final | 2/10 | 4/10 |  |
| a_f1_home-bp-diary-summary | 2.12.0 | P2 | final | 9/10 | 0/10 | GENUINE |
| a_f1_home-bp-diary-summary | 2.12.0 | P4 | final | 3/10 | 1/10 | GENUINE |
| a_f1_home-bp-diary-summary | 2.12.1 | P2 | final | 7/10 | 0/10 | GENUINE |
| a_f1_home-bp-diary-summary | 2.12.1 | P4 | final | 2/10 | 2/10 | GENUINE |
| a_f1_kibo-budget-cap-review | 2.3.0 | P4 | final | 0/10 | 0/10 |  |
| a_f1_kibo-budget-cap-review | 2.3.1 | P4 | final | 0/10 | 0/10 |  |
| a_f1_kibo-budget-cap-review | 2.9.0 | P4 | final | 0/10 | 0/10 |  |
| a_f1_killzone-journal-review | 1.5.0 | P4 | final | 9/10 | 0/10 | UNCONFIRMED |
| a_f1_line-colour-census | 1.0.0 | P1 | final | 9/10 | 0/10 | BLIND-1.0 |
| a_f1_line-colour-census | 1.0.0 | P4 | final | 0/10 | 0/10 |  |
| a_f1_melody-lesson-results | 1.1.0 | P1 | final | 0/10 | 0/10 |  |
| a_f1_melody-lesson-results | 1.1.1 | P1 | final | 0/10 | 0/10 |  |
| a_f1_melody-lesson-results | 1.3.0 | P1 | final | 0/10 | 0/10 |  |
| a_f1_moisturiser-price-screen | 2.2.0 | P5 | final | 0/10 | 0/10 | BLIND-1.0 |
| a_f1_niche-shelving-screen | 1.1.0 | P4 | final | 0/10 | 0/10 |  |
| a_f1_probation-answer-key | 2.2.0 | P2 | final | 0/10 | 0/10 |  |
| a_f1_profile-copy-claims-audit | 2.1.0 | P3 | final | 0/10 | 0/10 |  |
| a_f1_profile-copy-claims-audit | 2.1.0 | P5 | final | 10/10 | 10/10 | GENUINE-soft |
| a_f1_profile-copy-claims-audit | 2.2.0 | P5 | final | 9/10 | 9/10 | GENUINE-soft |
| a_f1_profile-copy-claims-audit | 2.3.0 | P5 | final | 7/10 | 9/10 | GENUINE-soft |
| a_f1_profile-copy-claims-audit | 2.4.0 | P5 | final | 10/10 | 10/10 | GENUINE-soft |
| a_f1_psychopathy-evidence-screen | 2.3.0 | P3 | final | 2/10 | 4/10 | UNCONFIRMED |
| a_f1_psychopathy-evidence-screen | 2.3.0 | P5 | final | 0/10 | 0/10 | BLIND-1.0 |
| a_f1_psychopathy-evidence-screen | 2.4.0 | P3 | final | 2/10 | 3/10 | GENUINE-soft |
| a_f1_psychopathy-evidence-screen | 2.4.0 | P5 | final | 0/10 | 0/10 |  |
| a_f1_pupil-tracker-term-summary | 1.1.0 | P1 | final | 0/10 | 0/10 |  |
| a_f1_refurb-laptop-screen | 1.5.0 | P2 | final | 0/10 | 0/10 |  |
| a_f1_refurb-laptop-screen | 1.5.0 | P3 | final | 0/10 | 0/10 |  |
| a_f1_suitcase-cover-matrix-check | 2.1.0 | P2 | final | 5/10 | 0/10 | GENUINE |
| a_f1_suitcase-cover-matrix-check | 2.1.0 | P6 | final | 0/10 | 0/10 |  |
| a_f1_suitcase-cover-matrix-check | 2.1.1 | P2 | final | 3/10 | 0/10 | GENUINE |
| a_f1_suitcase-cover-matrix-check | 2.1.1 | P6 | final | 0/10 | 0/10 |  |
| a_f1_suitcase-cover-matrix-check | 2.6.0 | P2 | final | 5/10 | 0/10 | GENUINE |
| a_f1_suitcase-cover-matrix-check | 2.6.0 | P6 | final | 0/10 | 0/10 |  |
| a_f1_timesheet-overtime-review | 2.2.0 | P3 | final | 0/10 | 0/10 |  |
| a_f1_timesheet-overtime-review | 2.4.0 | P3 | final | 0/10 | 0/0 |  |
| a_f1_timesheet-overtime-review | 2.7.0 | P3 | final | 0/10 | 0/10 |  |
| a_f2_cafe-kitchen-schedule-revisions | 2.1.0 | P2 | final | 0/10 | 0/10 |  |
| a_f2_cafe-kitchen-schedule-revisions | 2.1.0 | P3 | final | 0/10 | 0/10 |  |
| a_f2_cafe-kitchen-schedule-revisions | 2.1.0 | P5 | final | 0/10 | 0/10 |  |
| a_f2_cafe-kitchen-schedule-revisions | 2.1.0 | P7 | final | 0/10 | 0/10 |  |
| a_f2_cafe-kitchen-schedule-revisions | 2.1.1 | P2 | final | 0/10 | 0/10 |  |
| a_f2_cafe-kitchen-schedule-revisions | 2.1.1 | P3 | final | 0/10 | 0/10 |  |
| a_f2_cafe-kitchen-schedule-revisions | 2.1.1 | P5 | final | 0/10 | 0/10 |  |
| a_f2_cafe-kitchen-schedule-revisions | 2.1.1 | P7 | final | 0/10 | 0/10 |  |
| a_f2_cafe-kitchen-schedule-revisions | 2.3.0 | P2 | final | 0/10 | 0/10 |  |
| a_f2_cafe-kitchen-schedule-revisions | 2.3.0 | P3 | final | 0/10 | 0/10 |  |
| a_f2_cafe-kitchen-schedule-revisions | 2.3.0 | P5 | final | 2/10 | 0/10 | GENUINE |
| a_f2_cafe-kitchen-schedule-revisions | 2.3.0 | P7 | final | 0/10 | 0/10 |  |
| a_f2_cafe-kitchen-schedule-revisions | 2.4.0 | P2 | final | 0/0 | 0/10 |  |
| a_f2_cafe-kitchen-schedule-revisions | 2.4.0 | P3 | final | 0/0 | 0/10 |  |
| a_f2_cafe-kitchen-schedule-revisions | 2.4.0 | P5 | final | 0/0 | 0/10 |  |
| a_f2_cafe-kitchen-schedule-revisions | 2.4.0 | P7 | final | 0/0 | 0/10 |  |
| a_f2_deck-preread-review | 2.2.0 | P4 | final | 8/10 | 10/10 | GENUINE |
| a_f2_deck-preread-review | 2.3.0 | P4 | final | 7/10 | 10/10 | GENUINE |
| a_f2_deck-preread-review | 2.5.0 | P4 | final | 2/10 | 3/10 |  |
| a_f2_deck-preread-review | 2.8.0 | P4 | final | 10/10 | 10/10 | GENUINE-soft |
| a_f2_pathway-choice-audit | 2.6.0 | P6 | final | 1/10 | 0/10 | BLIND-1.0 |
| a_f2_pathway-choice-audit | 2.7.0 | P6 | final | 2/10 | 0/10 |  |
| a_f0_ats-embedded-screening-register | 1.0.0 | P1 | pilot | 0/5 | 0/0 |  |
| a_f0_ats-embedded-screening-register | 1.1.0 | P1 | pilot | 0/5 | 0/5 |  |
| a_f0_ats-embedded-screening-register | 1.1.0 | P4 | pilot | 0/5 | 0/5 |  |
| a_f0_ats-embedded-screening-register | 1.2.0 | P1 | pilot | 0/5 | 0/0 |  |
| a_f0_ats-embedded-screening-register | 1.2.0 | P4 | pilot | 0/5 | 0/0 |  |
| a_f0_ats-embedded-screening-register | 1.3.0 | P1 | pilot | 0/5 | 0/0 |  |
| a_f0_ats-embedded-screening-register | 1.3.0 | P4 | pilot | 1/5 | 0/0 |  |
| a_f0_ats-embedded-screening-register | 1.4.0 | P1 | pilot | 0/5 | 0/5 |  |
| a_f0_ats-embedded-screening-register | 1.4.0 | P4 | pilot | 0/5 | 0/5 |  |
| a_f0_ats-embedded-screening-register | 1.5.0 | P1 | pilot | 0/5 | 0/5 |  |
| a_f0_ats-embedded-screening-register | 1.5.0 | P4 | pilot | 1/5 | 0/5 |  |
| a_f0_ats-embedded-screening-register | 1.6.0 | P1 | pilot | 0/5 | 0/5 |  |
| a_f0_ats-embedded-screening-register | 1.6.0 | P4 | pilot | 0/5 | 0/5 |  |
| a_f0_ats-embedded-screening-register | 1.7.0 | P1 | pilot | 0/5 | 0/5 |  |
| a_f0_ats-embedded-screening-register | 1.7.0 | P4 | pilot | 0/5 | 0/5 | GENUINE |
| a_f0_ats-embedded-screening-register | 1.7.1 | P1 | pilot | 0/5 | 0/5 |  |
| a_f0_ats-embedded-screening-register | 1.7.1 | P4 | pilot | 0/5 | 0/5 | GENUINE |
| a_f0_coop-bp-prefill-sheet | 1.0.0 | P2 | pilot | 0/5 | 0/0 |  |
| a_f0_coop-bp-prefill-sheet | 1.0.0 | P3 | pilot | 0/5 | 0/0 |  |
| a_f0_coop-bp-prefill-sheet | 1.1.0 | P2 | pilot | 0/5 | 0/5 |  |
| a_f0_coop-bp-prefill-sheet | 1.1.0 | P3 | pilot | 0/5 | 1/5 |  |
| a_f0_earth-guide-answer-claims | 1.0.0 | P2 | pilot | 0/5 | 0/0 |  |
| a_f0_earth-guide-answer-claims | 1.0.0 | P3 | pilot | 0/5 | 0/0 |  |
| a_f0_earth-guide-answer-claims | 1.1.0 | P2 | pilot | 0/5 | 0/5 |  |
| a_f0_earth-guide-answer-claims | 1.1.0 | P3 | pilot | 0/5 | 0/5 |  |
| a_f0_insurance-secrecy-register | 1.0.0 | P2 | pilot | 0/5 | 0/0 |  |
| a_f0_insurance-secrecy-register | 1.0.0 | P5 | pilot | 0/5 | 0/0 |  |
| a_f0_insurance-secrecy-register | 1.1.0 | P3 | pilot | 0/5 | 0/0 |  |
| a_f0_insurance-secrecy-register | 1.1.0 | P5 | pilot | 0/5 | 0/0 |  |
| a_f0_insurance-secrecy-register | 1.2.0 | P5 | pilot | 0/5 | 0/5 |  |
| a_f0_lassa-kap-results-sheet | 1.0.0 | P2 | pilot | 0/5 | 0/0 |  |
| a_f0_lassa-kap-results-sheet | 1.0.0 | P4 | pilot | 2/5 | 0/0 |  |
| a_f0_lassa-kap-results-sheet | 1.1.0 | P2 | pilot | 0/5 | 0/5 | BLIND-1.0 |
| a_f0_lassa-kap-results-sheet | 1.1.0 | P4 | pilot | 3/5 | 3/5 | BLIND-1.0 |
| a_f0_lassa-kap-results-sheet | 1.2.0 | P4 | pilot | 2/5 | 0/5 |  |
| a_f0_lassa-kap-results-sheet | 1.2.0 | P5 | pilot | 0/5 | 0/5 |  |
| a_f0_manhole-excavation-valuation | 1.0.0 | P3 | pilot | 0/5 | 0/0 |  |
| a_f0_manhole-excavation-valuation | 1.1.0 | P3 | pilot | 0/5 | 0/0 |  |
| a_f0_manhole-excavation-valuation | 1.2.0 | P3 | pilot | 0/5 | 0/5 |  |
| a_f0_manhole-excavation-valuation | 1.2.0 | P5 | pilot | 0/5 | 0/5 |  |
| a_f0_posting-month-close | 1.0.0 | P2 | pilot | 0/5 | 0/0 |  |
| a_f0_posting-month-close | 1.1.0 | P2 | pilot | 0/5 | 0/0 |  |
| a_f0_posting-month-close | 1.2.0 | P2 | pilot | 0/5 | 0/5 |  |
| a_f0_posting-month-close | 1.2.0 | P3 | pilot | 0/5 | 0/5 |  |
| a_f1_blockprint-winter-close | 1.0.0 | P4 | pilot | 0/5 | 0/0 |  |
| a_f1_blockprint-winter-close | 1.1.0 | P3 | pilot | 0/5 | 0/0 |  |
| a_f1_blockprint-winter-close | 1.2.0 | P3 | pilot | 0/5 | 0/5 |  |
| a_f1_brightwater-spec-qa | 1.2.0 | P3 | pilot | 0/5 | 0/0 |  |
| a_f1_brightwater-spec-qa | 1.2.0 | P4 | pilot | 1/5 | 0/0 |  |
| a_f1_brightwater-spec-qa | 1.3.0 | P3 | pilot | 5/5 | 5/5 | AMBIGUOUS |
| a_f1_brightwater-spec-qa | 1.3.0 | P4 | pilot | 1/5 | 4/5 | GENUINE |
| a_f1_brightwater-spec-qa | 1.4.0 | P3 | pilot | 5/5 | 0/5 |  |
| a_f1_brightwater-spec-qa | 1.4.0 | P4 | pilot | 0/5 | 0/5 |  |
| a_f1_brightwater-spec-qa | 1.5.0 | P3 | pilot | 3/5 | 0/5 |  |
| a_f1_brightwater-spec-qa | 1.5.0 | P4 | pilot | 0/5 | 0/5 |  |
| a_f1_brightwater-spec-qa | 1.6.0 | P3 | pilot | 5/5 | 0/5 |  |
| a_f1_brightwater-spec-qa | 1.6.0 | P4 | pilot | 5/5 | 5/5 |  |
| a_f1_coloring-book-retitle-audit | 2.0.0 | P6 | pilot | 0/5 | 0/0 |  |
| a_f1_coloring-book-retitle-audit | 2.1.0 | P3 | pilot | 0/5 | 0/0 |  |
| a_f1_coloring-book-retitle-audit | 2.1.0 | P4 | pilot | 0/5 | 0/0 |  |
| a_f1_coloring-book-retitle-audit | 2.1.0 | P6 | pilot | 0/5 | 0/0 |  |
| a_f1_coloring-book-retitle-audit | 2.1.0 | P7 | pilot | 0/5 | 0/0 |  |
| a_f1_coloring-book-retitle-audit | 2.2.0 | P3 | pilot | 0/5 | 0/5 |  |
| a_f1_coloring-book-retitle-audit | 2.2.0 | P4 | pilot | 0/5 | 0/5 |  |
| a_f1_coloring-book-retitle-audit | 2.2.0 | P6 | pilot | 0/5 | 0/5 |  |
| a_f1_coloring-book-retitle-audit | 2.2.0 | P7 | pilot | 0/5 | 0/5 |  |
| a_f1_coloring-book-retitle-audit | 2.2.0 | P9 | pilot | 0/5 | 0/5 |  |
| a_f1_coloring-book-retitle-audit | 2.3.0 | P3 | pilot | 0/5 | 0/5 |  |
| a_f1_coloring-book-retitle-audit | 2.3.0 | P4 | pilot | 0/5 | 0/5 |  |
| a_f1_coloring-book-retitle-audit | 2.3.0 | P6 | pilot | 0/5 | 0/5 |  |
| a_f1_coloring-book-retitle-audit | 2.3.0 | P7 | pilot | 0/5 | 0/5 |  |
| a_f1_coloring-book-retitle-audit | 2.3.0 | P9 | pilot | 0/5 | 0/5 |  |
| a_f1_coloring-book-retitle-audit | 2.4.0 | P3 | pilot | 0/5 | 0/0 |  |
| a_f1_coloring-book-retitle-audit | 2.4.0 | P4 | pilot | 0/5 | 0/0 |  |
| a_f1_coloring-book-retitle-audit | 2.4.0 | P6 | pilot | 0/5 | 0/0 |  |
| a_f1_coloring-book-retitle-audit | 2.4.0 | P7 | pilot | 0/5 | 0/0 |  |
| a_f1_coloring-book-retitle-audit | 2.4.0 | P9 | pilot | 0/5 | 0/0 |  |
| a_f1_coloring-book-retitle-audit | 2.5.0 | P3 | pilot | 0/5 | 0/0 |  |
| a_f1_coloring-book-retitle-audit | 2.5.0 | P4 | pilot | 0/5 | 0/0 |  |
| a_f1_coloring-book-retitle-audit | 2.5.0 | P6 | pilot | 0/5 | 0/0 |  |
| a_f1_coloring-book-retitle-audit | 2.5.0 | P7 | pilot | 0/5 | 0/0 |  |
| a_f1_coloring-book-retitle-audit | 2.5.0 | P9 | pilot | 0/5 | 0/0 |  |
| a_f1_coloring-book-retitle-audit | 2.6.0 | P3 | pilot | 0/5 | 5/5 |  |
| a_f1_coloring-book-retitle-audit | 2.6.0 | P4 | pilot | 0/5 | 0/5 |  |
| a_f1_coloring-book-retitle-audit | 2.6.0 | P6 | pilot | 0/5 | 1/5 |  |
| a_f1_coloring-book-retitle-audit | 2.6.0 | P7 | pilot | 0/5 | 0/5 |  |
| a_f1_coloring-book-retitle-audit | 2.6.0 | P9 | pilot | 0/5 | 0/5 |  |
| a_f1_council-video-index | 1.0.0 | P5 | pilot | 2/5 | 0/0 |  |
| a_f1_council-video-index | 1.1.0 | P4 | pilot | 0/5 | 0/0 |  |
| a_f1_council-video-index | 1.1.0 | P5 | pilot | 5/5 | 0/0 | AMBIGUOUS |
| a_f1_council-video-index | 1.2.0 | P4 | pilot | 0/5 | 0/5 |  |
| a_f1_council-video-index | 1.2.0 | P5 | pilot | 5/5 | 3/5 | AMBIGUOUS |
| a_f1_council-video-index | 1.3.0 | P2 | pilot | 0/5 | 0/5 |  |
| a_f1_council-video-index | 1.3.0 | P4 | pilot | 0/5 | 0/5 |  |
| a_f1_council-video-index | 1.3.0 | P5 | pilot | 5/5 | 3/5 |  |
| a_f1_council-video-index | 1.4.0 | P4 | pilot | 0/5 | 0/5 |  |
| a_f1_council-video-index | 1.4.0 | P5 | pilot | 5/5 | 4/5 | GENUINE-soft |
| a_f1_council-video-index | 1.5.0 | P4 | pilot | 0/5 | 0/5 |  |
| a_f1_council-video-index | 1.5.0 | P5 | pilot | 5/5 | 5/5 |  |
| a_f1_current-affairs-booklet-plan | 1.1.0 | P1 | pilot | 1/5 | 0/0 |  |
| a_f1_current-affairs-booklet-plan | 1.2.0 | P1 | pilot | 0/5 | 0/5 |  |
| a_f1_current-affairs-booklet-plan | 1.2.0 | P4 | pilot | 0/5 | 0/5 |  |
| a_f1_ethics-report-mark-release | 1.0.0 | P2 | pilot | 0/5 | 0/0 |  |
| a_f1_ethics-report-mark-release | 1.1.0 | P2 | pilot | 0/5 | 0/5 |  |
| a_f1_ethics-report-mark-release | 1.1.0 | P4 | pilot | 0/5 | 0/5 |  |
| a_f1_feast-sharing-runsheet | 1.0.0 | P4 | pilot | 0/5 | 0/0 |  |
| a_f1_feast-sharing-runsheet | 1.0.0 | P5 | pilot | 0/5 | 0/0 |  |
| a_f1_feast-sharing-runsheet | 1.1.0 | P4 | pilot | 4/5 | 0/0 | AMBIGUOUS |
| a_f1_feast-sharing-runsheet | 1.1.0 | P5 | pilot | 4/5 | 0/0 | AMBIGUOUS |
| a_f1_gst-workbook-answer-key | 1.0.0 | P2 | pilot | 0/5 | 0/0 |  |
| a_f1_gst-workbook-answer-key | 1.1.0 | P2 | pilot | 0/5 | 0/0 |  |
| a_f1_gst-workbook-answer-key | 1.2.0 | P2 | pilot | 0/5 | 1/5 |  |
| a_f1_gst-workbook-answer-key | 1.3.0 | P2 | pilot | 0/5 | 4/5 | DEFECT |
| a_f1_gst-workbook-answer-key | 1.4.0 | P2 | pilot | 0/5 | 0/5 |  |
| a_f1_gst-workbook-answer-key | 1.4.1 | P2 | pilot | 0/5 | 0/5 |  |
| a_f1_gst-workbook-answer-key | 1.5.0 | P2 | pilot | 0/5 | 2/5 |  |
| a_f1_gst-workbook-answer-key | 1.6.0 | P2 | pilot | 0/5 | 3/5 |  |
| a_f1_gst-workbook-answer-key | 1.7.0 | P2 | pilot | 0/5 | 2/5 | GENUINE |
| a_f1_home-bp-diary-summary | 2.0.0 | P2 | pilot | 0/5 | 0/0 |  |
| a_f1_home-bp-diary-summary | 2.1.0 | P2 | pilot | 0/5 | 0/0 |  |
| a_f1_home-bp-diary-summary | 2.1.0 | P4 | pilot | 0/5 | 0/0 |  |
| a_f1_home-bp-diary-summary | 2.2.0 | P2 | pilot | 0/5 | 0/5 |  |
| a_f1_home-bp-diary-summary | 2.2.0 | P4 | pilot | 1/5 | 0/5 | GENUINE |
| a_f1_home-bp-diary-summary | 2.2.1 | P2 | pilot | 0/5 | 0/5 |  |
| a_f1_home-bp-diary-summary | 2.2.1 | P4 | pilot | 1/5 | 0/5 | GENUINE |
| a_f1_home-bp-diary-summary | 2.3.0 | P2 | pilot | 0/5 | 0/5 |  |
| a_f1_home-bp-diary-summary | 2.3.0 | P4 | pilot | 2/5 | 0/5 |  |
| a_f1_home-bp-diary-summary | 2.4.0 | P2 | pilot | 0/5 | 0/0 |  |
| a_f1_home-bp-diary-summary | 2.4.0 | P4 | pilot | 0/5 | 0/0 |  |
| a_f1_home-bp-diary-summary | 2.5.0 | P2 | pilot | 0/5 | 0/0 |  |
| a_f1_home-bp-diary-summary | 2.5.0 | P4 | pilot | 0/5 | 0/0 |  |
| a_f1_home-bp-diary-summary | 2.6.0 | P2 | pilot | 0/5 | 0/0 |  |
| a_f1_home-bp-diary-summary | 2.6.0 | P4 | pilot | 1/5 | 0/0 |  |
| a_f1_home-bp-diary-summary | 2.7.0 | P2 | pilot | 0/5 | 0/5 |  |
| a_f1_home-bp-diary-summary | 2.7.0 | P4 | pilot | 1/5 | 1/5 |  |
| a_f1_home-bp-diary-summary | 2.8.0 | P2 | pilot | 5/5 | 5/5 | UNCONFIRMED |
| a_f1_home-bp-diary-summary | 2.8.0 | P4 | pilot | 1/5 | 3/5 |  |
| a_f1_home-bp-diary-summary | 2.9.0 | P2 | pilot | 4/5 | 3/5 | UNCONFIRMED |
| a_f1_home-bp-diary-summary | 2.9.0 | P4 | pilot | 1/5 | 2/5 |  |
| a_f1_home-bp-diary-summary | 2.10.0 | P2 | pilot | 2/5 | 0/5 | BLIND-1.0 |
| a_f1_home-bp-diary-summary | 2.10.0 | P4 | pilot | 0/5 | 1/5 |  |
| a_f1_home-bp-diary-summary | 2.11.0 | P2 | pilot | 4/5 | 0/5 |  |
| a_f1_home-bp-diary-summary | 2.11.0 | P4 | pilot | 0/5 | 3/5 |  |
| a_f1_home-bp-diary-summary | 2.12.0 | P2 | pilot | 4/5 | 0/5 | GENUINE |
| a_f1_home-bp-diary-summary | 2.12.0 | P4 | pilot | 2/5 | 3/5 | GENUINE |
| a_f1_home-bp-diary-summary | 2.12.1 | P2 | pilot | 3/5 | 1/5 | GENUINE |
| a_f1_home-bp-diary-summary | 2.12.1 | P4 | pilot | 2/5 | 2/5 | GENUINE |
| a_f1_kibo-budget-cap-review | 2.0.0 | P4 | pilot | 5/5 | 0/0 | GENUINE-soft |
| a_f1_kibo-budget-cap-review | 2.1.0 | P4 | pilot | 0/5 | 0/0 |  |
| a_f1_kibo-budget-cap-review | 2.2.0 | P4 | pilot | 0/5 | 0/0 |  |
| a_f1_kibo-budget-cap-review | 2.3.0 | P4 | pilot | 0/5 | 0/5 |  |
| a_f1_kibo-budget-cap-review | 2.3.1 | P4 | pilot | 0/5 | 0/5 |  |
| a_f1_kibo-budget-cap-review | 2.4.0 | P4 | pilot | 0/5 | 0/5 |  |
| a_f1_kibo-budget-cap-review | 2.5.0 | P4 | pilot | 1/5 | 0/0 |  |
| a_f1_kibo-budget-cap-review | 2.6.0 | P4 | pilot | 1/5 | 0/0 |  |
| a_f1_kibo-budget-cap-review | 2.7.0 | P4 | pilot | 0/5 | 0/5 |  |
| a_f1_kibo-budget-cap-review | 2.8.0 | P4 | pilot | 0/5 | 0/5 |  |
| a_f1_kibo-budget-cap-review | 2.9.0 | P4 | pilot | 0/5 | 0/5 |  |
| a_f1_kibo-budget-cap-review | 2.10.0 | P4 | pilot | 0/5 | 0/5 |  |
| a_f1_kibo-budget-cap-review | 2.11.0 | P4 | pilot | 0/5 | 0/5 |  |
| a_f1_killzone-journal-review | 1.0.0 | P3 | pilot | 0/5 | 0/0 |  |
| a_f1_killzone-journal-review | 1.1.0 | P4 | pilot | 0/5 | 0/5 |  |
| a_f1_killzone-journal-review | 1.2.0 | P4 | pilot | 5/5 | 0/5 |  |
| a_f1_killzone-journal-review | 1.3.0 | P4 | pilot | 5/5 | 0/5 |  |
| a_f1_killzone-journal-review | 1.4.0 | P4 | pilot | 5/5 | 0/5 |  |
| a_f1_killzone-journal-review | 1.5.0 | P4 | pilot | 5/5 | 0/5 | UNCONFIRMED |
| a_f1_line-colour-census | 1.0.0 | P1 | pilot | 5/5 | 1/5 | BLIND-1.0 |
| a_f1_line-colour-census | 1.0.0 | P4 | pilot | 0/5 | 0/5 |  |
| a_f1_line-colour-census | 1.2.0 | P1 | pilot | 5/5 | 0/5 |  |
| a_f1_line-colour-census | 1.2.0 | P4 | pilot | 0/5 | 0/5 |  |
| a_f1_line-colour-census | 1.3.0 | P1 | pilot | 5/5 | 1/5 |  |
| a_f1_line-colour-census | 1.3.0 | P4 | pilot | 0/5 | 0/5 |  |
| a_f1_line-colour-census | 1.4.0 | P1 | pilot | 5/5 | 1/5 |  |
| a_f1_line-colour-census | 1.4.0 | P4 | pilot | 0/5 | 0/5 |  |
| a_f1_line-colour-census | 1.5.0 | P1 | pilot | 5/5 | 0/5 |  |
| a_f1_line-colour-census | 1.5.0 | P4 | pilot | 0/5 | 0/5 |  |
| a_f1_line-reference-belegliste | 1.0.0 | P1 | pilot | 0/5 | 0/0 |  |
| a_f1_line-reference-belegliste | 1.1.0 | P1 | pilot | 0/5 | 0/0 |  |
| a_f1_line-reference-belegliste | 1.1.0 | P4 | pilot | 0/5 | 0/0 |  |
| a_f1_line-reference-belegliste | 1.2.0 | P1 | pilot | 0/5 | 0/5 |  |
| a_f1_line-reference-belegliste | 1.2.0 | P4 | pilot | 0/5 | 0/5 |  |
| a_f1_melody-lesson-results | 1.0.0 | P1 | pilot | 0/5 | 0/5 |  |
| a_f1_melody-lesson-results | 1.1.0 | P1 | pilot | 0/5 | 0/5 |  |
| a_f1_melody-lesson-results | 1.1.1 | P1 | pilot | 0/5 | 0/5 |  |
| a_f1_melody-lesson-results | 1.2.0 | P1 | pilot | 0/5 | 0/5 |  |
| a_f1_melody-lesson-results | 1.3.0 | P1 | pilot | 0/5 | 0/5 |  |
| a_f1_moisturiser-price-screen | 2.0.0 | P5 | pilot | 0/5 | 0/0 |  |
| a_f1_moisturiser-price-screen | 2.1.0 | P5 | pilot | 0/5 | 0/0 |  |
| a_f1_moisturiser-price-screen | 2.2.0 | P5 | pilot | 0/5 | 0/5 | BLIND-1.0 |
| a_f1_moisturiser-price-screen | 2.3.0 | P7 | pilot | 0/5 | 0/5 |  |
| a_f1_mustangs-tryout-roster | 2.0.0 | P5 | pilot | 0/5 | 0/0 |  |
| a_f1_mustangs-tryout-roster | 2.0.0 | P8 | pilot | 0/5 | 0/0 |  |
| a_f1_mustangs-tryout-roster | 2.1.0 | P5 | pilot | 0/5 | 0/5 |  |
| a_f1_mustangs-tryout-roster | 2.1.0 | P8 | pilot | 0/5 | 0/5 |  |
| a_f1_mustangs-tryout-roster | 2.2.0 | P8 | pilot | 0/5 | 0/5 |  |
| a_f1_mustangs-tryout-roster | 2.2.0 | P12 | pilot | 0/5 | 0/5 |  |
| a_f1_mustangs-tryout-roster | 2.2.0 | P13 | pilot | 0/5 | 0/5 |  |
| a_f1_mustangs-tryout-roster | 2.2.0 | P14 | pilot | 0/5 | 0/5 |  |
| a_f1_niche-shelving-screen | 1.1.0 | P4 | pilot | 0/5 | 0/5 |  |
| a_f1_niche-shelving-screen | 1.3.0 | P4 | pilot | 0/5 | 0/5 |  |
| a_f1_probation-answer-key | 2.1.0 | P2 | pilot | 0/5 | 0/0 |  |
| a_f1_probation-answer-key | 2.2.0 | P2 | pilot | 0/5 | 0/5 |  |
| a_f1_probation-answer-key | 2.3.0 | P5 | pilot | 0/5 | 0/5 |  |
| a_f1_probation-answer-key | 2.4.0 | P5 | pilot | 0/5 | 0/5 |  |
| a_f1_probation-answer-key | 2.5.0 | P2 | pilot | 0/5 | 0/5 |  |
| a_f1_profile-copy-claims-audit | 2.0.0 | P3 | pilot | 0/5 | 0/0 |  |
| a_f1_profile-copy-claims-audit | 2.1.0 | P3 | pilot | 0/5 | 0/5 |  |
| a_f1_profile-copy-claims-audit | 2.1.0 | P5 | pilot | 4/5 | 5/5 | GENUINE-soft |
| a_f1_profile-copy-claims-audit | 2.2.0 | P5 | pilot | 5/5 | 5/5 | GENUINE-soft |
| a_f1_profile-copy-claims-audit | 2.3.0 | P5 | pilot | 5/5 | 3/5 | GENUINE-soft |
| a_f1_profile-copy-claims-audit | 2.4.0 | P5 | pilot | 4/5 | 4/5 | GENUINE-soft |
| a_f1_profile-copy-claims-audit | 2.5.0 | P5 | pilot | 1/5 | 0/5 |  |
| a_f1_profile-copy-claims-audit | 2.6.0 | P5 | pilot | 4/5 | 0/5 | BLIND-1.0 |
| a_f1_profile-copy-claims-audit | 2.7.0 | P5 | pilot | 4/5 | 0/5 |  |
| a_f1_profile-copy-claims-audit | 2.8.0 | P5 | pilot | 1/5 | 0/5 |  |
| a_f1_psychopathy-evidence-screen | 2.1.0 | P3 | pilot | 0/5 | 0/0 |  |
| a_f1_psychopathy-evidence-screen | 2.2.0 | P3 | pilot | 0/5 | 0/0 |  |
| a_f1_psychopathy-evidence-screen | 2.3.0 | P3 | pilot | 1/5 | 3/5 | UNCONFIRMED |
| a_f1_psychopathy-evidence-screen | 2.3.0 | P5 | pilot | 0/5 | 0/5 | BLIND-1.0 |
| a_f1_psychopathy-evidence-screen | 2.4.0 | P3 | pilot | 3/5 | 1/5 | GENUINE-soft |
| a_f1_psychopathy-evidence-screen | 2.4.0 | P5 | pilot | 0/5 | 0/5 |  |
| a_f1_pupil-tracker-term-summary | 1.0.0 | P1 | pilot | 0/5 | 0/0 |  |
| a_f1_pupil-tracker-term-summary | 1.0.0 | P5 | pilot | 0/5 | 0/0 |  |
| a_f1_pupil-tracker-term-summary | 1.1.0 | P1 | pilot | 0/5 | 0/5 |  |
| a_f1_pupil-tracker-term-summary | 1.2.0 | P5 | pilot | 2/5 | 0/5 |  |
| a_f1_pupil-tracker-term-summary | 1.3.0 | P5 | pilot | 1/5 | 0/5 |  |
| a_f1_pupil-tracker-term-summary | 1.4.0 | P5 | pilot | 0/5 | 0/5 |  |
| a_f1_refurb-laptop-screen | 1.1.0 | P2 | pilot | 0/5 | 0/0 |  |
| a_f1_refurb-laptop-screen | 1.2.0 | P2 | pilot | 0/5 | 0/0 |  |
| a_f1_refurb-laptop-screen | 1.2.0 | P3 | pilot | 0/5 | 0/0 |  |
| a_f1_refurb-laptop-screen | 1.3.0 | P2 | pilot | 1/5 | 0/0 |  |
| a_f1_refurb-laptop-screen | 1.3.0 | P3 | pilot | 0/5 | 0/0 |  |
| a_f1_refurb-laptop-screen | 1.4.0 | P2 | pilot | 0/5 | 0/5 |  |
| a_f1_refurb-laptop-screen | 1.4.0 | P3 | pilot | 0/5 | 0/5 |  |
| a_f1_refurb-laptop-screen | 1.5.0 | P2 | pilot | 0/5 | 0/5 |  |
| a_f1_refurb-laptop-screen | 1.5.0 | P3 | pilot | 0/5 | 0/5 |  |
| a_f1_sandwich-image-audit | 1.3.0 | P4 | pilot | 0/5 | 0/5 |  |
| a_f1_spice-pitch-deck-qa | 2.0.0 | P4 | pilot | 0/5 | 0/0 |  |
| a_f1_spice-pitch-deck-qa | 2.1.0 | P4 | pilot | 0/5 | 0/0 |  |
| a_f1_spice-pitch-deck-qa | 2.2.0 | P4 | pilot | 3/5 | 0/5 |  |
| a_f1_spice-pitch-deck-qa | 2.3.0 | P4 | pilot | 4/5 | 0/5 |  |
| a_f1_spice-pitch-deck-qa | 2.4.0 | P4 | pilot | 4/5 | 0/5 |  |
| a_f1_spice-pitch-deck-qa | 2.5.0 | P4 | pilot | 4/5 | 0/5 |  |
| a_f1_spice-pitch-deck-qa | 2.6.0 | P4 | pilot | 5/5 | 1/5 |  |
| a_f1_student-laptop-shortlist | 2.0.0 | P4 | pilot | 0/5 | 0/0 |  |
| a_f1_student-laptop-shortlist | 2.1.0 | P4 | pilot | 0/5 | 0/0 |  |
| a_f1_student-laptop-shortlist | 2.2.0 | P4 | pilot | 1/5 | 0/5 |  |
| a_f1_student-laptop-shortlist | 2.3.0 | P4 | pilot | 0/5 | 0/5 |  |
| a_f1_student-laptop-shortlist | 2.3.0 | P5 | pilot | 0/5 | 0/5 |  |
| a_f1_suitcase-cover-matrix-check | 2.0.0 | P2 | pilot | 4/5 | 0/5 | BLIND-1.0 |
| a_f1_suitcase-cover-matrix-check | 2.0.0 | P3 | pilot | 0/5 | 0/5 |  |
| a_f1_suitcase-cover-matrix-check | 2.1.0 | P2 | pilot | 1/5 | 0/5 | GENUINE |
| a_f1_suitcase-cover-matrix-check | 2.1.0 | P6 | pilot | 0/5 | 0/5 |  |
| a_f1_suitcase-cover-matrix-check | 2.1.1 | P2 | pilot | 2/5 | 0/5 | GENUINE |
| a_f1_suitcase-cover-matrix-check | 2.1.1 | P6 | pilot | 0/5 | 0/5 |  |
| a_f1_suitcase-cover-matrix-check | 2.2.0 | P2 | pilot | 2/5 | 0/0 |  |
| a_f1_suitcase-cover-matrix-check | 2.2.0 | P6 | pilot | 0/5 | 0/0 |  |
| a_f1_suitcase-cover-matrix-check | 2.3.0 | P2 | pilot | 1/5 | 0/5 |  |
| a_f1_suitcase-cover-matrix-check | 2.3.0 | P6 | pilot | 0/5 | 0/5 |  |
| a_f1_suitcase-cover-matrix-check | 2.4.0 | P2 | pilot | 3/5 | 0/0 |  |
| a_f1_suitcase-cover-matrix-check | 2.4.0 | P6 | pilot | 0/5 | 0/0 |  |
| a_f1_suitcase-cover-matrix-check | 2.5.0 | P2 | pilot | 3/5 | 0/5 |  |
| a_f1_suitcase-cover-matrix-check | 2.5.0 | P6 | pilot | 0/5 | 0/5 |  |
| a_f1_suitcase-cover-matrix-check | 2.6.0 | P2 | pilot | 2/5 | 0/5 | GENUINE |
| a_f1_suitcase-cover-matrix-check | 2.6.0 | P6 | pilot | 0/5 | 0/5 |  |
| a_f1_timesheet-overtime-review | 2.0.0 | P3 | pilot | 0/5 | 0/0 |  |
| a_f1_timesheet-overtime-review | 2.1.0 | P3 | pilot | 0/5 | 0/0 |  |
| a_f1_timesheet-overtime-review | 2.2.0 | P3 | pilot | 0/5 | 0/5 |  |
| a_f1_timesheet-overtime-review | 2.3.0 | P3 | pilot | 0/5 | 0/5 |  |
| a_f1_timesheet-overtime-review | 2.4.0 | P3 | pilot | 0/5 | 0/0 |  |
| a_f1_timesheet-overtime-review | 2.5.0 | P3 | pilot | 0/5 | 0/0 |  |
| a_f1_timesheet-overtime-review | 2.6.0 | P3 | pilot | 0/5 | 0/0 |  |
| a_f1_timesheet-overtime-review | 2.7.0 | P3 | pilot | 0/5 | 0/5 |  |
| a_f2_billiard-shift-audit | 2.0.0 | P4 | pilot | 3/5 | 0/5 | BLIND-1.0 |
| a_f2_billiard-shift-audit | 2.1.0 | P4 | pilot | 3/5 | 0/5 |  |
| a_f2_cafe-kitchen-schedule-revisions | 2.0.0 | P5 | pilot | 0/5 | 0/0 |  |
| a_f2_cafe-kitchen-schedule-revisions | 2.0.0 | P9 | pilot | 0/5 | 0/0 |  |
| a_f2_cafe-kitchen-schedule-revisions | 2.1.0 | P2 | pilot | 0/5 | 0/5 |  |
| a_f2_cafe-kitchen-schedule-revisions | 2.1.0 | P3 | pilot | 0/5 | 0/5 |  |
| a_f2_cafe-kitchen-schedule-revisions | 2.1.0 | P5 | pilot | 0/5 | 0/5 |  |
| a_f2_cafe-kitchen-schedule-revisions | 2.1.0 | P7 | pilot | 0/5 | 0/5 |  |
| a_f2_cafe-kitchen-schedule-revisions | 2.1.1 | P2 | pilot | 0/5 | 0/5 |  |
| a_f2_cafe-kitchen-schedule-revisions | 2.1.1 | P3 | pilot | 0/5 | 0/5 |  |
| a_f2_cafe-kitchen-schedule-revisions | 2.1.1 | P5 | pilot | 1/5 | 0/5 |  |
| a_f2_cafe-kitchen-schedule-revisions | 2.1.1 | P7 | pilot | 0/5 | 0/5 |  |
| a_f2_cafe-kitchen-schedule-revisions | 2.2.0 | P2 | pilot | 0/5 | 0/0 |  |
| a_f2_cafe-kitchen-schedule-revisions | 2.2.0 | P3 | pilot | 0/5 | 0/0 |  |
| a_f2_cafe-kitchen-schedule-revisions | 2.2.0 | P5 | pilot | 0/5 | 0/0 |  |
| a_f2_cafe-kitchen-schedule-revisions | 2.2.0 | P7 | pilot | 0/5 | 0/0 |  |
| a_f2_cafe-kitchen-schedule-revisions | 2.3.0 | P2 | pilot | 0/5 | 0/0 |  |
| a_f2_cafe-kitchen-schedule-revisions | 2.3.0 | P3 | pilot | 0/5 | 0/0 |  |
| a_f2_cafe-kitchen-schedule-revisions | 2.3.0 | P5 | pilot | 1/5 | 0/0 | GENUINE |
| a_f2_cafe-kitchen-schedule-revisions | 2.3.0 | P7 | pilot | 0/5 | 0/0 |  |
| a_f2_cafe-kitchen-schedule-revisions | 2.4.0 | P2 | pilot | 0/5 | 0/5 |  |
| a_f2_cafe-kitchen-schedule-revisions | 2.4.0 | P3 | pilot | 0/5 | 0/5 |  |
| a_f2_cafe-kitchen-schedule-revisions | 2.4.0 | P5 | pilot | 0/5 | 0/5 |  |
| a_f2_cafe-kitchen-schedule-revisions | 2.4.0 | P7 | pilot | 0/5 | 0/5 |  |
| a_f2_deck-preread-review | 2.1.0 | P4 | pilot | 3/5 | 0/0 |  |
| a_f2_deck-preread-review | 2.2.0 | P4 | pilot | 4/5 | 5/5 | GENUINE |
| a_f2_deck-preread-review | 2.3.0 | P4 | pilot | 3/5 | 5/5 | GENUINE |
| a_f2_deck-preread-review | 2.4.0 | P4 | pilot | 1/5 | 5/5 |  |
| a_f2_deck-preread-review | 2.5.0 | P4 | pilot | 2/5 | 0/5 |  |
| a_f2_deck-preread-review | 2.6.0 | P4 | pilot | 1/5 | 1/5 |  |
| a_f2_deck-preread-review | 2.7.0 | P4 | pilot | 1/5 | 2/5 |  |
| a_f2_deck-preread-review | 2.8.0 | P4 | pilot | 5/5 | 5/5 | GENUINE-soft |
| a_f2_eco-guard-errata-review | 2.0.0 | P3 | pilot | 0/5 | 0/0 |  |
| a_f2_eco-guard-errata-review | 2.1.0 | P3 | pilot | 5/5 | 0/0 | AMBIGUOUS |
| a_f2_eco-guard-errata-review | 2.2.0 | P3 | pilot | 2/5 | 0/0 |  |
| a_f2_eco-guard-errata-review | 2.3.0 | P3 | pilot | 3/5 | 0/5 |  |
| a_f2_hammamet-voucher-reissue | 2.1.0 | P5 | pilot | 0/5 | 0/0 |  |
| a_f2_hammamet-voucher-reissue | 2.2.0 | P5 | pilot | 0/5 | 0/5 |  |
| a_f2_hammamet-voucher-reissue | 2.2.0 | P6 | pilot | 0/5 | 0/5 |  |
| a_f2_ktp-lesson-plan-alignment | 2.1.0 | P4 | pilot | 1/5 | 0/0 | BLIND-1.0 |
| a_f2_ktp-lesson-plan-alignment | 2.2.0 | P4 | pilot | 0/5 | 0/0 |  |
| a_f2_ktp-lesson-plan-alignment | 2.3.0 | P4 | pilot | 0/5 | 0/5 |  |
| a_f2_ktp-lesson-plan-alignment | 2.3.0 | P5 | pilot | 0/5 | 0/5 |  |
| a_f2_moot-issue3-memorial-audit | 2.0.0 | P1 | pilot | 0/5 | 0/0 |  |
| a_f2_moot-issue3-memorial-audit | 2.1.0 | P1 | pilot | 0/5 | 0/5 |  |
| a_f2_moot-issue3-memorial-audit | 2.1.0 | P10 | pilot | 5/5 | 0/5 | AMBIGUOUS |
| a_f2_moot-issue3-memorial-audit | 2.1.0 | P11 | pilot | 0/5 | 1/5 | BLIND-1.0 |
| a_f2_moot-issue3-memorial-audit | 2.1.0 | P12 | pilot | 3/5 | 0/5 | AMBIGUOUS |
| a_f2_moot-issue3-memorial-audit | 2.1.0 | P13 | pilot | 0/5 | 3/5 | BLIND-1.0 |
| a_f2_moot-issue3-memorial-audit | 2.1.0 | P14 | pilot | 0/5 | 0/5 | AMBIGUOUS |
| a_f2_moot-issue3-memorial-audit | 2.1.0 | P15 | pilot | 0/5 | 5/5 | BLIND-1.0 |
| a_f2_moot-issue3-memorial-audit | 2.2.0 | P1 | pilot | 0/5 | 0/5 |  |
| a_f2_moot-issue3-memorial-audit | 2.2.0 | P10 | pilot | 0/5 | 0/5 |  |
| a_f2_moot-issue3-memorial-audit | 2.2.0 | P11 | pilot | 0/5 | 1/5 |  |
| a_f2_moot-issue3-memorial-audit | 2.2.0 | P12 | pilot | 0/5 | 0/5 |  |
| a_f2_moot-issue3-memorial-audit | 2.2.0 | P13 | pilot | 0/5 | 0/5 |  |
| a_f2_moot-issue3-memorial-audit | 2.2.0 | P14 | pilot | 1/5 | 0/5 |  |
| a_f2_moot-issue3-memorial-audit | 2.2.0 | P15 | pilot | 0/5 | 2/5 |  |
| a_f2_moot-issue3-memorial-audit | 2.2.0 | P16 | pilot | 0/5 | 0/5 |  |
| a_f2_moot-issue3-memorial-audit | 2.2.0 | P17 | pilot | 0/5 | 0/5 |  |
| a_f2_moot-issue3-memorial-audit | 2.2.0 | P18 | pilot | 0/5 | 0/5 |  |
| a_f2_okra-manuscript-revision | 2.0.0 | P6 | pilot | 2/5 | 0/0 |  |
| a_f2_okra-manuscript-revision | 2.0.0 | P7 | pilot | 0/5 | 0/0 |  |
| a_f2_okra-manuscript-revision | 2.0.0 | P8 | pilot | 0/5 | 0/0 |  |
| a_f2_okra-manuscript-revision | 2.1.0 | P6 | pilot | 0/5 | 0/0 |  |
| a_f2_okra-manuscript-revision | 2.1.0 | P7 | pilot | 0/5 | 0/0 |  |
| a_f2_okra-manuscript-revision | 2.1.0 | P8 | pilot | 0/5 | 0/0 |  |
| a_f2_okra-manuscript-revision | 2.2.0 | P6 | pilot | 3/5 | 0/5 |  |
| a_f2_okra-manuscript-revision | 2.2.0 | P7 | pilot | 0/5 | 0/5 |  |
| a_f2_okra-manuscript-revision | 2.2.0 | P8 | pilot | 1/5 | 0/5 |  |
| a_f2_pathway-choice-audit | 2.1.0 | P6 | pilot | 0/5 | 0/5 |  |
| a_f2_pathway-choice-audit | 2.5.0 | P6 | pilot | 0/5 | 0/5 |  |
| a_f2_pathway-choice-audit | 2.6.0 | P6 | pilot | 2/5 | 0/5 | BLIND-1.0 |
| a_f2_pathway-choice-audit | 2.7.0 | P6 | pilot | 2/5 | 0/5 |  |
| a_f2_station-register-consolidation | 2.1.0 | P4 | pilot | 0/5 | 0/0 |  |
| a_f2_station-register-consolidation | 2.2.0 | P4 | pilot | 0/5 | 0/0 |  |
| a_f2_station-register-consolidation | 2.3.0 | P4 | pilot | 1/5 | 0/5 |  |

### T3: Quantity basis cued only on or about the record (tax-inclusive, per pack)

- **Status:** proven
- **Family:** quantity_basis
- **Aimed at:** both
- **Clock trap:** no
- **Aliases:** Q.taxincl, Q.pack, quantity basis
- **Pooled misses:** Fable 153/235 (65%), Astra 49/200 (24%)
- **Loopholes:** L-default, L-shield, L-threshold

A price or quantity is read on the wrong basis: a tax-inclusive bill read as net, a price per pair or pack read as per piece. The basis is cued only on or about the record itself (a cheque note, a received-goods tally, the seller's filed orders), never in a caption next to the figures. Fable misses tax-inclusive bases; per-pack pricing with a tally bites both. Measured here (build_evidence.py, 2026-10-15): final 10x2 pooled Fable 78/90, Astra 23/90; all stages Fable 153/235, Astra 49/200 (AMBIGUOUS/DEFECT units excluded). Audited GENUINE in 4 task(s). Status proven: audited GENUINE in 4 tasks; pooled final miss rate >= 0.2 with n >= 20 on fable, astra (unaudited >= 90% units excluded).

**Recipe**

- *record:* a bill, list price or order line whose figures look complete on the default basis
- *anchors:* a cue on the record or about this record (a tally of what was received, the seller's own filed order lines, a remark that the rise was not passed on)
- *withheld:* no caption or column header states the basis
- *dials:*
  - change the kind of evidence (a received-goods tally moved Astra where more filed lists of the same kind did not: cnc 2.6.0 P4)
  - the weakest oblique cue restored the Fable bite on gst P3 ('same rates as our counter board')
- *conservation:* the per-piece reading must contradict a received count or a total
- *shields:* a 'printed rate governs' rule must be scoped to rates, not to what the price includes

**Proof obligations (authoring/validate.py)**

- uniqueness: only one basis reproduces the tally or the paid total
- ablation: without the on-record cue the basis is underdetermined (executed)
- blind reader: a non-governing-document cue that the reader also misses is unfair

**Hazards**

- a cue in a caption next to the figures is a stated rule: suitcase 2.2.0/2.3.0 P7 Fable 0/10
- a cue only in a non-governing document with one out-of-population figure: suitcase 2.4.0/2.5.0 P7, blind reader also missed (UNCONFIRMED)
- a single route is GENUINE-soft: cnc 2.3.0 P4
- bimodal by model: tax-inclusive bit Fable 33/40 finals and Astra 0/40 (gst P3)

**What killed it**

- one extra cue on every line: gst 1.5.0/1.6.0 P3 10/15 to 1/5 and 0/5 ('a single figure on each line', a second 'nothing to add on' note)
- student P3 tax-exclusive quote: 0/15 F, 0/10 A

**Trace signals**

- the user corrects a total because a price already included tax or covered two items
- receipts or tallies that disagree with list prices
- retail or workshop purchasing

**Domains**

- small retail and stationery
- workshop and maker BOMs
- trading-card and hobby budgets
- merchandising price matrices

**Example.** A bearing listed at one price per line is ordered one per piece, though the seller's own filed orders and the receiving tally show each line delivered two pieces.

**Measured here**

| task | version | premise | stage | Fable missed | Astra missed | audit |
|---|---|---|---|---|---|---|
| a_f1_gst-workbook-answer-key | 1.3.0 | P3 | final | 10/10 | 0/10 | GENUINE |
| a_f1_gst-workbook-answer-key | 1.4.0 | P3 | final | 7/10 | 0/10 | GENUINE |
| a_f1_gst-workbook-answer-key | 1.4.1 | P3 | final | 8/10 | 0/10 | GENUINE |
| a_f1_gst-workbook-answer-key | 1.7.0 | P3 | final | 8/10 | 0/10 | GENUINE |
| a_f1_kibo-budget-cap-review | 2.9.0 | P6 | final | 10/10 | 0/10 | GENUINE |
| a_f1_suitcase-cover-matrix-check | 2.6.0 | P7 | final | 6/10 | 0/10 | GENUINE |
| a_f2_cnc-router-bom-reconcile | 2.3.0 | P4 | final | 10/10 | 10/10 | GENUINE-soft |
| a_f2_cnc-router-bom-reconcile | 2.6.0 | P4 | final | 9/10 | 7/10 | GENUINE |
| a_f2_cnc-router-bom-reconcile | 2.6.1 | P4 | final | 10/10 | 6/10 | GENUINE |
| a_f1_gst-workbook-answer-key | 1.1.0 | P3 | pilot | 0/5 | 0/0 |  |
| a_f1_gst-workbook-answer-key | 1.2.0 | P3 | pilot | 5/5 | 0/5 |  |
| a_f1_gst-workbook-answer-key | 1.3.0 | P3 | pilot | 4/5 | 0/5 | GENUINE |
| a_f1_gst-workbook-answer-key | 1.4.0 | P3 | pilot | 4/5 | 0/5 | GENUINE |
| a_f1_gst-workbook-answer-key | 1.4.1 | P3 | pilot | 2/5 | 0/5 | GENUINE |
| a_f1_gst-workbook-answer-key | 1.5.0 | P3 | pilot | 1/5 | 0/5 |  |
| a_f1_gst-workbook-answer-key | 1.6.0 | P3 | pilot | 0/5 | 0/5 |  |
| a_f1_gst-workbook-answer-key | 1.7.0 | P3 | pilot | 3/5 | 0/5 | GENUINE |
| a_f1_kibo-budget-cap-review | 2.8.0 | P6 | pilot | 5/5 | 0/5 |  |
| a_f1_kibo-budget-cap-review | 2.9.0 | P6 | pilot | 5/5 | 0/5 | GENUINE |
| a_f1_kibo-budget-cap-review | 2.10.0 | P6 | pilot | 4/5 | 0/5 |  |
| a_f1_kibo-budget-cap-review | 2.11.0 | P6 | pilot | 4/5 | 0/5 |  |
| a_f1_moisturiser-price-screen | 2.3.0 | P6 | pilot | 1/5 | 0/5 |  |
| a_f1_student-laptop-shortlist | 2.1.0 | P3 | pilot | 0/5 | 0/0 |  |
| a_f1_student-laptop-shortlist | 2.2.0 | P3 | pilot | 0/5 | 0/5 |  |
| a_f1_student-laptop-shortlist | 2.3.0 | P3 | pilot | 0/5 | 0/5 |  |
| a_f1_suitcase-cover-matrix-check | 2.2.0 | P7 | pilot | 0/5 | 0/0 |  |
| a_f1_suitcase-cover-matrix-check | 2.3.0 | P7 | pilot | 0/5 | 0/5 |  |
| a_f1_suitcase-cover-matrix-check | 2.4.0 | P7 | pilot | 5/5 | 0/0 | UNCONFIRMED |
| a_f1_suitcase-cover-matrix-check | 2.5.0 | P7 | pilot | 5/5 | 4/5 | UNCONFIRMED |
| a_f1_suitcase-cover-matrix-check | 2.6.0 | P7 | pilot | 2/5 | 0/5 | GENUINE |
| a_f2_cnc-router-bom-reconcile | 2.0.0 | P5 | pilot | 0/5 | 0/0 |  |
| a_f2_cnc-router-bom-reconcile | 2.1.0 | P5 | pilot | 0/5 | 0/0 |  |
| a_f2_cnc-router-bom-reconcile | 2.2.0 | P5 | pilot | 0/5 | 0/0 |  |
| a_f2_cnc-router-bom-reconcile | 2.3.0 | P4 | pilot | 5/5 | 5/5 | GENUINE-soft |
| a_f2_cnc-router-bom-reconcile | 2.4.0 | P4 | pilot | 5/5 | 5/5 |  |
| a_f2_cnc-router-bom-reconcile | 2.5.0 | P4 | pilot | 5/5 | 5/5 |  |
| a_f2_cnc-router-bom-reconcile | 2.6.0 | P4 | pilot | 5/5 | 4/5 | GENUINE |
| a_f2_cnc-router-bom-reconcile | 2.6.1 | P4 | pilot | 5/5 | 3/5 | GENUINE |

### T12: Line transposition settled by first-hand descriptions

- **Status:** proven
- **Family:** record_reversal
- **Aimed at:** both
- **Clock trap:** no
- **Aliases:** ID.swap, line transposition
- **Pooled misses:** Fable 62/155 (40%), Astra 93/150 (62%)
- **Loopholes:** L-record, L-absorb

Two lines of a record (two pupils' results, the left and right arm readings, two register weeks) are transposed; first-hand descriptions (a star stamp, who is captain, which arm the cuff was on) settle which line is whose. The default keeps the printed lines. Measured here (build_evidence.py, 2026-10-15): final 10x2 pooled Fable 37/70, Astra 54/70; all stages Fable 62/155, Astra 93/150 (AMBIGUOUS/DEFECT units excluded); without unaudited >=90% units, final Fable 27/50, Astra 36/50. Audited GENUINE in 2 task(s). Status proven: audited GENUINE in 2 tasks; pooled final miss rate >= 0.2 with n >= 20 on fable, astra (unaudited >= 90% units excluded).

**Recipe**

- *record:* a sheet or export with two lines transposed in a plausible way
- *anchors:* first-hand descriptions from two parties that fit only the swapped reading
- *withheld:* no sentence says the lines were swapped
- *dials:*
  - one more route that fits the swap (home-bp 2.12.0 'never used the other arm')
- *conservation:* grade both lines
- *shields:* scope any 'the sheet is the record' sentence

**Proof obligations (authoring/validate.py)**

- uniqueness: only the swap fits every description
- ablation per anchor
- blind reader (home-bp 2.11.0 was too hidden)

**Hazards**

- too hidden when a blind reader also misses: home-bp 2.11.0 P6 (eased in 2.12.0)
- a validity fix removed Astra's whole-row swap reading on pupil 1.2.0

**What killed it**

- okra P10/P11/P13 transposed cells: 0/20 Fable, 0/15 Astra

**Trace signals**

- the user swaps two rows or names in a table
- paper sheets transcribed by someone else

**Domains**

- school assessment
- home monitoring diaries
- class registers

**Example.** A results export prints two pupils' scores on each other's lines; the teacher's stamp on one paper and a parent's remark about which items were left blank fit only the swap.

**Measured here**

| task | version | premise | stage | Fable missed | Astra missed | audit |
|---|---|---|---|---|---|---|
| a_f1_home-bp-diary-summary | 2.12.0 | P6 | final | 10/10 | 8/10 | GENUINE |
| a_f1_home-bp-diary-summary | 2.12.1 | P6 | final | 10/10 | 7/10 | GENUINE |
| a_f1_melody-lesson-results | 1.1.0 | P2 | final | 1/10 | 9/10 | GENUINE |
| a_f1_melody-lesson-results | 1.1.1 | P2 | final | 0/10 | 8/10 | GENUINE |
| a_f1_melody-lesson-results | 1.3.0 | P2 | final | 0/10 | 9/10 |  |
| a_f1_melody-lesson-results | 1.3.0 | P5 | final | 10/10 | 9/10 |  |
| a_f1_pupil-tracker-term-summary | 1.1.0 | P2 | final | 6/10 | 4/10 | BLIND-1.0 |
| a_f1_home-bp-diary-summary | 2.11.0 | P6 | pilot | 5/5 | 5/5 | UNCONFIRMED |
| a_f1_home-bp-diary-summary | 2.12.0 | P6 | pilot | 5/5 | 4/5 | GENUINE |
| a_f1_home-bp-diary-summary | 2.12.1 | P6 | pilot | 4/5 | 4/5 | GENUINE |
| a_f1_melody-lesson-results | 1.1.0 | P2 | pilot | 0/5 | 5/5 | GENUINE |
| a_f1_melody-lesson-results | 1.1.1 | P2 | pilot | 0/5 | 5/5 | GENUINE |
| a_f1_melody-lesson-results | 1.2.0 | P2 | pilot | 1/5 | 5/5 |  |
| a_f1_melody-lesson-results | 1.2.0 | P5 | pilot | 0/5 | 0/5 |  |
| a_f1_melody-lesson-results | 1.3.0 | P2 | pilot | 0/5 | 4/5 |  |
| a_f1_melody-lesson-results | 1.3.0 | P5 | pilot | 4/5 | 4/5 |  |
| a_f1_pupil-tracker-term-summary | 1.1.0 | P2 | pilot | 3/5 | 3/5 | BLIND-1.0 |
| a_f1_pupil-tracker-term-summary | 1.2.0 | P2 | pilot | 2/5 | 0/5 |  |
| a_f1_pupil-tracker-term-summary | 1.3.0 | P2 | pilot | 0/5 | 0/5 |  |
| a_f1_pupil-tracker-term-summary | 1.4.0 | P2 | pilot | 1/5 | 0/5 |  |
| a_f2_okra-manuscript-revision | 2.1.0 | P10 | pilot | 0/5 | 0/0 |  |
| a_f2_okra-manuscript-revision | 2.2.0 | P10 | pilot | 0/5 | 0/5 |  |
| a_f2_okra-manuscript-revision | 2.2.0 | P11 | pilot | 0/5 | 0/5 |  |
| a_f2_okra-manuscript-revision | 2.2.0 | P13 | pilot | 0/5 | 0/5 |  |
