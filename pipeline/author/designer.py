"""Stage F2 -- the pieces of the design stage every author route shares.

The Anthropic transport (`_call`, `_consume_stream`, `CALL_DEADLINE_S`), the
spec tool schema, the category guidance, step naming, and the checks that the
authored reference solution actually satisfies the grader (`derive_solution`,
`verify_solution`). The designing itself is `agent_designer`, which inspects the
full evidence index; the one-shot, single-call designer that used to live here
was reachable only with ARENA_AGENT_DESIGN=0 and an extraction production never
produces, and was deleted. `design` remains as the name the batch passes around.

Everything a design can get wrong is caught by a gate rather than trusted: an
unpublished rule fails `contract.completeness`, a hand-typed target fails
`grader.oracle`, an ungrounded trap fails `trap.faithful`, and a stored answer
fails `answer.derivation`.
"""

from __future__ import annotations

import json
import http.client
import os
import re
from collections import Counter
import time
import urllib.error
import urllib.request
from ..provider import request_slot, _http_failure, _retry_delay, _transport_observer
from pathlib import Path
from typing import Any

from . import oracle
from .checks import Workspace, evaluate
from ..gates.integrity import _typed_literals
from ..config import ARENA_MODEL
from ..credential import auth_headers as _shared_auth_headers

API_URL = "https://api.anthropic.com/v1/messages"
MODEL = os.environ.get("ARENA_DESIGNER_MODEL", ARENA_MODEL)

SPEC_TOOL = {
    "name": "design",
    "description": "Emit the environment specification.",
    "input_schema": {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "description": {"type": "string"},
            "category": {"type": "string"},
            "intent": {"type": "string"},
            "keywords": {"type": "array", "items": {"type": "string"}},
            "difficulty": {"type": "string",
                           "description": "Explain the distinct professional decisions and "
                                          "hypothesized reasoning demands. Do not claim measured difficulty."},
            "novelty": {"type": "string",
                        "description": "One sentence: what does this ask that a "
                                       "re-skin of an existing task would not?"},
            "projections": {
                "type": "array",
                "description": "Ordered. A parse projection reads one fixture "
                               "file; a join or stem_overlap reads projections "
                               "declared earlier in this list.",
                "items": {
                    "type": "object",
                    "properties": {
                        "as": {"type": "string",
                               "description": "REQUIRED. Name of the projection, "
                                              "ending .jsonl. Target expressions "
                                              "read this name as their `file`."},
                        "op": {"type": "string", "enum": ["parse", "join",
                                                          "stem_overlap", "concat"],
                               "description": "Defaults to parse."},
                        "file": {"type": "string",
                                 "description": "parse only: the fixture file."},
                        "parser": {"type": "string",
                                   "description": "parse only: a registry name."},
                        "left": {"type": "string"}, "right": {"type": "string"},
                        "on": {"type": "string"},
                        "fields": {"type": "object",
                                   "description": "join only: alias -> "
                                                  "'left.field' or 'right.field'."},
                        "compute": {"type": "array", "items": {"type": "object"},
                                    "description": "join only: derived booleans, "
                                                   "each {field, kind, fields} "
                                                   "with kind all_true | equal | "
                                                   "both_resolved_and_equal "
                                                   "(+guard)."},
                        "paper": {"type": "string"},
                        "sources": {"type": "object",
                                    "description": "stem_overlap only: projection "
                                                   "name -> fixture filename."},
                    },
                    "required": ["as"],
                },
            },
            "instruction": {"type": "string"},
            "deliverable_file": {"type": "string"},
            "checks": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "kind": {"type": "string",
                                 "enum": ["objective", "guardrail"]},
                        "weight": {"type": "number", "description":
                    "Share of the task's 100 points. Weight is an argument about "
                    "importance, so it must be defensible from the seed, not "
                    "assigned by feel. Rank the checks by what the practitioner "
                    "in the trace actually cared about, then size them: a "
                    "judgement the user explicitly corrected outranks one they "
                    "never mentioned; a conclusion the whole deliverable rests on "
                    "outranks a supporting detail; a check covering twenty rows "
                    "outranks one covering two. Weights must NOT be uniform -- "
                    "equal weights say every check matters equally, which is "
                    "almost never true and is how an incidental detail comes to "
                    "outweigh the answer. Guardrails carry weight 0: they "
                    "protect, they do not score."},
        "weight_basis": {"type": "string", "description":
                    "One sentence justifying THIS weight against the others, "
                    "citing the evidence: the correction it comes from, the share "
                    "of the deliverable it covers, or what breaks downstream if "
                    "it is wrong. 'Important' is not a justification. Required "
                    "for every scored check."},
                        "band": {"type": "string",
                                 "enum": ["floor", "core", "stretch"]},
                        "dimension": {"type": "string"},
                        "basis": {"type": "string",
                                  "description": "Public wording. The instruction "
                                                 "must actually say this."},
                        "assertion": {"type": "string",
                                      "enum": ["equals", "numeric_within",
                                               "set_equals", "multiset_equals", "subset_of",
                                               "superset_of", "contains",
                                               "absent", "present", "matches",
                                               "row_count", "fixture_intact", "optimal_path", "optimal_subset"]},
                        "actual": {"type": "object", "properties": {"op": {"type": "string"}},
                                   "required": ["op"], "description": "Always include op. JSON outputs use {op:'field',file:'answer.json',path:'field_name'}."},
                        "target": {
                            "type": "object",
                            "description":
                                "An EXPRESSION over the projections, recomputed "
                                "from the fixture at grade time -- {op: count|"
                                "pluck|difference|intersection|sum|rows|field, "
                                "...}. The ONE exception is a sentinel the "
                                "instruction fixes (an abstention string, a "
                                "required word), which is {op: literal, value: "
                                "..., why: \"...\"} -- and `why` is MANDATORY "
                                "there, explaining why the value cannot be "
                                "derived from the fixture. A literal without "
                                "`why` is refused: hand-typed expected values "
                                "are how an answer key comes to say 26 when the "
                                "truth is 27."},
                        "requires": {"type": "array", "items": {"type": "string"}},
                        "rule_quote": {"type": "string", "description":
                            "Required when the target filters rows (where) or uses a regex: "
                            "the sentence(s) copied verbatim from this check's step "
                            "instruction that publish the rule the filter applies, "
                            "unless rule_sources witness the rule in accessible fixture documents."},
                        "rule_sources": {"type": "array", "items": {
                            "type": "object", "properties": {
                                "file": {"type": "string"}, "quote": {"type": "string"}},
                            "required": ["file", "quote"], "additionalProperties": False},
                            "description": "Exact public rule sentences in fixture documents "
                                           "available at this check's step; no future-step evidence."},
                        "rule_terms": {"type": "object", "additionalProperties": {"type": "string"},
                            "description": "Fixture token -> the instruction's wording for it, "
                                           "when the instruction names a column or value "
                                           "differently (e.g. a translated header). Published."},
                        "tolerance": {"type": "number"},
                    },
                    "required": ["id", "kind", "weight", "weight_basis", "band",
                                 "dimension", "basis", "assertion", "actual"],
                },
            },
            "traps": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "type": {"type": "string",
                                 "enum": ["misleading_label", "stale_authority",
                                          "unreadable_source", "unsatisfiable",
                                          "forbidden_edit", "scope_creep_bait",
                                          "regression_bait", "plausible_decoy",
                                          "derived_answer"]},
                        "surface": {"type": "string"},
                        "provenance": {"type": "string",
                                       "enum": ["trace_derived", "authored"]},
                        "derived_from": {"type": "string",
                                         "description": "trace_derived: "
                                                        "session::msgN"},
                        "correction_class": {"type": "string", "description": "For every trace_derived trap, classify the cited user correction and preceding assistant action using the correction classes allowed by that trap type. list_corrections.signal is a coarse discovery signal (for example steerability), NOT a correction class. Ground the classification in the quoted exchange."},
                        "quote": {"type": "string",
                                  "description": "trace_derived: the user's words, "
                                                 "verbatim."},
                        "grounding": {"type": "string",
                                      "description": "authored: why a practitioner "
                                                     "here would meet this case."},
                        "grounded_in": {"type": "string",
                                        "description": "authored: a fixture "
                                                       "filename that exists."},
                        "beatable_by": {"type": "string"},
                        "probe": {"type": "string",
                                  "enum": ["plausible_wrong", "destructive",
                                           "answer_lookup"]},
                        "checks": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["id", "type", "surface", "provenance",
                                 "beatable_by", "probe", "checks"],
                },
            },
            "second_step": {"type": "object", "description":
            "OPTIONAL second graded step, over the SAME documents. Include one "
            "only when the seed genuinely supports it. Its purpose is narrow "
            "and specific: step 2 introduces information that was not available "
            "in step 1, and tests whether the decision taken in step 1 survives "
            "it. That is what makes it harder than step 1 rather than merely "
            "longer -- the agent must notice that something it already "
            "concluded is now wrong, and say so. A second step that is just "
            "'more of the same work' is worse than no second step: it doubles "
            "the cost and measures the same thing twice. Do NOT restate step "
            "1's deliverable; the new deliverable records what CHANGED and why.",
            "properties": {
                "instruction": {"type": "string", "description":
                    "The prose for step 2. It must state the new information "
                    "plainly and must not tell the agent what to conclude from "
                    "it."},
                "deliverable_file": {"type": "string", "description":
                    "Where step 2's answer is written. Must differ from step 1's."},
                "new_information": {"type": "string", "description":
                    "One sentence: what step 2 reveals that step 1 could not "
                    "have known, and which earlier decision it puts in doubt."}},
            "required": ["instruction", "deliverable_file", "new_information"]},
        "forged_applicable": {"type": "boolean"},
            "forged_reason": {"type": "string"},
        },
        "required": ["name", "description", "category", "intent", "keywords",
                     "difficulty", "novelty", "projections", "instruction",
                     "deliverable_file", "checks", "traps", "forged_applicable",
                     "forged_reason"],
    },
}


from .contracts import compile_steps, contained

SPEC_TOOL["input_schema"]["properties"].update({
    "outputs": {"type": "array", "items": {"type": "object"},
                "description": "Public JSON output schemas, each {file,step:1 or 2,schema}."},
    "solution": {"type": "object", "description": "Complete reference output values by filename."},
    "quality": {"type": "object", "description": "Evidence, semantic coverage and discrimination cases required by the production contract."},
})
SPEC_TOOL["input_schema"]["required"] += ["outputs", "solution", "quality"]


def _auth_headers() -> dict:
    """Anthropic auth, whichever credential the workspace carries.

    `keys.env` may hold either an API key or an OAuth token, and they are not
    interchangeable: an `sk-ant-...` key goes on `x-api-key`, an OAuth token
    goes on `Authorization: Bearer` and 401s on `x-api-key`. Reading only one
    variable name means a credential swap looks like an outage.
    """
    # Route on the CREDENTIAL, not on which variable happened to hold it. An
    # OAuth token pasted into ANTHROPIC_API_KEY is an ordinary mistake, and
    # keying on the variable name sends it as `x-api-key`, which 401s and reads
    # like an outage rather than a typo. Discriminator adopted from the upstream
    # fork's `anthropic_credential.py`.
    return _shared_auth_headers()


#: Wall-clock ceiling for one model call, however slowly it is arriving. The
#: socket timeout is per-read, so a stream that trickles a byte every few
#: minutes resets it forever and the build sits at 0% CPU with an ESTABLISHED
#: connection. Measured: a-004 spent 70 minutes in one call after streaming was
#: enabled, having already been the task that wedged for 20 before it. A
#: request that cannot finish inside this is not going to.
#: **Unbounded by default** (user, 2026-09-23: "there should not be any turns or
#: time limit"). A wall-clock cap on an authoring call is an artificial limit,
#: not fault detection, and it destroys work rather than protecting anything:
#: measured on this workspace, a fresh build lost 1,578 seconds and 31 completed
#: designer responses to `retry delay exceeds the remaining call deadline` when
#: the provider slowed down. The draft was sound; only the clock had run out.
#:
#: What still protects against a genuine hang is READ_TIMEOUT_S below, which is
#: the right instrument: a socket that has delivered nothing for two minutes is
#: dead, whereas a call that is merely slow is still working. The a-004 incident
#: this deadline was added for -- 70 minutes in one call -- was a *silent*
#: connection, which the per-read timeout catches on its own.
#:
#: Set `ARENA_CALL_DEADLINE_S` to a positive number to reinstate a cap.
_deadline_env = os.environ.get("ARENA_CALL_DEADLINE_S", "").strip()
CALL_DEADLINE_S = float(_deadline_env) if _deadline_env else None

#: Per-read socket timeout. Lower than the deadline on purpose: a server that
#: has sent nothing for this long is not about to, and 300s meant a silent
#: connection burned five minutes per attempt before anything noticed.
READ_TIMEOUT_S = float(os.environ.get("ARENA_READ_TIMEOUT_S", "120"))


class _CallTimeout(TimeoutError):
    """One call exceeded its wall-clock deadline. Retryable."""


class _StreamInterrupted(ConnectionError):
    """A Messages response has no authoritative terminal event."""


def _consume_stream(resp, deadline: float | None = None, progress=None) -> dict:
    """Assemble complete Messages events; no partial response authorizes tools."""
    blocks, partial, closed, data = {}, {}, set(), []
    message, started, seen_delta, events = {}, False, False, 0
    last_progress = time.monotonic()
    for raw in resp:
        if deadline is not None and time.monotonic() > deadline:
            raise _CallTimeout('Anthropic stream exceeded its call deadline')
        try:
            line = raw.decode('utf-8').rstrip('\r\n')
        except UnicodeDecodeError:
            raise RuntimeError('Anthropic stream contained invalid UTF-8') from None
        if line.startswith('data:'):
            data.append(line[5:].lstrip(' '))
            continue
        if line or not data:
            continue
        payload, data = '\n'.join(data), []
        try:
            event = json.loads(payload)
        except ValueError:
            raise RuntimeError('Anthropic stream contained malformed event JSON') from None
        if not isinstance(event, dict):
            raise RuntimeError('Anthropic stream event must be an object')
        kind = event.get('type')
        events += 1
        now = time.monotonic()
        if progress is not None and (events == 1 or now - last_progress >= 10):
            progress('stream-active', events=events)
            last_progress = now
        if kind == 'error':
            error = event.get('error')
            code = error.get('type') if isinstance(error, dict) else None
            if code in {'api_error', 'overloaded_error', 'rate_limit_error'}:
                raise _StreamInterrupted('Anthropic stream reported ' + code)
            raise RuntimeError('Anthropic stream reported a provider error')
        if kind == 'message_start':
            value = event.get('message')
            if started or not isinstance(value, dict) or value.get('content', []) != []:
                raise RuntimeError('Anthropic message_start violates the response contract')
            started, message = True, dict(value)
        elif kind in {'content_block_start', 'content_block_delta', 'content_block_stop'}:
            index = event.get('index')
            if not started or type(index) is not int or not 0 <= index < 4096:
                raise RuntimeError('Anthropic content block has an invalid index or message boundary')
            if kind == 'content_block_start':
                block = event.get('content_block')
                if index in blocks or not isinstance(block, dict) or not isinstance(block.get('type'), str):
                    raise RuntimeError('Anthropic content block start is invalid or duplicated')
                blocks[index], partial[index] = dict(block), []
                continue
            if index not in blocks or index in closed:
                raise RuntimeError('Anthropic delta or stop has no open content block')
            block = blocks[index]
            if kind == 'content_block_delta':
                delta = event.get('delta')
                if not isinstance(delta, dict):
                    raise RuntimeError('Anthropic block delta must be an object')
                delta_type = delta.get('type')
                if delta_type == 'input_json_delta':
                    fragment = delta.get('partial_json')
                    if block['type'] not in {'tool_use', 'server_tool_use'} or not isinstance(fragment, str):
                        raise RuntimeError('Anthropic tool input delta has an invalid contract')
                    partial[index].append(fragment)
                elif delta_type in {'text_delta', 'thinking_delta', 'signature_delta'}:
                    field = {'text_delta': 'text', 'thinking_delta': 'thinking', 'signature_delta': 'signature'}[delta_type]
                    value = delta.get(field)
                    if not isinstance(value, str) or not isinstance(block.get(field, ''), str):
                        raise RuntimeError('Anthropic text or reasoning delta must be a string')
                    block[field] = block.get(field, '') + value
                elif delta_type == 'citations_delta':
                    citation = delta.get('citation')
                    if not isinstance(citation, dict) or not isinstance(block.get('citations', []), list):
                        raise RuntimeError('Anthropic citation delta has an invalid contract')
                    block.setdefault('citations', []).append(citation)
                # Unknown event/delta types remain forward-compatible. They
                # never complete a known block or a message on their own.
            else:
                # A block can close because generation hit its output limit.
                # Only the message terminal tells us whether its JSON must be
                # complete; never execute or accept a block merely on closure.
                closed.add(index)
        elif kind == 'message_delta':
            delta, usage = event.get('delta'), event.get('usage', {})
            if not started or not isinstance(delta, dict) or not isinstance(usage, dict) or 'content' in delta:
                raise RuntimeError('Anthropic message delta has an invalid contract')
            seen_delta = True
            message.update(delta)
            if not isinstance(message.get('usage', {}), dict):
                raise RuntimeError('Anthropic usage must be an object')
            message.setdefault('usage', {}).update(usage)
        elif kind == 'message_stop':
            if (not started or not seen_delta or closed != set(blocks) or set(blocks) != set(range(len(blocks)))
                    or not isinstance(message.get('stop_reason'), str) or not message['stop_reason']):
                raise _StreamInterrupted('Anthropic terminal event arrived before the response was complete')
            content = []
            for index in range(len(blocks)):
                block = blocks[index]
                if block['type'] in {'tool_use', 'server_tool_use'}:
                    if message['stop_reason'] == 'max_tokens':
                        # Discard the entire tool batch, including completed
                        # calls preceding the cutoff. Authoring can request
                        # smaller edits; screening records its terminal limit.
                        continue
                    # A no-argument tool may send an empty delta after its
                    # initial input:{} block. Empty fragments add no input.
                    input_json = ''.join(partial[index])
                    if input_json.strip():
                        try:
                            block['input'] = json.loads(input_json)
                        except json.JSONDecodeError as exc:
                            if progress is not None:
                                reason = message['stop_reason']
                                progress('invalid-tool-input',
                                    status=reason if reason in {'tool_use', 'end_turn', 'pause_turn'} else 'unknown',
                                    characters=sum(map(len, partial[index])),
                                    line=exc.lineno, column=exc.colno)
                            raise RuntimeError('Anthropic tool input did not parse as JSON') from None
                    if (not isinstance(block.get('input'), dict)
                            or not isinstance(block.get('id'), str) or not block['id']
                            or not isinstance(block.get('name'), str) or not block['name']):
                        raise RuntimeError('Anthropic completed tool block has an invalid contract')
                content.append(block)
            message['content'] = content
            ids = [b['id'] for b in message['content'] if b['type'] in {'tool_use', 'server_tool_use'}]
            if len(ids) != len(set(ids)):
                raise RuntimeError('Anthropic response repeated a tool call identifier')
            if progress is not None:
                reason = message['stop_reason']
                status = reason if reason in {'end_turn', 'tool_use', 'max_tokens',
                    'stop_sequence', 'pause_turn', 'refusal', 'model_context_window_exceeded'} else 'unknown'
                progress('terminal', events=events, status=status)
            return message
    raise _StreamInterrupted('Anthropic stream ended without message_stop')

def _call(body: dict, retries: int = 5) -> dict:
    body = {**body, "stream": True}
    data = json.dumps(body).encode()
    last: Exception | None = None
    observe = _transport_observer()
    deadline = (time.monotonic() + CALL_DEADLINE_S
                if CALL_DEADLINE_S is not None else None)

    def left() -> float | None:
        return None if deadline is None else deadline - time.monotonic()

    for attempt in range(retries):
        remaining = left()
        if remaining is not None and remaining <= 0:
            raise _CallTimeout('Anthropic call exceeded its deadline across attempts')
        req = urllib.request.Request(API_URL, data=data, method="POST", headers={
            "anthropic-version": "2023-06-01",
            "content-type": "application/json", **_auth_headers()})
        try:
            observe('request-start', attempt=attempt + 1)
            with request_slot():
                remaining = left()
                if remaining is not None and remaining <= 0:
                    raise _CallTimeout('Anthropic call deadline expired while awaiting admission')
                # The per-read timeout always applies: a socket silent this long
                # is dead. Only the overall cap is optional.
                socket_timeout = (READ_TIMEOUT_S if remaining is None
                                  else min(READ_TIMEOUT_S, remaining))
                with urllib.request.urlopen(req, timeout=socket_timeout) as resp:
                    observe('response-open', attempt=attempt + 1)
                    return _consume_stream(resp, deadline, observe)
        except urllib.error.HTTPError as exc:
            last, delay = _http_failure(exc, attempt)
            observe('http-error', attempt=attempt + 1, status=exc.code, retryable=delay is not None)
            if delay is None:
                raise last from None
        except (urllib.error.URLError, TimeoutError, ConnectionError, http.client.IncompleteRead) as exc:
            last = RuntimeError(f'Anthropic transport interrupted ({type(exc).__name__})')
            delay = _retry_delay(None, attempt)
            observe('transport-interrupted', attempt=attempt + 1)
        if attempt + 1 < retries:
            remaining = left()
            if remaining is not None and delay >= remaining:
                raise _CallTimeout('Anthropic retry delay exceeds the remaining call deadline') from None
            observe('retry-wait', attempt=attempt + 1, delay_s=round(delay, 3))
            time.sleep(delay)
    observe('exhausted', attempts=retries)
    raise RuntimeError(f'designer call failed after {retries} attempts: {last}') from None


#: What each TARGET LEVEL means for the fixture, in the designer's terms. The
#: level is classified from the seed before authoring -- how much workspace
#: survived and how hard the user pushed back (`select/categories.py`) -- and it
#: decides what the task can honestly be built from. Below F2 the fixture is
#: authored, and even there the scenario is not negotiable.
CATEGORY_GUIDANCE = {
    "F3": ("TARGET LEVEL F3 (Replay). The workspace lifted cleanly and the user "
           "pushed back repeatedly. Use the real documents as they are and build "
           "the task around the disputes the trace actually contains. You should "
           "need to invent almost no DOCUMENT content -- additional traps are "
           "still expected, planted on surfaces these documents already contain "
           "and aligned with the trace's scenario."),
    "F2": ("TARGET LEVEL F2 (Scenario). The trace's scenario, failure mode and "
           "grading criteria survive, but the fixture must be rebuilt around them. "
           "If the user pushed back repeatedly while little of the workspace "
           "survived, the DISPUTES are the asset: build the task around them and "
           "assemble the documents they require -- only documents this "
           "practitioner would plausibly have had. If the workspace lifted but the "
           "trace carries little pushback, the DOCUMENTS are the asset: let the "
           "task follow what they actually support, and do not invent a dispute "
           "the trace does not contain; a manufactured argument reads as one."),
    "F1": ("TARGET LEVEL F1 (Pattern). Too little of the workspace survived to "
           "rebuild the scenario, but the user's correction pattern did. You must "
           "AUTHOR the fixture -- expected and legitimate here -- as a world that "
           "reproduces the mistake the user corrected. Ground every document in "
           "the situation this trace describes: same domain, same role, same "
           "artefacts, same conventions. Invent the CONTENT, never the SITUATION."),
    "F0": ("TARGET LEVEL F0 (Inspired). Neither the workspace nor a correction "
           "survived in usable form, so you AUTHOR the whole fixture. This is "
           "legitimate: Arena allows F0 when a concrete source user goal and "
           "the capability needed to complete it are preserved. Cite that "
           "inspiration precisely and exercise the same goal and capability "
           "in the synthetic scenario. Claim F1 or F2 only with the additional "
           "pattern or scenario evidence; no recoverable goal or capability "
           "means Unrelated/F-1, which cannot be delivered."),
}


def _step_name(category: str | None, ordinal: int = 1) -> str:
    """One filesystem-safe path segment for the step directory.

    A category carrying a separator -- `education/exam_prep` is a real one from
    this corpus -- used to be pasted straight into the path, producing
    `steps/01-education/exam_pre/instruction.md`, two levels deep. The gates glob
    `steps/*/instruction.md`, which does not match it, so the instruction became
    invisible to them: `contract.completeness` then blocked the bundle for a
    rule the instruction actually states, and every basis line scored against the
    fixture alone. A path defect read as a contract defect, which is the worst
    shape a finding can have.
    """
    raw = (category or "task").lower()
    clean = "-".join(p for p in "".join(
        c if c.isalnum() else "-" for c in raw).split("-") if p)
    return f"{ordinal:02d}-{clean[:18].strip('-') or 'task'}"


def design(row: dict, extraction, bundle: Path,
           feedback: list[str] | None = None, **options) -> dict:
    """Design with the evidence-inspecting agent designer.

    The one-shot route this used to hold -- a single schema-constrained call
    with a prompt of its own -- was reachable only through a switch and an
    extraction carrying no evidence index, which production never produces.
    It was deleted; this is the designer callable the batch passes, and it
    forwards budget, feedback and resume state unchanged.
    """
    from .agent_designer import design as design_with_evidence
    return design_with_evidence(row, extraction, bundle, feedback=feedback, **options)


def _expression_nodes(expr):
    """Walk executable expression operands, never filenames or explanatory prose."""
    if not isinstance(expr, dict) or "op" not in expr:
        return
    yield expr
    for key in ("of", "a", "b", "then", "else", "date", "days", "start", "end"):
        yield from _expression_nodes(expr.get(key))
    if expr.get("op") in {"derive_rows", "bind_rows", "record"}:
        for value in expr.get("fields", {}).values():
            yield from _expression_nodes(value)


def _target_has_derivation(expr: dict, projections: list[dict]) -> bool:
    derived = {p.get("as") for p in projections if p.get("op") in {"join", "stem_overlap"}}
    for node in _expression_nodes(expr):
        if node["op"] in {"difference", "intersection", "latest", "sum", "add",
                          "subtract", "multiply", "divide", "date_add", "days_between", "compare", "if"}:
            return True
        if node["op"] in {"rows", "filter"} and node.get("where"):
            return True
        if node.get("file") in derived:
            return True
    return False


def _target_reads_headings(expr: dict) -> bool:
    if not isinstance(expr, dict):
        return False
    operation = expr.get("op")
    if operation == "extract":
        pattern = expr.get("pattern", "")
        captures_text = re.search(r"\((?:\.\*|\.\+|\[\^\\n\][*+])\??\)", pattern)
        return bool(captures_text and _target_reads_headings(expr.get("of")))
    if operation == "field":
        return "heading" in re.split(r"[.\[\]]+", expr.get("path", ""))
    if operation == "pluck":
        name = expr.get("field")
        if name == "heading":
            return True
        source = expr.get("of", {})
        while isinstance(source, dict):
            if source.get("op") in {"derive_rows", "bind_rows"} and name in source.get("fields", {}):
                return _target_reads_headings(source["fields"][name])
            if source.get("op") == "select":
                return source.get("fields", {}).get(name) == "heading"
            source = source.get("of")
        return False
    if operation == "select":
        return "heading" in expr.get("fields", {}).values()
    if operation in {"derive_rows", "bind_rows", "record"}:
        return any(_target_reads_headings(value) for value in expr.get("fields", {}).values())
    operands = ("then", "else") if operation == "if" else ("of", "a", "b")
    return any(_target_reads_headings(expr.get(name)) for name in operands)


def verify_solution(spec: dict, bundle: Path) -> list[str]:
    """Grade the derived solution. Anything it fails is a defect in the spec.

    Caught here rather than at the `golden` probe, where it appears as
    `golden-below-one` with no indication of which check or why.
    """
    from .checks import Check, grade
    fixture = bundle / "environment" / "files"
    # This validates a NEW draft against its current inputs. A previous emitted
    # version may still have an older privacy-minimized fixture manifest on disk.
    # Do not overwrite or weaken that version's exported integrity evidence.
    import hashlib
    protected = {}
    for path in sorted(fixture.rglob("*")):
        if path.is_symlink():
            raise ValueError("fixture symlinks are forbidden")
        if path.is_file():
            protected[path.relative_to(fixture).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    draft_manifest = {"files": protected}
    derived_dir = bundle / "authoring" / "draft-derived"
    import shutil
    if derived_dir.exists():
        if derived_dir.is_symlink():
            raise ValueError("draft projections cannot be a symlink")
        shutil.rmtree(derived_dir)
    oracle.write(oracle.project(fixture, spec.get("projections", [])), derived_dir)
    staged = bundle / "authoring" / "solution-check"
    if staged.exists():
        import shutil
        shutil.rmtree(staged)
    staged.mkdir(parents=True)
    for name, content in (spec.get("solution") or {}).items():
        target = contained(staged, name)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content if isinstance(content, str)
                          else json.dumps(content, indent=2, ensure_ascii=False))

    # Evaluate each target on its own first, so a fault is reported WITH the
    # check that caused it. `grade()` raises on the first bad target and the
    # message travels up with no check id attached -- the designer then gets
    # "a literal target must carry a 'why'" and nine checks to guess between,
    # which is why a010 burned four whole design attempts on one missing field.
    # A repair loop that cannot locate the fault cannot repair it.
    from .oracle import project as _project
    probe_ws = Workspace(source=fixture, submitted=fixture, derived=derived_dir)
    target_errors = []
    for c in spec["checks"]:
        if c.get("target") is None:
            continue
        try:
            evaluate(c["target"], probe_ws, "source")
        except Exception as exc:
            # Show the offending expression, not just its check id. Naming the
            # check told the model WHERE to look; pasting the fragment tells it
            # WHAT to change, and the literal-'why' fault alone had burned five
            # design attempts across three bundles because the model was
            # re-emitting the whole spec and guessing at the edit.
            fragment = json.dumps(c["target"], ensure_ascii=False)
            if len(fragment) > 400:
                fragment = fragment[:400] + " ...(truncated)"
            target_errors.append(
                f"check {c['id']!r} target: {exc}\n"
                f"      the offending expression is: {fragment}\n"
                f"      fix THIS expression and change nothing else")
    if target_errors:
        return target_errors

    checks = [Check(**{k: v for k, v in c.items()
                       if k in Check.__dataclass_fields__})
              for c in spec["checks"]]
    try:
        result = grade(checks, Workspace(source=fixture, submitted=staged,
                                         derived=derived_dir,
                                         fixture_manifest=draft_manifest,
                                         projections=spec["projections"],
                                         outputs=spec.get("outputs", [])))
    except Exception as exc:                 # a bad regex, a malformed operand
        return [f"grading the reference solution raised "
                f"{type(exc).__name__}: {exc}"]
    problems = list(result.get("contract_errors", [])) + [f"{cid}: {row.get('reason') or 'failed'}"
                for cid, row in result["checks"].items()
                if not row.get("passed") and not row.get("gated_out")]
    if problems:
        return problems

    # A literal target holding a LIST is an answer key typed in by hand -- the
    # exact defect the whole `target` mechanism exists to prevent, arriving
    # through the one door left open for sentinels. Measured on a005: four
    # checks carrying 64% of the weight were `op: literal` with the answer
    # spelled out and a paragraph of `why` justifying it, and every gate passed
    # because the grader agrees with itself.
    #
    # A sentinel is a scalar the instruction fixes ("NOT_RECORDED"). A set of
    # filenames is never a sentinel: if those four files are the answer, some
    # expression over the projections selects them, and that expression is the
    # check. If none does, the fixture cannot support the question.
    typed = [f"{c['id']} (at {', '.join(_typed_literals(c.get('target')))})"
             for c in spec["checks"] if _typed_literals(c.get("target"))]
    if typed:
        return ["these checks hand-type their answer as a literal list: "
                + ", ".join(typed) +
                ". A literal is for a SCALAR sentinel the instruction fixes, "
                "never for a set. Replace each with an expression over the "
                "projections that selects those members -- difference, "
                "intersection, or rows+where. If no expression can select them, "
                "the fixture does not support the question and the check must "
                "change, not its target."]

    # A heading set the instruction never scopes. Which depths count, whether
    # the document's own title counts, and whether to record the text or the
    # markup are all arbitrary and all defensible either way -- so a model that
    # reads it differently is not wrong, and the task is ambiguous rather than
    # hard. Measured on a007: four checks scored 0 across ten rollouts on
    # submissions that were the reference answer verbatim, differing only by the
    # markdown prefix. Guidance alone did not stop it recurring, so it is a
    # refusal.
    if any(_target_reads_headings(c.get("target") or {}) for c in spec["checks"]
           if c.get("kind") == "objective"):
        prose = "\n".join(step["instruction"] for step in compile_steps(spec)).lower()
        if not any(k in prose for k in ("heading level", "any level", "top-level",
                                        "level heading", "every heading",
                                        "all headings", "h1", "h2", "depth")):
            return ["checks pluck a set of headings or sections, but the "
                    "instruction never states WHICH HEADINGS COUNT. Two careful "
                    "readers then produce different sets and both are "
                    "defensible, which makes the task ambiguous rather than "
                    "hard. Add a scope block to the INSTRUCTION TEXT. This "
                    "wording passed on another bundle -- adapt it to your "
                    "documents, keep all four points, and change nothing else "
                    "about the spec:\n"
                    "        RULES OF SCOPE for every heading or section you "
                    "report:\n"
                    "        - Count ATX headings at every depth -- `#`, `##`, "
                    "`###`, `####` and deeper -- as sections.\n"
                    "        - The document's own top-level title line counts "
                    "as a section like any other.\n"
                    "        - Record each heading as its text alone, with the "
                    "leading `#` marks and the single space after them "
                    "stripped, and no other change to wording, casing or "
                    "punctuation.\n"
                    "        - Compare headings between documents by that "
                    "stripped text, exactly."]

    # Two objectives with the same answer are one objective charged twice. The
    # grader is happy -- both pass together, both fail together -- and the
    # rubric reads as two independent findings. Measured across this batch on
    # a004, a007, a009 and a010: pairs like `open_items` / `closed_by_ruling`
    # resolved to identical sets, so the second check added no constraint and
    # its weight was a duplicate of the first's.
    from .checks import normalise as _norm
    answers: dict[str, tuple] = {}
    twins: list[str] = []
    for check in spec["checks"]:
        if check.get("kind") != "objective":
            continue
        keys = [k for k in (check.get("actual", {}).get("path") or "").split(".") if k]
        cur = (spec.get("solution") or {}).get(check["actual"].get("file"), {})
        try:
            for k in keys:
                cur = cur[k]
        except Exception:
            continue
        if not isinstance(cur, list) or len(cur) < 3:
            continue
        sig = tuple(sorted(str(_norm(v)) for v in cur))
        if sig in answers:
            twins.append(f"{answers[sig]} and {check['id']}")
        else:
            answers[sig] = check["id"]
    if twins:
        return ["these objectives resolve to the SAME answer, so the second "
                "measures nothing the first does not: " + "; ".join(twins) +
                ". Give each check a distinct constraint, or drop one and give "
                "its weight to a check that asks something else."]

    # §0. An answer read from one surface is stored, not derived: full access to
    # the fixture hands it over. Measured on a007, where seven checks carrying
    # 69% of the weight were `pluck headings from one file` and the task still
    # read as hard because the remaining 31% was genuinely difficult.
    # A scalar literal is a SENTINEL the instruction fixes -- "NOT_RECORDED",
    # a required word, a fixed verdict -- and it is the correct shape for an
    # abstention check, which every task here carries exactly one of. It can
    # never be an expression over the projections, because the whole point is
    # that the value is NOT derivable from the fixture. Counting it as a
    # single-surface read-off penalised every bundle 12-16% of its weight for
    # the one check that is doing the hardest thing in the task. It is excluded
    # from the numerator AND the denominator, so the ratio measures what it
    # claims to: of the weight that COULD be derived, how much actually is.
    #
    # List-valued literals are a different animal and are refused outright
    # further up -- those are hand-typed answer keys, not sentinels.
    def _is_sentinel(check: dict) -> bool:
        target = check.get("target") or {}
        return (target.get("op") == "literal"
                and not isinstance(target.get("value"), (list, dict)))

    derivable = [c for c in spec["checks"]
                 if c.get("kind") == "objective" and not _is_sentinel(c)]
    readoff = [c for c in derivable
               if c.get('assertion') not in ('optimal_path', 'optimal_subset')
               and not _target_has_derivation(c.get("target") or {}, spec.get("projections", []))]
    share = sum(c.get("weight", 0) for c in readoff)
    total = sum(c.get("weight", 0) for c in derivable) or 1
    if share / total >= 0.5:
        return [f"{share / total:.0%} of the objective weight is a single-surface "
                f"read-off ({', '.join(c['id'] for c in readoff)}). A model with "
                "the whole fixture would already have those answers. Build the "
                "majority of the weight from reconciliations, arithmetic or "
                "temporal decisions whose results are written down nowhere."]

    # A null inside the reference answer means the projection produced rows but
    # could not read the field the check plucks -- a parser that does not fit
    # the document. Measured on a004: `report_section_titles` was
    # [None] * 15, because the section parser found 15 headings in a
    # Chinese-language markdown file and read a title from none of them. The
    # task is then unanswerable: no model, and no careful reader, produces a
    # list of nulls. Every rollout scores 0 on it and the zero looks exactly
    # like difficulty, which is the one thing a benchmark must never confuse.
    nulls = []
    from .contracts import schema_at, allows_null
    output_schemas = {item['file']: item['schema'] for item in spec.get('outputs', [])}
    for name, content in (spec.get("solution") or {}).items():
        if not isinstance(content, dict):
            continue
        for field, value in content.items():
            field_schema = schema_at(output_schemas.get(name, {}), field) or {}
            if value is None and not allows_null(field_schema):
                nulls.append(f"{name}.{field} is null")
            elif isinstance(value, list) and allows_null(field_schema.get('items', {})):
                continue  # Explicit typed uncertainty is not a missing projection.
            elif isinstance(value, list) and value and all(v is None for v in value):
                nulls.append(f"{name}.{field} is {len(value)} nulls")
            elif isinstance(value, list) and any(v is None for v in value):
                nulls.append(f"{name}.{field} contains "
                             f"{sum(1 for v in value if v is None)} nulls")
    if nulls:
        return ["the reference answer contains nulls, so the task is "
                "unanswerable as specified: " + "; ".join(nulls) + ". The parser "
                "you chose returns rows for these documents but cannot read the "
                "field being plucked. Choose a parser that fits, pluck a field it "
                "actually emits, or build the answer from a different projection."]

    # A reference answer that is mostly duplicates is a projection plucking the
    # wrong field. Measured on a003: `divergent_colour_tokens` held 250 entries
    # of which 193 were repeats -- `margin`, `padding`, `font-size` -- because
    # the parser had scraped CSS PROPERTY NAMES and the check called them colour
    # tokens. A model that answered correctly (`--bg-main`, `--bg-card`) scored
    # 0 against it. Nothing downstream can tell that apart from a hard task: the
    # grader is self-consistent, golden scores 1.0, and the zero looks earned.
    junk = []
    for name, content in (spec.get("solution") or {}).items():
        if not isinstance(content, dict):
            continue
        for field, value in content.items():
            if isinstance(value, list) and len(value) >= 8:
                counts = Counter(str(v).casefold() for v in value)
                uniq = len(counts)
                if uniq / len(value) < 0.5:
                    junk.append(f"{name}.{field}: {len(value)} entries, only "
                                f"{uniq} distinct")
                    continue
                # One value dominating is the same defect at a different shape,
                # and the distinct ratio cannot see it. Measured on a010:
                # `hud_beat_labels` was 52% distinct -- over the ratio floor --
                # while being the literal word "Setting" fifteen times out of
                # twenty-nine, mixed with art-direction terms the check does not
                # ask about. A label repeated half the time labels nothing.
                top, n = counts.most_common(1)[0]
                if n / len(value) >= 0.25:
                    junk.append(f"{name}.{field}: {top!r} appears {n} times in "
                                f"{len(value)} entries ({n / len(value):.0%})")
    if junk:
        return ["the reference answer is mostly repeats, which means the "
                "projection is plucking a field that does not identify anything: "
                + "; ".join(junk) + ". A set-valued answer must name distinct "
                "things. Pluck a field whose values are unique per row, or "
                "aggregate to the thing the question is actually about."]

    # Degeneracy. A check whose correct answer is an empty collection is earned
    # by an agent that creates the deliverable and writes nothing into it, and
    # no other gate sees this: `seed_zero` omits the deliverable entirely, so
    # every check fails there for the wrong reason. Measured on one design in
    # this batch, four objectives carrying 69% of the weight were empty sets --
    # a task that reads as hard and is mostly free. Caught here because the
    # repair is a redesign of the projections, which is what the designer is
    # holding in its hands right now.
    empty = staged.parent / "empty-check"
    if empty.exists():
        import shutil
        shutil.rmtree(empty)
    empty.mkdir(parents=True)
    for name in (spec.get("solution") or {}):
        target = empty / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("{}\n")
    # Measured with the gate graph REMOVED. A `requires` edge hides degeneracy:
    # an empty-answer check sitting behind a gate is reported `gated_out` and
    # costs nothing, so the probe reads clean -- until Stage 8 calibration finds
    # the gate resting on an unreachable or out-of-band check and ungates it,
    # which is the documented remedy. Then the empty answers become reachable
    # and free, and the task quietly loses a third of its weight. Measured on
    # a001 and a009: both read 0.0 gated, 0.386 and 0.46 once ungated. So the
    # invariant has to hold in the ungated worst case, not just today's graph.
    ungated = [Check(**{k: v for k, v in c.items()
                        if k in Check.__dataclass_fields__ and k != "requires"})
               for c in spec["checks"]]
    try:
        blank = grade(ungated, Workspace(source=fixture, submitted=empty,
                                         derived=derived_dir,
                                         projections=spec["projections"]))
    except Exception as exc:
        return [f"empty-deliverable control could not run: {type(exc).__name__}: {exc}"]
    if blank["reward"] > 0.34:
        # Objectives only. Guardrails assert negative space, so they pass on an
        # empty deliverable BY DESIGN and contribute no weight -- naming them
        # here sends the repair after checks that are behaving correctly, and
        # burns the repair budget that the real defect needs.
        objective_ids = {c["id"] for c in spec["checks"]
                         if c.get("kind") == "objective"}
        free = [cid for cid, row in blank["checks"].items()
                if row.get("passed") and not row.get("gated_out")
                and cid in objective_ids]
        return [f"an EMPTY deliverable already scores {blank['reward']} because "
                f"these objectives have an empty collection as their correct "
                f"answer: {', '.join(free)}. Your projections matched nothing for "
                "them. Reshape the task so each scored set is non-empty in the "
                "fixture -- pick sets the documents actually populate -- or drop "
                "those checks. A task an idle agent half-passes is not a task."]
    if spec.get("outputs") and spec.get("quality"):
        import copy
        import shutil
        import tempfile
        from .build import build
        from ..assurance import controls
        with tempfile.TemporaryDirectory(prefix="arena-design-controls-") as tmp:
            candidate = Path(tmp) / bundle.name
            shutil.copytree(fixture, candidate / "environment/files")
            build(copy.deepcopy(spec), candidate)
            return controls(candidate)["errors"]
    return []


def derive_solution(spec: dict, bundle: Path) -> dict:
    """The authored reference deliverable, after checking the draft projects.

    Production specs carry public outputs and a complete authored reference,
    which `verify_solution` then grades independently. Assembling a reference
    from the checks' own targets -- the one-shot designer's route -- turned a
    partial deliverable into proof of solvability, and is gone.
    """
    fixture = bundle / "environment" / "files"
    rows = oracle.project(fixture, spec["projections"])
    # Draft probes must not rewrite the last emitted grader or its identity.
    derived_dir = bundle / "authoring" / "draft-derived"
    if derived_dir.exists():
        import shutil
        shutil.rmtree(derived_dir)
    oracle.write(rows, derived_dir)
    if not spec.get("outputs"):
        raise ValueError("production specs need public outputs schemas")
    # A complete authored reference is independently checked. Never turn
    # targets into a partial deliverable and call that proof of solvability.
    if not spec.get("solution"):
        raise ValueError("production specs need a complete reference solution")
    return spec["solution"]
