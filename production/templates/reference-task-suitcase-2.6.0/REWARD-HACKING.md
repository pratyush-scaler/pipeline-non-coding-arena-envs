# Reward hacking - a_f1_suitcase-cover-matrix-check 2.6.0 (B6v6, envs-b6/_v6)

All probes executed by `authoring/validate.py` and `research/batch4/fix261011/selftest.py` on `mktemp -d` copies with the
verifier's Python 3.11 (outputs in `authoring/validate_output.txt`, `authoring/selftest_output.txt`).

| probe | result |
|---|---|
| empty workspace (no deliverable) | 0.0, contract error (missing file) |
| forged `reward.json` next to the reference deliverable | 0.0, "undeclared deliverable" |
| FIFO beside the deliverable / the deliverable itself a FIFO | 0.0 both, no hang |
| symlink into the fixture beside the deliverable | 0.0, "undeclared deliverable or symlink (symlink)" |
| fixture tamper (colour table edited in place, answer re-derived from the tampered file) | 0.0: `g_fixture_intact` (sha256 manifest of every fixture byte) zeroes the step |
| deep JSON (5,000 and 100 nested arrays) | 0.0, "nested deeper than 64 levels", no crash |
| 5,000-digit integer, NaN, non-UTF-8 bytes, duplicate keys, Markdown fences | 0.0 each, contract error |
| self-consistent junk subcategory figures with a matching total and share | obj_after_total requires the five subcategories P1 does not touch to match the export, so junk fails obj_after_by_subcategory and obj_after_total. Since 2.1.1 the share check is not gated: a share that is the whole-percent floor of the solver's own counts earns its 17 points whatever those counts are, as the instruction states ('graded against your own ru_skus_after and active_skus_after'). Junk with an own-floor share scores 0.91 on an otherwise correct answer; junk with a share that is not its own floor scores 0.74 (validate section 3) |
| duplicate or case-only duplicate entries in `designs` | 0.0, contract error ("repeated array entries"); selftest dup_case |
| hedged `designs` (both 'Ретро-марки' and 'Воздушные шары', or every print plus the new one) | fails obj_designs: `set_equals` admits no extras (validate section 3) |
| hedged or inverted price split (every printed figure, VAT taken out of every row, every row put on the VAT-inclusive basis, base and mid swapped) | fails obj_price_segments only (validate section 3); the check is an exact record of three counts |
| answer lookup | the reference solution and the grader (`steps/*/solution/`, `tests/`) are excluded from the agent image by `.dockerignore`; the agent image copies only `environment/files/`. checks.json holds expressions, not answers; `tests/derived/` (projections) is verifier-side |
| stored answer in the reference | none: solve.py derives every figure from the fixture; each counterfactual edit (including the swapped licence statuses and the rewritten size examples) flips its output and the grader follows |

Residual: the fixture is readable, so the deck's own figures (60 SKU, 28 designs, 232 before, the label split S 13 / M 23 /
L 19 / XL 5) are visible; the deck's price split is a blank. Copying them loses P5, P6 and the before check. The P1, P2, P5,
P6 and P7 targets are frozen readings of the fixture:
- P1 filters the export by subcategory and supplier country.
- P2 reads the truncation mode from the guide's worked example (the one discriminating figure since 2.6.0).
- P5 maps the licensing sheet's subject column to matrix prints with a literal table.
- P6 reads the three worked size figures at grade time.
- P7 reads the segment bounds from passport section 8, and the supplier and VAT rate from that supplier's letter, at
  grade time; the basis reading (that supplier's matrix figures carry VAT; every other figure is the passport's net
  purchase price) is frozen, like P5's subject table.

An agent cannot reach these targets except by reading the same files. Nothing else was found.
