# TRAJ: reasoning loopholes in the failing runs, in the models' own words

B7 research. Written 2026-10-15. This was a read-only pass over stored campaign artifacts. Nothing was launched, and no keys or credentials were read.

**Models and harnesses**
- **Fable 5.1** ran in Claude Code (`agent/trajectory.json`, plus the `sessions/` jsonl). Its thinking blocks are stored empty, so its reasons come from:
  - messages;
  - the occasional `reasoning_content` summary;
  - code in its tool calls;
  - its deliverables.
- **GPT-6 Astra** ran in Codex (`agent/codex.txt` and the rollout jsonl). Its reasoning items are encrypted, with an empty `summary`, so its reasons come only from:
  - its progress messages (about 600 characters per step-run);
  - comments and literals in its Python;
  - its deliverables.

  When this note says an Astra run was "silent", it means nothing in that visible text mentions the deciding evidence. Its hidden reasoning may have.

---

## 0. Headline

1. **Reading is not the problem.** On 521 failing premise-runs, the trap's resolving quote and every anchor appeared in the model's own tool output in 519 cases. In all 521, the anchors were read before the first write to `/app/deliverables`.
   - The only true never-read cases (A) are 2 Astra coloring step-1 runs. Neither opened `correspondence/`.
   - Every other failure is an integration failure.
2. **The two models fail differently.**
   - **Fable (331 failing premise-runs).**
     - 56% voice the deciding evidence (classes B1, C*, C and F).
     - 43% notice the conflict and resolve it against the evidence (C* or C).
     - 104 of those 142 runs attach a "flag" or "worth confirming" note.
     - In 23 of them, the final message spells out the correct answer as an "If X, then Y" hedge, and the run still commits to the record.
   - **Astra (190 failing premise-runs).**
     - 83% are silent: 110 silent key-joins (B0) and 47 silent default conventions (D).
     - The rest surface in two structural ways rather than in prose:
       - 15 additive unions that keep both readings;
       - 14 abstentions to an allowed "not determinable" value.
     - Astra's messages contain no flags and no "If X then Y" alternatives (0 of 190 step-runs).
3. **The dominant loophole for both models is L1, record or key primacy.** A filed key or "official" record beats descriptive prose from another party.
   - It accounts for 211 of Fable's 331 failing premise-runs and 143 of Astra's 190.
   - Fable says why: "I priced it as the file spells it", "I followed the supplier document", "the art log, which is the production record", "the fabricator's remark about the recording is a note, not the record of receipt".
   - Astra just joins on the key.
4. **Fable has a second, mostly Fable-only loophole: the rule shield (L3).** A real governing rule is cited to dismiss an anchor that bears on a different variable, or that the rule does not cover. A rule or governing document is cited in 50 of the 142 voiced-and-wrong runs. Examples:
   - "Section 3.2 does not allow leaving a reading out for notes";
   - "the printed rates govern" (used against tax-inclusive pricing);
   - "the house method treats emails and call notes as non-evidence";
   - "the guide builds the register from the ATS roles only" (no such rule exists).
5. **What flips a run to the right answer:**
   - a visible mechanism for the slip (page number vs slide ID, transposed digits, "one learner ID along");
   - an **impossibility** rather than an improbability;
   - a third converging anchor that witnesses the event itself;
   - a unique conjunction match ("only D28 has both a shop sign and a bird").

   Measured dials that support this:
   - cafe P1: two anchors gave Fable 0 of 20; adding "Nicte was at the new window recording" gave 5 of 10.
   - deck P4: two worked figures gave Fable 7 misses of 10 and Astra 10 of 10; four figures gave Fable 2 of 10 and Astra 3 of 10.
6. **Genuine vs unfair.** Blind readers solve the key-override traps, where no sentence gives the key priority. They also miss when the model's dismissal is backed by a rule that really covers the case. The clearest example is a printed form, or a governing table, that states the opposite:
   - home-bp P5 (practice row): Fable 10 of 10 missed, and the blind reader missed too;
   - suitcase P7 (VAT basis): Fable 10 of 10 missed; the blind reader said "not in the matrix, so I ignored it".

   Inferences that only fill a gap died on Fable, 0 misses each on 5-run pilots: kibo scope, ats Kodexa, timesheet payroll cycle, pathway P4/P5. Each of these pilot traps reclassified an unlabeled item rather than overriding a record.

---

## 1. Corpus and method

**Campaigns read.** All are under `W/pipeline-artifacts/b4/<task>-<ver>-<stage>-<model>/`.
- **Shipped finals, 10 runs per model:**
  - pathway 2.0.0, profile-copy 2.4.0, home-bp 2.2.1, timesheet 2.2.0, kibo 2.3.1;
  - suitcase 2.1.1, deck 2.3.0, ats 1.1.0, cnc 2.3.0 and 2.6.1;
  - gst 1.4.1 and 1.7.0, coloring 2.3.0 (3 steps), cafe 2.1.1 (3 steps).
- **v5 finals:**
  - deck 2.5.0 (both models);
  - cafe 2.3.0, pathway 2.3.0, timesheet 2.4.0 and coloring 2.5.0 (Fable only; Astra voided by the auth failure).
- **Fable round-2 pilots, 5 runs each:**
  - suitcase 2.4.0 and 2.5.0, home-bp 2.6.0 and 2.7.0, kibo 2.7.0, ats 1.4.0, pathway 2.4.0, timesheet 2.6.0.
- **Totals:**
  - Fable: 230 runs, or 310 step-runs.
  - Astra: 150 runs, or 190 step-runs.
  - Failing premise-runs on the graded trap premises: Fable 331, Astra 190.

**Procedure.** Premise maps come from each campaign's frozen `package/authoring/traps.json`, so the premise always matches the run. For every (run, premise) whose checks failed in `verifier/reward-details.json`:

1. **Was it read?** Check whether the resolving quote and each anchor appear in the model's tool outputs, using normalized 6-word windows, Unicode-aware. If not, the run is class A.
2. **Was the anchor voiced?** Check whether the anchor's distinctive terms appear in the model's own text: messages, reasoning summaries, code lines that are not cat/sed/ls commands, and the deliverable. One regex per premise.
3. **Was the alternative named?** Check whether the model's text names the *correct alternative for the graded item*. A second regex per premise.
4. **Assign a class:**
   - **C**: the alternative was named, and the run still failed. The model weighed it and chose the record.
   - **C\***: the anchor was voiced, and within ±350 characters it was dismissed, kept "as written", flagged or deferred.
   - **B1**: the anchor was voiced with no dismissal and no join.
   - **B0**: silent (for twin, actual and attribution traps).
   - **D**: silent (for exemplar and scale traps).
   - **F-union**: detected from the check reasons: the new owner was credited and the printed owner kept (ats), or both stocks were counted (cnc).
   - **F-abstain**: the check reason shows the answer was "not determinable".
5. **Spot checks.** Several samples per class were read by hand. False positives were corrected:
   - "door frame" in cafe;
   - "in pairs" in Python `object_pairs_hook`;
   - "recording half-centimetre" in cafe;
   - two Astra ats runs moved from B1 to C\*.

   The per-premise regexes are in `scratchpad/traj/classify.py`. Treat the counts as accurate to about ±3 per cell.
6. **Class E** (computed correctly but transcribed wrong) was looked for and not found in any sampled run.

**Excluded.** Failures that audits already called ambiguous or non-premise:
- deck 2.5.0's N5 `c_notes_other` / `c_sequence_pair` (4 Fable runs);
- Astra's coloring `c2_/c3_pages_front/noextra`, a scope bleed covered in L8.

---

## 2. Failure-class census

| class | meaning | Fable (331) | Astra (190) |
|---|---|---|---|
| A | deciding evidence never in the tool output | 0 | 2 (coloring P2, step 1: never opened `correspondence/`) |
| B0 | read, silent, keyed default | 84 (25%) | 110 (58%) |
| B1 | voiced the anchor, never tied it to the graded item | 40 (12%) | 0 |
| C* | voiced the anchor and dismissed or deferred it | 47 (14%) | 2 |
| C | named the correct alternative and rejected it | 95 (29%) | 0 |
| D | default convention or unit, silent | 60 (18%) | 47 (25%) |
| E | right computation, wrong transcription | 0 seen | 0 seen |
| F-union | credits both readings (no conservation check) | 4 | 15 (8%) |
| F-abstain | escapes to "not determinable" | 1 | 14 (7%) |

The per-premise breakdown is in Appendix A.

---

## 3. The loopholes

### L1. Record or key primacy: "the record wins over the remark"

**Definition.** When a structured record (an export key, filed slide ID, supplier dispatch note, art log, inbox log or bill) conflicts with descriptive prose from another party, the model keeps the record. Under L1 the prose is either never joined (Astra), or joined, recognised as conflicting, and overruled (Fable).

**Frequency.** On keyed identity premises (the TWIN and ACTUAL slips across 17 premises):
- **Fable missed 211 of 330 premise-runs (64%).** The 211 split as follows:
  - 104 C or C\*: noticed and overruled;
  - 23 B1;
  - 79 B0;
  - 5 F.
- **Astra missed 143 of 210 (68%).** The 143 split as follows:
  - 110 B0 (silent join);
  - 2 A;
  - 2 C\*;
  - 15 F-union;
  - 14 F-abstain.

**Fable's stated reasons.** Each quote is followed by its run ID.
- kibo P3: "One inconsistency to flag to Bia: the chat says the Japanese foil … was requested for Kessig Wolf Run, but the export carries that row under Cinder Glade. **I priced it as the file spells it.**" (6tmX6sV). Also "I priced the row under the name the export gives it" (NFEEwvi).
- cnc P3: "Dimas's printer log calls the four hung items 'motor cables', which conflicts with the supplier's shipping confirmation listing them as couplers. **I followed the supplier document.**" (AapPAN9). Also "the supplier's shipping confirmation and Darto's six-item count show they are couplers, so I followed the documents" (JmWvNXF).
- suitcase P5: "That matches «Ретро-марки» on ЧХ-30149, yet the supplier's design swap names ЧХ-30148. **I applied the supplier letter as written, since it is the explicit statement about the article**" (gAwTLWu). Also "I left it in the matrix since no file changes it" (RZkvShF).
- coloring P2: "**I followed the art log, which is the production record** of which file was revised. If the lettering actually landed on D28, page 61 would fail instead of page 37." (k6HYgHN)
- cafe P1 (2.3.0): "The later brief entry in the log belongs to job TC-2641, and **the fabricator's remark about the recording is a note, not the record of receipt.**" (tFTMM2s). Also "The similar-looking job TC-2641 … is a different project" (JXCq7Xz).
- gst P4: "Malaprabha's remark about crating the guillotine **does not change the bill's supplier**, Shree Balaji Paper Mart of Pune" (EPKukEk). One run's section is headed "**Red herrings I set aside**" (TnFqH5m); another's is "**Distractors I did not act on**" (GrQie6z).

**Astra's form.** No words. A dict or `DictReader` join on the printed key, as in pathway: `follow_up = sorted(set(register) - transferred_out - valid_learners)`. In deck it is stated as a fact: "N8 concerns the momentum slide, while N9 concerns the closing slide, so both remain standing" (AP2Ghw4).

**Trap designs that use it.** TWIN keying slips (`governing_vs_filing_key`, `identity_variants_twins`) and ACTUAL delivery and stock traps, where the slipped row fits its key and the true owner is identified only by remarks from other parties.

**How to use it genuinely.**
- No sentence anywhere may give the key or record priority. The audits withdrew traps where one did:
  - psychopathy's "the log decides";
  - ktp's "the class journal records each lesson";
  - cafe 2.1.0's clause 2.2, "drawings govern".
- Give at least two anchors from two parties.
- Make the keyed reading contradict a fact under every reading. Examples:
  - a learner who transferred out three days before collection has a slip;
  - the brief mentions a frame fitted after its logged date;
  - the reason clause in the letter names a drawing whose licence was renewed.

**Genuine vs unfair.**
- **Genuine** (blind reader 1.0, model misses): pathway P2, kibo P3, timesheet P4, home-bp P3, suitcase P5, ats P2, cnc P3, cafe P1/P6 (second reader), coloring 2.3.0 (with the wing clause), gst P1/P4, deck P2.
- **Unfair**:
  - coloring 2.2.0: log against handoff with nothing to decide between them;
  - probation: the column's provenance was unstated and rule 5.2 deferred to it;
  - feast: a later dated note supported the printed label.
- **The pattern.** The trap is unfair when the record has a sentence that blesses it, or when the contradicting fact does not exclude the record's reading.

**Strength.**
- **Astra** shows L1 at full strength and silently. It is the largest single block of Astra's misses.
- **Fable** shows it at about the same miss rate, but notices the conflict roughly half the time. Its failures here sit one decision away from correct.

---

### L2. Two anomalies reported separately, never joined (orphan plus missing)

**Definition.** The model spots both halves of a mis-keying: a record that should not exist under its key, and a record that is missing under the right key. It reports each as its own follow-up and never infers that they are one record filed under the wrong key.

**Frequency.** Fable only. On pathway P2:
- 19 of 19 failing runs (2.0.0, 2.3.0, 2.4.0) state that Kamau transferred out;
- at least 15 of 19 also state that Halima's slip was handed in but has no row;
- 0 connect S13 to Halima.

Other single instances:
- kibo WD28P3w: "the Japanese foil Kessig Wolf Run the shop asked about **did not appear on Monday's export**";
- home-bp wGvLwUz: "stayed overnight in Klin … with the monitor at home, **yet an evening reading is recorded for that date** … I kept it as recorded. You may want to ask him";
- coloring 7V4eot9: "it may be the wrong design. That does not affect this margin audit".

Astra: 0 voiced.

**Quote.** From the same pathway message (7qhybBr):
- "S13: Kamau transferred out on 5 Oct, and the combination is from the STEM list, not his pathway."
- "Halima (no slip in the export despite handing one in) … Halima's slip is reported handed in but is missing from the export, so it may need keying rather than a fresh slip."

**Passing route.** Pathway 2.3.0, 5aArzNy: "It is keyed to Isaac Kamau, whose transfer out went through on Monday 5 October, **three days before slips were collected** … the slip is the Aviation combination **keyed in register order right after Gideon's. I treated it as Halima's slip mis-keyed one learner ID along**."

What the passing runs do:
1. They date the orphan against the event, which turns it into an impossibility.
2. They give a mechanism for the error.
3. They add a content match ("wants to fly").

**How to use it genuinely.** Leave both anomalies visible, so a careful reader sees two loose ends. Keep the identifying remark a by-the-way line. Do not hand over the mechanism. The blind reader solved pathway 2.0.0 and 2.3.0 at 1.0.

**Strength.** Strong on Fable: 100% of pathway failures. Absent on Astra, which never voices either half.

---

### L3. Rule shield: a real rule cited against evidence it does not cover (mostly Fable)

**Definition.** The model frames the anchor as a request the governing rule forbids, or as evidence of a kind the rule ranks low, and dismisses it. Meanwhile the anchor actually bears on another variable: the date of the row, the tax base, the unit, the price basis, or ownership.

**Frequency.** Fable cites a rule or governing document in 50 of its 142 C/C\* runs. By premise:

| premise | Fable | Astra | the rule cited |
|---|---|---|---|
| home-bp P3 | C\* 6 of 17 misses | 0 | §3.2, "notes are not grounds" |
| gst P3 | 8 of 16 misses | — | note 1, "printed rate governs" |
| profile P7 | about 5 of 10 | — | method 2.1, "not evidence" |
| home-bp P5 | 10 of 10 drop day 1 as the printed form's practice row; 4 say outright that the form is binding | — | "the protocol makes the form's printed instructions binding" |
| suitcase P7 | 8 of 10 voiced | — | "contradicts the passport, so I ignored that" / "not a matrix SKU" |
| ats P2 | 5 of 15 | — | an invented rule: "the guide builds the register from the ATS roles only", "the register counts the roles the applicant actually declared" |

Astra: 0 voiced citations. Its nearest equivalent is the abstention in L6.

**Quotes.**
- home-bp P3: "The 3 September 'surgery' and 'upset' sessions, and the late 28 August morning after the train from Klin, stay in. **Section 3.2 does not allow leaving a reading out for notes or circumstances.**" (wGvLwUz)
- gst P3: "Mr. Sayyed's remark that the GST rise on bags was not passed on is **irrelevant to the key. The printed rates govern**" (U4H99ir). The remark is evidence that the bill is tax-inclusive, not that the rate changed.
- profile P7: "The export has no unit marker and **the house method treats emails and call notes as non-evidence, so I used the export as written**" (6PVgzQX). Also "two secondhand mentions … **I took the export at face value, as the method requires**" (BzCLdt7).
- suitcase P7: "The store letter and protocol call 1 690 and 1 790 covers 'mid', **which contradicts the passport, so I ignored that**" (Lo5igSR).
- home-bp P5: "Day 1 left out. The D-14 form marks day 1 (23 August) as a practice day … **the protocol makes the form's printed instructions part of itself.**" (48wiz4X)

**The genuine line.** This is where blind readers split.
- **When the rule really covers the case, the trap is ambiguous or unfair, and the blind reader misses too:**
  - home-bp P5: a printed current form;
  - suitcase P7: one figure outside the population in a non-governing document;
  - profile 2.2/2.3 P7: before method 2.1/2.2 were scoped;
  - cafe 2.1.0 P10: clause 2.2;
  - brightwater, council and melody.
- **When the rule has been scoped away from the trapped variable, the citation becomes a misreading the audit can show, and the trap is genuine:**
  - profile 2.4.0 scoped method 2.1/2.2 to rates and shares;
  - cafe 2.1.1 scoped clause 2.2 to quoted sizes;
  - home-bp §3.2 is about notes, not about re-dating a row;
  - gst note 1 is about the rate, not the base.
- **Recipe:** keep a rule that looks as if it applies, scope it explicitly so that it does not, and put the anchor on the other variable.

**Strength.** Strong on Fable. Its long reports cite clauses on almost every decision; 130 of 310 step-runs contain a section, rule or clause citation. The loophole is not observable on Astra.

---

### L4. Default numeric convention: half-up rounding, per-piece price, the floor of a rule

**Definition.** For an open numeric rule ("one decimal place", "whole rupees", "the price list", "cannot sit lower than"), the model applies the textbook default and never derives the convention from the worked figures. A variant default-unit form treats bare figures as counts, prices as tax-exclusive, and a matrix price as the band basis.

**Frequency** (class D, plus C where both conventions were computed):
- **Fable: 60 D, plus 6 C on exemplar premises** (deck P4 3, cafe P11 2, suitcase P2 1). The suitcase P7 and profile P7 C runs are counted under L3.
  - cnc P4 (pair pricing): 20 of 20 D;
  - profile P5: 10 of 10;
  - suitcase P2: 8;
  - deck P4: 6 D and 3 C;
  - home-bp P4: 4;
  - cafe P11: 4 D and 2 C ("DS-1 is built at 87, the lowest the client's 'as far as possible' allows");
  - profile P7: 3 D;
  - gst P3: 2 D;
  - suitcase P7: 2 D.
- **Astra: 47 D.**
  - cnc P4: 16;
  - deck P4: 13;
  - profile P5: 10;
  - gst P2 (per-line paise drop): 8.

**Quotes.**
- Silent `Decimal.quantize(..., ROUND_HALF_UP)` or `round(...)` appears in 20 of 20 profile P5 runs; the worked figures 41.8 and 43.9 are never mentioned.
- **Convention propagation** (home-bp P4, ByZ6VpY): `gap = int(rhu(office_sys - bsys, '1'))`. The half-up helper was validated against the session-mean exemplars and then reused for the white-coat gap, whose own exemplar truncates.
- **Audit-object anchoring** (deck P4, Fable). 3 of 7 failing runs printed both `ROUND_DOWN` and `ROUND_HALF_UP` and still chose half-up. 6 of 7 accepted the deck's printed S-02 "105.8%" as "correct from the product position table" (aVZKxzq) while writing 88.9 for S-03. The deck's own titles act as a competing set of examples.

**Passing route.**
- Astra, deck 2.5.0: "**The standard's examples consistently truncate** percentages to one decimal place" (MYsaFPj).
- Fable, deck 2.3.0: "the standard's own examples (19.975% shown as 19.9%, −2.467% shown as 2.4%) imply truncation" (qL8GH7h).
- Astra, cnc 2.6.1: "the receipt records show bearings and shaft supports supplied two pieces per ordered unit" (LJohPgv).

**Dial evidence** (measured):
- deck: 2 worked figures gave misses of Fable 7 of 10 and Astra 10 of 10; 4 figures gave Fable 2 of 10 and Astra 3 of 10.
- profile P5: one added worked figure took Astra from 10 of 10 to 0 of 5 (genuineness log).
- cnc P4: 3 or 4 filed lists moved neither model. Changing the kind of evidence (a receipt line, "Diterima … 4 bearing, 4 dudukan as") moved Astra to 4 of 10 passes and left Fable at 0 of 10.

**The genuine line.**
- **Genuine:** the worked figures sit in the governing standard or in the same office's current filed records, and only one convention reproduces all of them.
- **Unfair:**
  - eco-guard: the exemplars were from another year or module;
  - brightwater: the "within" examples sat outside the governed text;
  - suitcase P7: the basis showed only in a catalogue item outside the matrix.

**Strength.** Similar overall. Astra's quantity semantics are better: it solves cnc P4 (4 of 10), profile P7 (10 of 10), gst P3 (20 of 20) and cnc P5 (10 of 10), where Fable misses 20 of 20, 10 of 10, 16 of 20 and 6 of 10. Astra is weaker on rounding exemplars: gst P2 8 of 10 misses against Fable 0 of 20, and deck P4 13 of 20 against Fable 9 of 20. Profile P5 bites both models 10 of 10.

---

### L5. Absorption and satisficing: the anchor is made to fit the default answer

**Definition.** Instead of letting the anchor overturn the answer, the model finds a way for the default answer to accommodate it, and then stops. It does this in three ways:
- attaching the remark to an existing record that is correctly keyed;
- treating the anchor as a constraint the default already satisfies;
- noting that the draft under audit "checks out" under the default.

**Frequency.** Mostly Fable.
- **ats P2:** 8 of 10 Fable runs say the referral "matches **Imran Shaikh's Lumen Wireless record already in the ATS**", which is the printed owner (5Xs9BjQ, JZyhr64). In ats 1.4.0 a run keeps the slip on both people because "the reference check confirms his ATS entry" (XBQ2kYz). That reference check was itself filed under the slipped ID, so the corroboration is circular.
- **gst P1:** 6 of 6 Fable 1.4.1 fails: "it was consigned to Vidyadeep, not Excel Coaching Classes, so S-106 stays intra-state" (GrQie6z). Astra 7.0: "the bus-parcel message is from a different customer than S-106".
- **cafe P10:** 10 of 17 Fable fails: "SH-2 at 140 **still leaves the half metre the chilled counter's lid needs**" (PehFviD, jFdR65p). The lid remark is the identity evidence, and it was spent as a constraint check.
- **profile P6/P7:** 10 of 10 and 8 of 10 Fable fails conclude the claim holds: "Twelve Podwave … plus twenty-one Corner Seat videos … make 33 episodes … so '350,000+ across 33 episodes' is supportable" (6PVgzQX). Also: "I took the export at face value … **and that reading is also the one consistent with the copy's own 350,000+ figure**" (BzCLdt7).

**Trap designs that use it.**
- The "misread is complete and consistent" design in every traps.json: a TWIN whose wrong key fits.
- Premises whose default reproduces the draft's figure.
- An anchor that is also a satisfiable constraint.

**How to use it genuinely.**
- Make the anchor unable to fit the default under any reading. For example, the lid clearance should fail at 140, or the remark should name an attribute only the true owner has ("squared-paper books": only S-106 has graph books).
- Keep at least one anchor that is a constraint and one that identifies, so a careful reader cannot satisfy both with the default.

**Strength.** Strong on Fable, and probably what lies behind much of its B0. Astra shows it only in the gst abstentions.

---

### L6. Demanding an explicit statement before inferring (evidence threshold), with abstention as Astra's escape

**Definition.** The model refuses to infer from converging incidental anchors and wants a sentence that states the fact. Fable keeps the record and flags the issue. Astra uses an allowed escape value.

**Frequency.**
- **Astra:**
  - gst P1: 13 of 20 runs output "not determinable", for example "the bus-parcel evidence does not clearly identify Excel's order" (YLsDL4v);
  - gst P4: 1;
  - ats P2: 2, "the unnamed referral doesn't establish an additional role clearly enough to add it" (kvuREsR).
- **Fable:**
  - cnc P5: 1 voiced and 5 silent, "Nothing in the record states he bought it, and his 9 October budget message still counts the kit … so I kept KIT-ESP4" (tVhCmYW);
  - profile P7: "hearsay";
  - suitcase P5: "no file records a change to that article";
  - 1 abstention (gst 1.7.0).

**How to use it genuinely.** When "not determinable" is a legal value, the trap must make determinability itself derivable from at least two anchors. This was the case after the gst 1.4.0 fix; the audit called P1 "GENUINE-soft", the hole Astra escapes through. Otherwise the abstention is defensible, as audit 1.3.0 judged for S-101 and S-103.

**Strength.** Strong on Astra wherever an abstention value exists. Moderate on Fable, where it hides under L1.

---

### L7. Additive union: no conservation check

**Definition.** The model accepts both readings and credits both, without checking that the count or ownership is conserved. The new owner gets the item and the printed owner keeps it.

**Frequency.**
- **Astra: 15.**
  - cnc 2.3.0 P3: 10 of 10. "The workshop has enough couplers and motor cables" (UQJx7fA). The storekeeper's count of 6 = 2 + 4 cannot hold 2 + 4 + 4.
  - ats P2: 5 of 10. 30 months are added to Arjun while Imran keeps them: `additional_relevant_months = {'C-306': 30}` (6nfBt3g).
- **Fable: 4**, all ats. "Lumen stays on C-304 too, since the reference check confirms his ATS entry" (XBQ2kYz). "C-304's own Lumen row is kept, since the ATS and the reference check both support it" (f4guxpp).

**Trap designs that use it.** TWINs graded on both sides. ats grades `c_slip_printed` and `c_slip_owner` separately, and the *removal* side is missed 10 of 10 by both models while the *credit* side is missed by Fable 9 and Astra 5. Also stock traps with a stated count.

**How to use it genuinely.** Include a total, count or capacity that the union breaks: "isinya 6 biji", or one role per period in guide 2.1. Grade the removal side.

**Strength.** Astra-leaning. Fable does it only after it has decided the new owner is right.

---

### L8. Scope bleed: helpful over-inclusion (Astra, a non-premise failure)

coloring 2.3.0 steps 2–3: in 10 of 10 Astra runs, `pages_to_regenerate` includes 5, 19 and 49: "title updates on pages 1, 2, 3, and 61, **plus margin fixes on pages 5, 19, and 49**" (EyWzXgU). The field is defined as pages exported "for the new title".

Fable excluded them explicitly: "Pages 5, 19 and 49 have margin problems only and are excluded" (NBrg5cB).

This is real, but it is a field-scope misreading rather than an evidence trap. A trap built on it would be a definitional or ambiguity lever and should be disclosed as such.

---

### L9. Folder and date triage in multi-step tasks (Astra: the only partial reading)

In step 1 of cafe, Astra read **only** the correspondence dated on or before the step's date (`2026-09-07_fabricator_tops.md`, 10 of 10 runs). It skipped the seven later letters.

In step 1 of coloring, 2 runs never opened `correspondence/`. Those are the only class-A failures in the corpus: the client's "the one with the bird" form was never read.

Fable reads every file in every step: `cat`, `cat -A` (to expose hidden characters), `nl`, and `wc` for sizing.

**How to use it.** For Astra, an anchor in a folder or file that looks irrelevant to the current step, or is dated after it, is at risk of never being read. That is not a genuine reasoning trap. Keep step-relevant anchors in files dated on or before the step.

---

## 4. Passing routes: what the successful runs did

| premise | flip rate | the passing run's move |
|---|---|---|
| pathway P2 | Fable 0/10 → 3/10 → 3/5 | Dates the orphan ("transfer … three days before slips were collected"), gives a mechanism ("one learner ID along" in register order) and a content match ("wants to fly", the Aviation combination) |
| cafe P1/P6 | Fable 0/20 → 5/10 | Three temporal anchors including the act itself ("saw the owner recording the voice note at the new window on Thursday 09-03"), then "that entry **cannot be right**", then a mechanism ("the log's two kitchen-brief entries … swapped job numbers") |
| deck P2 | Fable 19/20 | A mechanism ("the closing slide sits at page 25, so the filing looks like a page-number slip") plus two remarks (CFO "happy with where it sits"; "three messages") |
| kibo P3 | Astra 2/10 | Demotes the key by its provenance: "Export names are account labels" (`prices/README_export.md`, "as entered on the account's list"); then `assert len(japanese_foils) == 1` |
| home-bp P3 | Astra 3/10 | A gap plus an impossibility: "The overnight trip rules out 27 August evening at home; the otherwise missing 26 August evening fits the recorded immediate post-ski session" |
| suitcase P5 | Fable 1/10 | Re-reads the letter's reason clause against the licence table: "the lighthouse licence is renewed, so I read the swap as applying to the Ретро-марки SKU ЧХ-30149" |
| coloring P2 | Fable 12/20, Astra 5/10 | A unique conjunction: "Only D28 has both a shop sign and a bird" (and still a hedge: "If the art log turns out to be right, pages 37 and 61 swap status") |
| timesheet P4 | Fable 9/25 | A two-hop chain restated through the handbook rule: print room → "the decimals lesson" → video list → Lesson 2; "Handbook 2.2 books a block to the task whose work was done" |
| profile P6/P7 | Astra 20/20 | Overrides the printed attribute: "February's cellar film is the commissioned Remparts reopening film, **despite its playlist**. Podwave's units are thousands, corroborated independently by the fermentation and circadian-neuroscience episode references" |
| gst P3 | Astra 20/20 | "Deccan Bags' three printed values are the entire amount payable"; `denominator = 100 + rate` |
| cnc P5 | Astra 10/10, Fable 4/10 | "On 10 October Bayu borrowed the multimeter to set Vref on four axes, and Wawan's phone connected to Bayu's FluidNC network … already in his hands, so rule 1.7 applies" |

**Common features of the passes.**
1. An impossibility, not a likelihood.
2. A mechanism for the error.
3. A unique match on content.
4. A third anchor that witnesses the event in question.

When none of these is present, the "record" wins.

**Traps that died, for contrast** (Fable round-2 pilots, 0 misses each in 5 runs): kibo P5 (commander already owned), ats P5 (Kodexa is a course), timesheet P5 (26th–25th payroll), pathway P4/P5 (Wycliffe left; slip timing). All of these *fill a gap or narrow a scope*; none overrides a record.
- Fable on kibo: "Since Kibo is Tiago's own prerelease pull, it stays in the cost total but is excluded from the ceiling".
- Fable on pathway: "Wycliffe's kit came back with this term's leavers".

**Fable infers freely; it will not overrule a record.**

---

## 5. Systematic Fable vs Astra differences

| dimension | Fable 5.1 (Claude Code) | GPT-6 Astra (Codex) |
|---|---|---|
| Visible text | Long reports (about 2.6k message characters per step-run); 60% of step-runs carry a flag; 18% carry an "If X, then Y" alternative | Terse (about 0.6k characters per step-run); 0 flags; 0 conditional alternatives; reasons live in code comments |
| Main failure shape | Notices and overrules (C/C\* 43%); flags it and commits to the record | Silent join or default (B0 + D 83%) |
| Conflict outcome when noticed | Keeps the record and writes a hedge ("If that row is actually a mislabeled Kessig Wolf Run, Cinder Glade would move to 1.30 USD") | Union (credits both) or abstains ("not determinable") |
| Rule citation | Heavy (L3); sometimes invents a rule (ats "ATS roles only") | Cites rules for conventions ("The guide and signed register establish…"), rarely to dismiss evidence |
| Stronger at | Mechanism-backed identity slips (deck P2 19/20, pathway with a content cue, coloring), rounding exemplars (gst P2 20/20) | Quantity semantics and attribute overrides inside a record (profile P6/P7, gst P3, cnc P5, cnc 2.6.1 P3, cnc P4 4/10) |
| Weaker at | Units, tax base, pairs (passes: profile P7 0/10, gst P3 4/20, cnc P4 0/20), and in-hand inference (cnc P5 4/10) | Cross-document identity chains with by-the-way remarks (pathway, timesheet, deck P2, cafe P1/P6, all 0/10); rounding exemplars with two figures |
| Reading | Reads everything in every step (`cat -A`, `nl`) | Reads everything in single-step tasks; triages by folder and date in step 1 of multi-step tasks (2 class-A misses) |
| Response to dials | Moves on extra converging anchors that witness the event; does not move on extra filed lists | Flips all-or-nothing on figure count (deck P4, profile P5); moves on a change in the *kind* of evidence (receipt line) |

---

## 6. Partial reading

- **No evidence that partial reading causes the trap failures.** Anchors were present in the tool output in 519 of 521 failing premise-runs, and were read before the first deliverable write in 521 of 521.
- **Fable:**
  - `cat` (often `cat -A`) on all files in every step-run;
  - `head` in 85 of 310 step-runs (CSV previews before Python parsing);
  - `grep` in 10.
- **Astra:**
  - `rg --files` to list, then `cat` or a Python `read_text` dump of whole files;
  - `rg -n` targeted search in 3 of 80 sampled step-runs;
  - no `sed -n` windows.
- **The exception** is Astra's step-1 triage in multi-step tasks (L9). In coloring 2.3.0, step 1 skipped correspondence or research in some runs, and 2 runs missed the deciding contact form. In cafe 2.1.1, step 1 read only the letter dated before the step.

---

## 7. Implications for trap design (ranked)

1. **Use L1, and design so the model has to *reverse* a record, not *fill* a gap.**
   - Use two or more anchors from two parties.
   - Remove any sentence that gives the record priority.
   - Make the keyed reading impossible rather than unlikely.
   - Withhold the mechanism, such as a visible transposition.
2. **Grade the removal side and include a conserved total** (L7). This catches Astra's union, and Fable's "keep it on both".
3. **Plant a rule that seems to apply, then scope it away from the trapped variable** (L3). Fable will cite it; the audit can show the citation is a misreading.
4. **Pair a constraint anchor with an identity anchor that the default answer cannot satisfy** (L5).
5. **For conventions, use exactly two worked figures,** both in the governing document or the same office's current filed records, each illustrating another rule (L4). Do not add a third, which flips Astra, and do not use figures outside the population, which the blind reader rejects.
6. **Never rely on**:
   - a printed current form or table that states the opposite (home-bp P5, suitcase P7: the blind reader also misses);
   - an anchor Astra might skip by folder or date (L9);
   - an abstention value without determinability anchors (L6).

---

## Appendix A: per-premise failure classes (failing runs / attempts)

Finals have 10 attempts per model; pilots have 5. "void" means the Astra campaign was voided by the 10-13 auth failure. For gst 1.7.0, the cnc 2.6.1 P3 Astra pass and the profile P6/P7 Astra passes, see §4.

| task | version | premise | mechanism | Fable fails | Astra fails |
|---|---|---|---|---|---|
| ats | 1.1.0 final | P2 | TWIN | 10: C\*2 C7 F-union1 | 10: B0 3, C\*2, F-union5 |
| ats | 1.4.0 pilot | P2 | TWIN | 5: C2 F-union3 | void |
| cafe | 2.1.1 final | P1 | TWIN | 10: B0 8, B1 2 | 10: B0 10 |
| cafe | 2.1.1 final | P6 | TWIN | 10: B0 9, B1 1 | 10: B0 10 |
| cafe | 2.1.1 final | P10 | TWIN | 10: B0 4, B1 1, C\*1, C4 | 9: B0 9 |
| cafe | 2.1.1 final | P11 | EXEMPLAR | 2: C1 D1 | 0 |
| cafe | 2.1.1 final | P8 | ATTR | 2: C2 | 0 |
| cafe | 2.3.0 final | P1 / P6 | TWIN | 5: B0 2, B1 1, C2 / 5: B0 4, C1 | void |
| cafe | 2.3.0 final | P10 / P11 / P5 / P8 | | 7 / 4 / 2 / 2 | void |
| cnc | 2.3.0 final | P3 | TWIN | 10: B0 1, B1 1, C8 | 10: F-union10 |
| cnc | 2.3.0 final | P4 | EXEMPLAR | 10: D10 | 10: D10 |
| cnc | 2.6.1 final | P3 | TWIN | 9: B0 1, B1 1, C7 | 0 |
| cnc | 2.6.1 final | P4 | EXEMPLAR | 10: D10 | 6: D6 |
| cnc | 2.6.1 final | P5 | ACTUAL | 6: B0 5, C1 | 0 |
| coloring | 2.3.0 final | P2 (step 1) | TWIN | 8: B0 1, B1 1, C6 | 5: A2, B0 3 |
| coloring | 2.3.0 final | P5 (step 2) | TWIN | 5: B1 2, C\*1, C2 | 4: B0 4 |
| coloring | 2.3.0 final | P8 (step 3) | TWIN | 6: B0 2, B1 1, C\*3 | 2: B0 2 |
| coloring | 2.5.0 final | P5 | TWIN | 3: C\*1 C2 | void |
| deck | 2.3.0 final | P2 | TWIN | 0 | 10: B0 10 |
| deck | 2.3.0 final | P4 | EXEMPLAR | 7: C2 D5 | 10: D10 |
| deck | 2.5.0 final | P2 | TWIN | 1: B0 1 | 10: B0 10 |
| deck | 2.5.0 final | P4 | EXEMPLAR | 2: C1 D1 | 3: D3 |
| deck | 2.5.0 final | P5 | ATTR | 4: B1 2, C\*1, C1 | 0 |
| gst | 1.4.1 final | P1 | ACTUAL | 6: C6 | 6: F-abstain6 |
| gst | 1.4.1 final | P3 | SCALE | 8: B1 2, C\*4, D2 | 0 |
| gst | 1.4.1 final | P4 | TWIN | 8: B0 1, C7 | 4: B0 3, F-abstain1 |
| gst | 1.7.0 final | P1 | ACTUAL | 1: F-abstain1 | 7: F-abstain7 |
| gst | 1.7.0 final | P2 | EXEMPLAR | 0 | 8: D8 |
| gst | 1.7.0 final | P3 | SCALE | 8: B1 4, C\*4 | 0 |
| gst | 1.7.0 final | P4 | TWIN | 0 | 2: B0 2 |
| home-bp | 2.2.1 final | P3 | TWIN | 10: B0 3, B1 2, C\*4, C1 | 7: B0 7 |
| home-bp | 2.2.1 final | P4 | EXEMPLAR | 2: D2 | 0 |
| home-bp | 2.6.0 / 2.7.0 pilot | P5 | REVISED | 5: B1 3, C\*2 / 5: B1 3, C\*2 | void |
| home-bp | 2.6.0 / 2.7.0 pilot | P3 | TWIN | 2 / 5 | void |
| kibo | 2.3.1 final | P3 | TWIN | 10: B0 6, C4 | 8: B0 8 |
| kibo | 2.7.0 pilot | P3 | TWIN | 5: B0 2, C3 | void |
| pathway | 2.0.0 final | P2 | TWIN | 10: B1 4, C\*6 | 10: B0 10 |
| pathway | 2.3.0 final | P2 | TWIN | 7: B1 3, C\*4 | void |
| pathway | 2.4.0 pilot | P2 | TWIN | 2: B1 1, C\*1 | void |
| profile-copy | 2.4.0 final | P5 | EXEMPLAR | 10: D10 | 10: D10 |
| profile-copy | 2.4.0 final | P6 | TWIN | 10: B0 10 | 0 |
| profile-copy | 2.4.0 final | P7 | SCALE | 10: B1 2, C\*2, C3, D3 | 0 |
| suitcase | 2.1.1 final | P5 | TWIN | 9: B0 2, C\*3, C4 | 9: B0 9 |
| suitcase | 2.1.1 final | P2 | EXEMPLAR | 3: D3 | 0 |
| suitcase | 2.4.0 / 2.5.0 pilot | P7 | SCALE | 5: C4 D1 / 5: C4 D1 | void |
| suitcase | 2.4.0 / 2.5.0 pilot | P5 / P2 | | 4, 3 / 2, 3 | void |
| timesheet | 2.2.0 final | P4 | TWIN | 7: B0 6, C1 | 10: B0 10 |
| timesheet | 2.4.0 final / 2.6.0 pilot | P4 | TWIN | 4: B0 4 / 5: B0 5 | void |

## Appendix B: reproduction

The scripts are in this session's scratchpad (`…/scratchpad/traj/`) and are not persisted to the workspace.
- `lib.py`: unified event loader for both models; normalized 6-word "seen" test; windows.
- `prem.py`: per-premise windows with seen flags and check reasons.
- `count.py`: regex voicing per run.
- `classify.py`: the A–F classification.
- `reasons.py`: tags for the stated reasons.
- `order.py`: whether anchors were read before the deliverable was written.
- `coverage.py`: reading coverage.
- `ifalt2.py`: hedged alternatives.

Genuine/unfair verdicts are cited from `research/batch4/b6/genuineness.md`. Run IDs in quotes are the `package__<id>` suffixes inside each campaign's `jobs/run/`.
