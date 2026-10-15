# Project instructions

## Calibration types

Apply these standing user preferences, defined on 2026-09-13, whenever a request
mentions Pilot or Complete calibration (case-insensitive):

| Requested calibration | Attempts per model | Launcher setting |
| --- | ---: | --- |
| Pilot | 3 | `ATTEMPTS=3` |
| Complete | 6 | `ATTEMPTS=6` |

Do not ask the user to repeat the attempt count. If no type or count is specified,
preserve the existing default of 6 attempts per model. An explicit count in the
current request takes precedence.

Only the attempt target changes between these types. Keep the concurrency cap at
36 and preserve all other established specifications: models, task, fixture,
grader, native agent, effort, token limits, validated release/image, host resources,
and infrastructure/provider retry and failure-accounting rules, unless the user
explicitly changes them. Pilot is the same calibration with fewer attempts, not
a separate smoke test or a reduced-effort configuration.

The count is the existing campaign target per model, not a required number of
successful passes. Valid low or zero scores count. Retryable infrastructure/provider
failures may cause additional executions within the existing retry budget;
review-required cases retain their reserved sample slot and are not automatically
resampled.

Use the existing launcher's `ATTEMPTS` setting. See [the calibration runbook](env/bench/README.md)
for commands, release requirements, and retry semantics. Check current campaign
state before launching to avoid duplicates. Defining or discussing a type alone
does not request a run.

## Calibration reasoning effort

The standing user preference is maximum native reasoning effort for calibration
(confirmed 2026-09-13). Use `reasoning_effort=max` with the native effort adapter,
verify the value actually sent to each provider, and retain that evidence. Do not
silently fall back to high effort. Earlier high-effort runs remain separate from
max-effort calibration results.

## Calibration documentation and updates

Keep routine updates and prose documentation focused on run settings, execution
state, progress, results, and actionable next steps. Do not repeat historical
incident narratives unless the user explicitly asks for them. Keep original
diagnostics and exact classifications in the raw evidence; report current run
status and result completeness accurately.
