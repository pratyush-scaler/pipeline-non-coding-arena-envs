# Batch 6 round 3 (B6v6): stack the PROVEN mechanisms (2026-10-15; 75-minute box)

> **History (2026-10-15).** Superseded as instructions by `AUTHOR-BRIEF-B8.md`; kept for the measurements and reasoning behind its rules. Paths below are the old workspace layout (`$W/research/batch4/...`): in this repo the tools are in `production/tools/`, the briefs in `production/briefs/`, the templates in `production/templates/`, and trap modes come from `production/traps/TRAP-LIBRARY.md`.

Round 2 invented seven new kinds of trap and none landed. Measured on Fable:
- a stated rule was solved 0/5;
- the same fact hidden behind passing remarks was missed 5/5, and blind readers missed it too.

This round invents nothing. Your task gets **three decisive traps built from the templates below**. They are re-instantiated in this task's own material, with the SAME structural ingredients as the measured source, and dialled to the hard end of the band. The goal is a task that is extremely hard for BOTH models and still clean.

Read first, all still binding:
- `TUNE-BRIEF-B6v5-stochastic.md`: validity rules, gates and dials, plus the three round-2 addenda at its end;
- `HARD-DOCTRINE-B6v2.md` §5, §7 and §9–§15.

## Proven templates (measured in this harness, each audited GENUINE)

Before you build a template, open its source premise's files, VALIDATION.md entry and DIAL.md. Copy the *ingredients*; do not copy the wording.

**T1 Keying slip (identity).**
- **Measured:** both models 60–100% undialled. gst 1.7.0 P1: F 1/10, A 7/10. pathway 2.3.0 P2: F 7/10. cnc 2.6.1 P3: F 9/10.
- **Ingredients:**
  - A record is keyed under an ID it does not belong to.
  - The printed row is complete and self-consistent.
  - The true owner is identifiable only by descriptive details in two or more documents read for other reasons.
  - No sentence binds the printed key.
- **Dial:** one by-the-way descriptive anchor per notch (pathway "who wants to fly": F 10/10 → 7/10). A too-specific anchor overshoots (coloring "little crow": F 0.7 pass).
- **Kills it:**
  - a corrective or exclusive sentence;
  - a pointer;
  - a binding sentence;
  - a clash with a structured field.
- **Sources:** `_versions/a_f1_gst-workbook-answer-key-1.7.0` (P1), `_versions/a_f2_cnc-router-bom-reconcile-2.6.1` (P3), `_v5b/a_f2_pathway-choice-audit` (P2).

**T2 One-figure convention exemplar (convention).**
- **Measured:** Astra 80–100%, Fable 0–70%. gst 1.7.0 P2: A 8/10. profile 2.4.0 P5: A 10/10, F 10/10. deck 2.3.0 P4: A 10/10, F 7/10.
- **Ingredients:**
  - The governing document says what is reported but not the method (rounding, truncation, per-bill vs per-line, which end of a range).
  - EXACTLY ONE worked figure discriminates the method. It sits in the governing document, or in a signed record that document binds (§15.2).
  - Every other worked figure is non-discriminating.
- **Dial:** one more discriminating figure flips Astra to about 0 (profile P5: 10/10 → 0/5). Never add one for Astra; for Fable, move the single figure closer to where the figure is reported.
- **Kills it:**
  - a precedent clause;
  - "see the example";
  - a method name anywhere, including a template that prints the method's output (coloring spine: dead on Fable).
- **Sources:** gst 1.7.0 P2 (the HoD's ₹4,880 debit), `_versions/a_f1_profile-copy-claims-audit-2.4.0` P5.

**T3 Quantity meaning behind an indirect cue on the record itself (quantity).**
- **Measured:** gst 1.7.0 P3, tax-inclusive: F 8/10. cnc 2.6.1 P4, pair pricing with a receipt tally: F 10/10, A 6/10.
- **Ingredients:**
  - The figure's basis (tax-inclusive, per pair, per pack, per hundred) is signalled only by a semantic cue ON or ABOUT that record.
  - Examples: "the bill is at the same rates as our counter board"; a goods-received tally counting pieces against a price line counting packs.
  - The governing rule is silent on the basis.
- **Kills it:**
  - a caption naming the basis next to the figures (suitcase 2.3.0: 0/5);
  - a cue that lives only in non-governing documents and contradicts the governing one. Suitcase 2.4.0/2.5.0 were missed 5/5 and the blind reader missed them too, so the trap was INVALID.
- **Sources:** gst 1.7.0 P3; cnc 2.6.1 P4 (the "Diterima Sari… 4 bearing, 4 dudukan as" tally).

**T4 Scope: already in hand (scope).**
- **Measured:** cnc 2.6.1 P5: F 6/10, A 0/10.
- **Ingredients:**
  - A rule says to order or act only on what is still needed.
  - A first-hand record shows one item is already in hand, named by a technical or descriptive bridge, not by its catalogue name. In cnc, "FluidNC" and "Vref" bridge to the controller kit.
- **Kills it:** a direct statement of possession (kibo 2.5.0–2.7.0: 0/5).
- **Source:** cnc 2.6.1 P5 (rule 1.7).

**T5 Misfiled note (caption vs content).**
- **Measured:** deck 2.5.0 P5: F 4/10, A 0/10.
- **Ingredients:** a note or comment is filed under one item, but its content can only be about another item, and the content alone identifies that item.
- **Source:** `_v5b/a_f2_deck-preread-review` 2.5.0 P5 (N9).

**T6 Authority-parity temporal applicability (temporal).**
- **Measured:** cafe 2.3.0 P1 and P6: F 5/10 each.
- **Ingredients:**
  - Which edition, rate or rule applies depends on a date.
  - Two sources of SIMILAR authority disagree, e.g. a log entry against a dated register note plus a third party's dated mail.
  - First-hand dated records resolve it.
- **Kills it:**
  - a stated mapping rule (timesheet 2.4.0/2.5.0: 0/5);
  - an informal remark set against an official record (home-bp 2.6.0/2.7.0: 5/5, and the blind reader missed it, so INVALID).
- **Source:** `_v5b/a_f2_cafe-kitchen-schedule-revisions` 2.3.0 P1/P6.

**T7 Convention from two worked figures by different parties (convention).**
- **Measured:** cafe 2.3.0 P11: F 4/10.
- **Source:** cafe P11 ("next 5 cm": the standard's 6.1 figure plus another job's filed note).

**T8 Changed premise received before issue (changed premise).**
- **Measured:** cafe 2.3.0 P8: F 2/10.
- **Source:** cafe P8 (a civil-protection condition re-hangs the door).

## Design rule for this round
- **Three decisive traps, each from a different family:**
  - one Astra-proven template: T2, or T3 per-pack;
  - one Fable-proven template: T3 tax-inclusive, T4, T5 or T6;
  - the task's keying slip (T1), dialled to about 40–60% on both models.
  - A fourth trap is allowed only if it is a T7/T8 low-weight filler.
- **Fit:** build each template only where the task's domain supports it naturally (a tax cue needs a bill; in-hand needs an order). If a template cannot be instantiated naturally, pick another and say why. Never force one.
- **Ingredients:** same as the source. Do not add extra routes, and do not hide the cue further than the source does; the source's level is what measured in band.
- **Families in one file:** keep each template's anchors out of any document that another trap of the SAME family uses.
- **Weights:**
  - decisive traps 25 / 21 / 17 (or similar, unequal, ≥ 60 together);
  - dead premises down to ≤ 5 points each as fillers, or removed;
  - free share ≤ 0.40;
  - ≥ 8 graded checks summing to 100;
  - no cascade (§15.3: downstream checks grade on the agent's own upstream answer).
- **Proof for each new trap, in VALIDATION.md and validate.py:**
  - a uniqueness check;
  - an anchor ablation;
  - an executed counterfactual;
  - a census of its plausible wrong answers, each losing only its own check.
- **ONE version only this round,** at the setting you judge most likely to land at 40–60% on Fable. I dial after measurement. List every dial-able sentence in `authoring/DIAL.md`.
- **Target, measured 10 × 2:** pass@1 0.1–0.3 per model, ≥ 3 failure patterns per model, free share ≤ 0.40.

## Where to build
- The new tree goes at `W/envs-b6/_v6/<task>`, copied from the base version named in your prompt.
- Bump to the version named in your prompt.
- Remove any `verification/` receipt from the copy (it belongs to the base version).
- Do not touch `_versions/`, `_v5b/`, `_v5c/`, `_v5d/` or the live tree.

## Gates and hand-back
- **Gates** (all in the B6v5 brief):
  - `b6ctl check` gives DESIGN GATE PASS and selftest 0 BAD;
  - validate.py exits 0;
  - no `__pycache__`;
  - traps.json lists every decisive trap with its `template` (T1–T8) and `target_model`.
- **Hand back in ≤ 14 lines:**
  - per trap: the template, the documents used, the default wrong answer, the weight and the expected miss rate per model;
  - the dial sentences;
  - the expected free share;
  - the gate results;
  - any template you could not fit, and why.

## Limits
- No pools and no arena, harbor, coder, measure or benchmark commands.
- Never read keys.env.
- Never glob /tmp; use `mktemp -d` and remove only paths you created.
- No subagents and no attribution lines.
