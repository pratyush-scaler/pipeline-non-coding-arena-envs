"""Gates derived one-to-one from Arena's review of the first delivery.

All nine findings they returned on 2026-09-10 were *validation* defects, not
calibration defects: a grader rejecting "1960" because it only accepted numbers,
an answer key saying 26 when the truth was 27, a whitelist of acceptable evidence
that the instruction never published, a rollback that could run before the thing
it depended on had been graded. Not one of them would have shown up as an
anomalous score, so no amount of extra rollouts would have found any of them.
That is the argument for this module: they are caught by reading the bundle, and
so they can be caught automatically.

Mapping, so a future reader can check the claim:

  finding                                   gate
  kw002 rejects the string "1960"           grader.normalisation
  kw003 rollback runs before cleanup graded env.step_isolation
  kw003 key says 26, truth is 27            grader.oracle
  kw003b client demands forbidden fix       env.policy_consistency
  kw006 missing edge-case rule (x2)         contract.completeness
  kw006 ambiguous verdict categories (x2)   contract.ambiguity
  kw006 hidden evidence whitelist           contract.enumeration

Every gate here is a *heuristic over source*, and several can be fooled. Each one
says in its own findings what it cannot see, because the failure mode this
repository keeps repeating is declaring a surface closed and finding another hole
in it later.
"""

from __future__ import annotations

import ast
import json
import re
import tomllib
from pathlib import Path
from typing import Any, Iterable

from .base import Finding, FunctionGate, GateContext, Severity

STOPWORDS = frozenset("""
a an the and or but if then than that this those these is are was were be been being
of in on at to for from with without by as it its into over under no not must may can
each every all any some one two other same only also do does did have has had
""".split())


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def _tokens(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9_]{3,}", (text or "").lower())
            if w not in STOPWORDS}


#: Sentence boundaries: Latin punctuation before a space, or full-width
#: punctuation, which Chinese and Japanese write with no space after it.
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+|(?<=[\u3002\uff01\uff1f])")

#: Scripts written without spaces between words.
_UNSPACED = re.compile(r"[぀-ヿ㐀-䶿一-鿿豈-﫿가-힯]+")


def _content_tokens(text: str) -> set[str]:
    """`_tokens` for any script: words of three or more letters in any alphabet,
    and overlapping character pairs within Chinese, Japanese or Korean runs.

    `_tokens` reads ASCII only, so a basis line written in Chinese or Russian
    had no tokens at all and was reported as "no public wording". The designer
    cannot fix a wording that is present, the finding survived its repair, and
    a-036 (build 2026-09-26) was blocked for it; the ambiguity gates likewise
    called a Russian definition of `vhodit` undefined. ASCII text tokenises
    exactly as before.
    """
    text = (text or "").lower()
    tokens = {w for w in re.findall(r"\w{3,}", _UNSPACED.sub(" ", text)) if w not in STOPWORDS}
    for run in _UNSPACED.findall(text):
        tokens |= {run[i:i + 2] for i in range(len(run) - 1)} if len(run) > 1 else {run}
    return tokens


def _agent_visible_text(ctx: GateContext) -> str:
    """Everything the agent can read, not just the instruction.

    Getting this wrong invalidates two gates at once. The playbook's rule is
    "state the rules the agent could not reasonably discover, push everything
    else into the fixture" -- so a well-built task publishes most of its rules in
    fixture documents (`OUTPUT-CONTRACT.md`, `CONTINUITY-RULES.md`, form
    schemas), and only the arbitrary policy in the prose.

    Reading only `instruction.md` therefore reports a correctly-built task as
    riddled with unpublished rules. Measured on kw-006: the verdict vocabulary
    the ambiguity gate exists to check does not appear in either instruction at
    all -- it lives in the fixture. The agent-visible surface is the union.
    """
    parts: list[str] = []
    for pattern in ("steps/*/instruction.md", "instruction.md",
                    "steps/*/operating-notes.md", "operating-notes.md"):
        for path in sorted(ctx.task_dir.glob(pattern)):
            parts.append(path.read_text(errors="replace"))

    # Fixture documentation: what a competent agent reads before acting. Source
    # material the fixture merely *contains* (data records) is included too --
    # a rule stated in a data file is still stated.
    for root in (ctx.path("environment", "files"), ctx.path("environment", "fixtures")):
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in (
                    ".md", ".txt", ".json", ".csv", ".yaml", ".yml", ".toml"):
                continue
            if path.stat().st_size > 2_000_000:
                continue
            try:
                parts.append(path.read_text(errors="replace"))
            except OSError:
                continue
    return "\n".join(parts)


def _agent_visible_documents(ctx: GateContext) -> dict[str, str]:
    """Same surface as `_agent_visible_text`, kept per file.

    The enumeration gate needs per-document coverage: a set is published when one
    document declares it, not when its members happen to be scattered across a
    corpus.
    """
    out: dict[str, str] = {}
    for pattern in ("steps/*/instruction.md", "instruction.md",
                    "steps/*/operating-notes.md", "operating-notes.md"):
        for path in sorted(ctx.task_dir.glob(pattern)):
            out[str(path)] = path.read_text(errors="replace")
    for root in (ctx.path("environment", "files"), ctx.path("environment", "fixtures")):
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*")):
            if (path.is_file() and path.suffix.lower() in
                    (".md", ".txt", ".json", ".csv", ".yaml", ".yml", ".toml")
                    and path.stat().st_size <= 2_000_000):
                try:
                    out[str(path)] = path.read_text(errors="replace")
                except OSError:
                    continue
    return out


def _basis(ctx: GateContext) -> dict[str, str]:
    path = ctx.path("tests/basis.toml")
    if not path.exists():
        return {}
    with path.open("rb") as fh:
        return (tomllib.load(fh).get("checks") or {})


def _grader_sources(ctx: GateContext) -> list[tuple[Path, str]]:
    # Known shared runtime uses strict types to implement the published schema.
    # Exempt only exact reviewed bytes at the canonical export paths. A filename
    # allowlist would let custom grading code hide behind checks_runtime.py.
    author = Path(__file__).resolve().parents[1] / "author"
    reviewed = {f"_arena_runtime/{target}": (author / source).read_bytes()
                for source, target in (("checks.py", "checks_runtime.py"),
                                       ("contracts.py", "contracts.py"), ("oracle.py", "oracle.py"),
                                       ("path_witness.py", "path_witness.py"),
                                       ("subset_witness.py", "subset_witness.py"))}
    out = []
    for path in sorted(ctx.path("tests").rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        rel = path.relative_to(ctx.path("tests")).as_posix()
        if rel in reviewed and not path.is_symlink() and path.read_bytes() == reviewed[rel]:
            continue
        out.append((path, path.read_text(errors="replace")))
    return out


def _rel(ctx: GateContext, path: Path) -> str:
    try:
        return str(path.relative_to(ctx.task_dir))
    except ValueError:
        return str(path)


# --------------------------------------------------------------------------
# kw006 -- contract completeness: no rule the agent was never told
# --------------------------------------------------------------------------

def _completeness(ctx: GateContext) -> tuple[list[Finding], dict]:
    """Every scored decision must be anchored in what the agent was shown.

    `basis.toml` already exists to carry "public wording for every scored
    decision". Nothing was enforcing that the wording is actually *public* --
    which is precisely how kw006 came to classify D0386 using a page-existence
    rule the instruction never stated.

    The check is lexical and therefore approximate: it asks whether the content
    words of each basis line have support in the instruction. It cannot tell a
    genuinely stated rule from a coincidental word match, so a low score is a
    prompt to read, not a proof of concealment.
    """
    basis = _basis(ctx)
    if not basis:
        return [Finding(Severity.BLOCKER, "no-basis",
                        "tests/basis.toml declares no [checks]; there is nothing to "
                        "trace grader behaviour back to", "tests/basis.toml")], {}

    instruction = _agent_visible_text(ctx)
    if not instruction.strip():
        return [Finding(Severity.BLOCKER, "no-instruction",
                        "nothing agent-visible found (no instruction, no fixture "
                        "documents); scored rules cannot be shown to be published",
                        "steps/*/instruction.md")], {}

    vocab = _content_tokens(instruction)
    findings: list[Finding] = []
    scores: dict[str, float] = {}
    for check, wording in sorted(basis.items()):
        words = _content_tokens(wording)
        if not words:
            findings.append(Finding(Severity.BLOCKER, "empty-basis",
                                    f"check '{check}' has no public wording",
                                    "tests/basis.toml"))
            continue
        support = len(words & vocab) / len(words)
        scores[check] = round(support, 3)
        if support == 0.0:
            findings.append(Finding(
                Severity.BLOCKER, "unpublished-rule",
                f"check '{check}' shares no content word with anything the agent is "
                f"shown -- it enforces a rule that was never published: "
                f"{wording[:110]!r}", "tests/basis.toml"))
        elif support < 0.45:
            findings.append(Finding(
                Severity.WARN, "thin-publication",
                f"check '{check}' scores {support:.0%} lexical support; confirm the "
                "rule is stated rather than implied", "tests/basis.toml"))

    weakest = sorted(scores.items(), key=lambda kv: kv[1])[:5]
    return findings, {"support": scores, "weakest": weakest,
                      "method": "content-word overlap against the agent-visible "
                                "text. Blocks only at zero overlap; the 0-45% band "
                                "is a reading queue, not a verdict. A rule stated "
                                "in different words scores low and is not a defect, "
                                "and a coincidental match scores high and is."}


# --------------------------------------------------------------------------
# kw006 -- hidden enumerations
# --------------------------------------------------------------------------

class _CollectionFinder(ast.NodeVisitor):
    """Literal string collections used for membership tests.

    kw006's grader accepted only privately whitelisted evidence identifiers while
    the task said extra valid evidence was allowed. That whitelist was a set
    literal in the grader. Any such collection is either published or a trap the
    agent cannot see.
    """

    def __init__(self) -> None:
        self.collections: list[tuple[int, list[str]]] = []

    def _literals(self, node: ast.AST) -> list[str] | None:
        if not isinstance(node, (ast.Set, ast.List, ast.Tuple)):
            return None
        values = []
        for elt in node.elts:
            if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                values.append(elt.value)
            else:
                return None
        return values or None

    def visit_Assign(self, node: ast.Assign) -> None:
        values = self._literals(node.value)
        if values is None and isinstance(node.value, ast.Call):
            fn = node.value.func
            name = getattr(fn, "id", None) or getattr(fn, "attr", None)
            if name in ("set", "frozenset") and node.value.args:
                values = self._literals(node.value.args[0])
        if values and len(values) >= 3:
            self.collections.append((node.lineno, values))
        self.generic_visit(node)


def _key_enumerations(ctx: GateContext) -> list[tuple[str, str, list[str]]]:
    """Identifier-shaped string lists inside the answer key.

    kw006's evidence whitelist was not a Python literal -- it lived in
    tests/key/handover.json and was reached as `c["evidence"]`. An accept-list is
    a hidden enumeration wherever it is stored, so the key is searched too.
    """
    out: list[tuple[str, str, list[str]]] = []
    key_dir = ctx.path("tests/key")
    if not key_dir.is_dir():
        return out

    def walk(node: Any, path: str, origin: str) -> None:
        if isinstance(node, dict):
            for k, v in node.items():
                walk(v, f"{path}.{k}" if path else str(k), origin)
        elif isinstance(node, list):
            members = [v for v in node if isinstance(v, str)]
            if len(members) >= 3 and len(members) == len(node):
                ids = [m for m in members
                       if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.\-]{2,}", m)]
                if len(ids) >= 3:
                    out.append((origin, path, ids))
            for i, v in enumerate(node):
                walk(v, f"{path}[{i}]", origin)

    for path in sorted(key_dir.glob("*.json")):
        try:
            walk(json.loads(path.read_text()), "", _rel(ctx, path))
        except json.JSONDecodeError:
            continue
    return out


def _enumeration(ctx: GateContext) -> tuple[list[Finding], dict]:
    instruction = _agent_visible_text(ctx)
    basis_text = " ".join(_basis(ctx).values())
    published = instruction + "\n" + basis_text
    findings: list[Finding] = []
    evidence: dict[str, Any] = {"collections": []}

    for path, source in _grader_sources(ctx):
        try:
            tree = ast.parse(source)
        except SyntaxError as exc:
            findings.append(Finding(Severity.BLOCKER, "grader-syntax",
                                    f"cannot parse grader: {exc}", _rel(ctx, path)))
            continue
        finder = _CollectionFinder()
        finder.visit(tree)
        for lineno, values in finder.collections:
            # Identifier-shaped members are the risky kind: a set of record ids
            # or evidence locators the agent is expected to match exactly.
            idish = [v for v in values if re.fullmatch(r"[A-Z0-9][A-Za-z0-9_.\-]{2,}", v)]
            if len(idish) < 3:
                continue
            unpublished = [v for v in idish if v not in published]
            evidence["collections"].append(
                {"file": _rel(ctx, path), "line": lineno, "size": len(idish),
                 "unpublished": len(unpublished)})
            if unpublished:
                findings.append(Finding(
                    Severity.BLOCKER, "hidden-enumeration",
                    f"{len(unpublished)} of {len(idish)} identifiers in this "
                    f"collection are never published to the agent "
                    f"(e.g. {unpublished[:4]}); if the task allows any valid "
                    "answer, the grader must not hold a private allowlist",
                    f"{_rel(ctx, path)}:{lineno}"))

    # An answer key legitimately holds the correct answer, and §0 positively
    # requires those values NOT to appear in the fixture. So "unpublished" alone
    # is not a defect -- flagging it fires on 216 fields in one shipped bundle
    # and buries the one that matters.
    #
    # The defect is narrower: a key used as an ACCEPT-LIST bounding a field the
    # task says is open. kw006 told the agent extra valid evidence was allowed
    # and then graded against `allowed-references.json`. Those lists are named
    # like what they are, so the name is the discriminator.
    #
    # Known false negative: an accept-list under a neutral name is invisible
    # here. The full inventory is emitted as evidence for exactly that reason --
    # a reviewer signs off on the list, the gate only blocks the obvious case.
    accept_like = re.compile(
        r"allow|accept|permit|whitelist|eligible|admissible", re.I)
    openness = re.compile(
        r"\b(any|other|additional|extra|further|more)\b[^.]{0,60}"
        r"\b(valid|acceptable|evidence|reference|source)\b", re.I)
    task_says_open = bool(openness.search(instruction))
    evidence["task_declares_open_set"] = task_says_open

    docs = _agent_visible_documents(ctx)
    for origin, field, ids in _key_enumerations(ctx):
        # Membership is not the test. Every id in kw006's 390-entry allowlist
        # appears somewhere in the fixture -- the records exist, of course they
        # do. What was never published is the SET: which of them count. So ask
        # whether any single agent-visible document declares most of the list.
        best = max((sum(1 for v in ids if v in text) / len(ids)
                    for text in docs.values()), default=0.0)
        unpublished = [v for v in ids if v not in published]
        label = field or "(root)"
        entry = {"file": origin, "field": label, "size": len(ids),
                 "unpublished": len(unpublished), "best_doc_coverage": round(best, 2)}
        evidence["collections"].append(entry)
        if best >= 0.8:
            continue          # some document does declare this set
        named_like_allowlist = bool(accept_like.search(origin) or accept_like.search(label))
        if named_like_allowlist:
            findings.append(Finding(
                Severity.BLOCKER, "hidden-enumeration",
                f"{origin}:{label} is named as an accept-list and holds {len(ids)} "
                f"identifiers, but no agent-visible document declares the set "
                f"(best coverage {best:.0%}). Grading an open field against a "
                "private list silently narrows what counts as correct", origin))
        elif task_says_open:
            findings.append(Finding(
                Severity.WARN, "possible-accept-list",
                f"{origin}:{label} holds {len(ids)} identifiers that no single "
                f"document declares as a set (best coverage {best:.0%}) and the "
                "instruction offers an open set; confirm this is the answer and not "
                "a bound on acceptable answers", origin))
    return findings, evidence


# --------------------------------------------------------------------------
# kw006 -- ambiguous category definitions
# --------------------------------------------------------------------------

def _closed_vocabularies(ctx: GateContext) -> dict[str, list[str]]:
    """Sets of mutually exclusive values the agent must choose between.

    Three things count as a closed vocabulary: a JSON Schema `enum` in a
    fixture file, an `enum` in a published output schema, and a prose run of
    alternatives joined by an explicit "or". An earlier version
    treated every backticked lowercase token as a category and reported 53
    "ambiguous" pairs on one bundle -- they were form field names like
    `bottom_px` and `charged_blocks`, which are not alternatives at all.
    """
    vocabs: dict[str, list[str]] = {}
    for root in (ctx.path("environment", "files"), ctx.path("environment", "fixtures")):
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*.json")):
            if path.stat().st_size > 2_000_000:
                continue
            try:
                doc = json.loads(path.read_text(errors="replace"))
            except (json.JSONDecodeError, OSError):
                continue

            def walk(node: Any, trail: str) -> None:
                if isinstance(node, dict):
                    values = node.get("enum")
                    if isinstance(values, list) and len(values) >= 2 and all(
                            isinstance(v, str) for v in values):
                        vocabs[f"{path.name}:{trail or 'enum'}"] = values
                    for k, v in node.items():
                        walk(v, f"{trail}.{k}" if trail else str(k))
                elif isinstance(node, list):
                    for i, v in enumerate(node):
                        walk(v, f"{trail}[{i}]")

            walk(doc, "")

    # The output schema is a closed vocabulary too, and the most direct one:
    # it is where the agent is told which verdicts it may write. It is
    # published (each step's contract prints it), but the ENUM is only a list;
    # the definitions have to be in the prose. kw006's handover verdicts were
    # exactly this shape and this gate only ever read fixture JSON and prose.
    outputs_path = ctx.path("tests", "outputs.json")
    try:
        outputs = json.loads(outputs_path.read_text()).get("outputs", []) if outputs_path.is_file() else []
    except (json.JSONDecodeError, OSError, AttributeError):
        outputs = []
    for output in outputs if isinstance(outputs, list) else []:
        def schema_walk(node: Any, trail: str) -> None:
            if not isinstance(node, dict):
                return
            values = node.get("enum")
            if isinstance(values, list) and len(values) >= 2 and all(
                    isinstance(v, str) for v in values):
                vocabs[f"schema:{output.get('file')}:{trail or '(root)'}"] = values
            for key, sub in (node.get("properties") or {}).items():
                schema_walk(sub, f"{trail}.{key}" if trail else key)
            if isinstance(node.get("items"), dict):
                schema_walk(node["items"], f"{trail}[]")
        if isinstance(output, dict):
            schema_walk(output.get("schema"), "")

    text = _agent_visible_text(ctx)
    for run in re.findall(r"((?:`[a-z][a-z_]{2,24}`(?:,\s*|\s+)){1,6}`?or`?\s*`[a-z][a-z_]{2,24}`)",
                          text):
        terms = re.findall(r"`([a-z][a-z_]{2,24})`", run)
        if len(terms) >= 3:
            vocabs.setdefault("prose:" + "|".join(sorted(terms)), terms)
    return vocabs


#: Containment (shared words / the smaller definition's words) at or above
#: which one category's definition is the other's predicate, possibly plus
#: extra words -- a blocking ambiguity -- rather than a lexical resemblance
#: between two different predicates (v2, 2026-10-02).
NEAR_IDENTICAL_DEFINITIONS = 0.90


def _ambiguity(ctx: GateContext) -> tuple[list[Finding], dict]:
    """Alternatives the agent must choose between need disjoint definitions.

    kw006 asked for verdicts including `incorrect` and `unsupported` without
    saying which wins when both apply. Two defensible answers is an ambiguous
    task, not a hard one, and every zero it produces is measurement error.
    """
    text = _agent_visible_text(ctx)
    # A schema vocabulary's definitions must come from prose. The contract
    # prints the schema itself, and a JSON block lists every allowed value in
    # one "sentence" -- which would read as each value defining the others.
    prose = re.sub(r"```.*?```", " ", text, flags=re.S)
    prose_sentences = _SENTENCE_END.split(prose)
    vocabs = _closed_vocabularies(ctx)
    findings: list[Finding] = []
    evidence: dict[str, Any] = {"vocabularies": {k: v for k, v in list(vocabs.items())[:20]},
                                "n_vocabularies": len(vocabs)}
    if not vocabs:
        return findings, {**evidence, "note": "no closed vocabulary found"}

    sentences = _SENTENCE_END.split(text)
    precedence = {"precedence", "takes", "wins", "before", "priority", "prefer",
                  "overrides", "rather", "instead", "unless", "only"}
    overlaps = []
    # One schema enum is often reachable by many paths; report each ambiguous
    # PAIR once. Without this, kw-003's three overlapping status values produced
    # 71 findings describing the same three problems.
    seen_pairs: set[tuple[str, str]] = set()
    seen_undefined: set[str] = set()
    for name, terms in vocabs.items():
        # Every vocabulary is defined by windows, not whole sentences. Prose
        # vocabularies kept whole-sentence crediting after schema ones moved
        # off it, so values defined side by side read as one: a-051's four
        # roles, each defined separately in one sentence that also says "the
        # four do not contain one another", scored 92-99% and blocked the task;
        # a-046's three mutually exclusive outcomes scored 78-89% (build
        # 2026-09-26). Re-run over all 33 bundles: 9 blockers gone, none new.
        windows = _definition_windows(terms, prose_sentences)
        defs = {term: set().union(*(_content_tokens(window) - set(terms)
                                  for window in fragments))
                for term, fragments in windows.items()}
        # Precedence is still read from the whole sentences that discuss a
        # value, as it always was for prose vocabularies.
        context: dict[str, set[str]] = {}
        if not name.startswith("schema:"):
            for term in terms:
                words: set[str] = set()
                for sent in sentences:
                    if re.search(rf"\b{re.escape(term)}\b", sent):
                        words |= _content_tokens(sent) - {term}
                context[term] = words
        undefined = [t for t, w in defs.items() if len(w) < 4]
        for term in undefined:
            if term in seen_undefined:
                continue
            seen_undefined.add(term)
            findings.append(Finding(
                Severity.BLOCKER, "undefined-category",
                f"`{term}` is an allowed value of {name} but is never given a "
                "definition the agent could apply. Define it by MEANING (what the "
                "value says about the item); where the boundary is a rule a fixture "
                "document already states, refer to that rule (e.g. 'the plan's stop "
                "condition holds for this partner') and never restate its threshold, "
                "exception or procedure in the instruction -- a restated rule is an "
                "answer leak", name))
        for i, a in enumerate(terms):
            for b in terms[i + 1:]:
                wa, wb = defs.get(a, set()), defs.get(b, set())
                if not wa or not wb:
                    continue
                j = len(wa & wb) / len(wa | wb)
                if j < 0.5:
                    continue
                stated = any(w in (wa | wb | context.get(a, set()) | context.get(b, set()))
                             for w in precedence)
                # The precedence vocabulary is English. Where the defining
                # words are mostly in another script a stated precedence cannot
                # be read, and a blocker would be one the author cannot clear.
                unreadable = sum(not w.isascii() for w in wa | wb) * 2 > len(wa | wb)
                polarity_contrast = _negated_definition_contrast(windows[a], windows[b])
                # A contract that declares its values mutually exclusive ("exactly
                # one of six mutually exclusive values") has stated the boundary;
                # shared vocabulary is then the domain's, not an overlap (a-044's
                # OPEN "nothing sold yet" vs CLOSED "zero shares remain" blocked
                # at 75% shared words, 2026-10-02). The semantic review still
                # reads the predicates.
                # Checked per LINE (a field's bullet), not per sentence: a-044
                # declares "exactly one of six mutually exclusive values" in the
                # bullet's first sentence and defines OPEN/CLOSED in later ones.
                declared_exclusive = any(
                    re.search(r"mutually exclusive|exactly one of", s, re.I)
                    and re.search(rf"\b{re.escape(a)}\b", s) and re.search(rf"\b{re.escape(b)}\b", s)
                    for s in text.splitlines())
                polarity_contrast = polarity_contrast or declared_exclusive
                overlaps.append({"vocab": name, "a": a, "b": b,
                                 "jaccard": round(j, 2), "precedence_stated": stated,
                                 "precedence_readable": not unreadable,
                                 "polarity_contrast": polarity_contrast})
                pair = tuple(sorted((a, b)))
                if pair in seen_pairs:
                    continue
                seen_pairs.add(pair)
                if not stated:
                    findings.append(Finding(
                        # v2: near-identical definitions are an ambiguity and
                        # block; a partial lexical overlap (60% shared words for
                        # "printed in black and white" vs "printed in colour",
                        # a-003, 2026-10-02) is a heuristic the author cannot
                        # clear by editing, so it is a WARN and the semantic
                        # review decides whether the predicates overlap.
                        Severity.WARN if unreadable or polarity_contrast
                        or len(wa & wb) / min(len(wa), len(wb)) < NEAR_IDENTICAL_DEFINITIONS
                        else Severity.BLOCKER,
                        "overlapping-categories",
                        f"`{a}` and `{b}` (both allowed values of {name}) share "
                        f"{j:.0%} of their defining language and no precedence is "
                        "recognised lexically; check whether their predicates overlap"
                        + (". The definitions contain a matching predicate with opposite "
                           "polarity, so similarity is not proof of ambiguity. "
                           "Independent semantic review must verify the boundary"
                           if polarity_contrast else
                           ". The definitions are not in English, so a stated "
                           "precedence cannot be recognised lexically: read them"
                           if unreadable else ""),
                        name))
    evidence["overlaps"] = overlaps[:20]
    return findings, evidence


def _windowed_definitions(terms: list[str], sentences: list[str]) -> dict[str, set[str]]:
    """Each value's defining words: what follows it up to the next value of the
    same vocabulary (or the sentence end), else what precedes it.

    Schema vocabularies are often defined in one sentence -- `keep_as_is` when
    the line is exactly the quote and `trim_to_quote` when it carries other
    words too. Crediting each value with the whole sentence reads two disjoint
    definitions as 91% the same; a window per value reads them as written."""
    return {term: set().union(*(_content_tokens(window) - set(terms)
                               for window in fragments))
            for term, fragments in _definition_windows(terms, sentences).items()}


def _definition_windows(terms: list[str], sentences: list[str]) -> dict[str, list[str]]:
    """Retain the actual clauses, including negation, before content tokenisation."""
    definitions: dict[str, list[str]] = {term: [] for term in terms}
    if not terms:
        return definitions
    ordered = sorted(terms, key=len, reverse=True)
    plain = re.compile("|".join(rf"\b{re.escape(term)}\b" for term in ordered))
    # Where the contract writes its values in backticks, only a backticked
    # value starts a definition: a value's word used in another's definition
    # ("`fact` (the source's own figure the forecast is scored against)") must
    # not cut that definition short (a-009, 2026-10-02: `fact` reported undefined).
    ticked = re.compile("|".join(rf"`{re.escape(term)}`" for term in ordered))
    for sentence in sentences:
        hits = list(ticked.finditer(sentence)) or list(plain.finditer(sentence))
        for index, match in enumerate(hits):
            end = hits[index + 1].start() if index + 1 < len(hits) else len(sentence)
            window = sentence[match.end():end]
            if len(_content_tokens(window) - set(terms)) < 2:
                start = hits[index - 1].end() if index else 0
                window = sentence[start:match.start()] + " " + window
            definitions[match.group(0).strip("`")].append(window)
    return definitions


def _negated_definition_contrast(first: list[str], second: list[str]) -> bool:
    """Recognise an otherwise identical predicate, not merely any negation word."""
    negators = {"not", "never", "não", "nao"}

    def clauses(windows: list[str]) -> list[list[str]]:
        return [re.findall(r"\w+", clause.casefold()) for window in windows
                for clause in re.split(r"[;:()\n]", window)]

    first_clauses, second_clauses = clauses(first), clauses(second)
    for negative, positive in ((first_clauses, second_clauses),
                               (second_clauses, first_clauses)):
        for words in negative:
            if sum(word in negators for word in words) != 1:
                continue
            predicate = [word for word in words if word not in negators]
            if len(predicate) < 5 or len(_content_tokens(" ".join(predicate))) < 3:
                continue
            for candidate in positive:
                if any(word in negators for word in candidate):
                    continue
                if any(candidate[start:start + len(predicate)] == predicate
                       for start in range(len(candidate) - len(predicate) + 1)):
                    return True
    return False


# --------------------------------------------------------------------------
# kw002 -- brittle comparison / type strictness
# --------------------------------------------------------------------------

class _ComparisonFinder(ast.NodeVisitor):
    def __init__(self) -> None:
        self.strict_types: list[tuple[int, str]] = []
        self.exact_strings: list[tuple[int, str]] = []
        self.float_equality: list[int] = []
        self.type_identity: list[tuple[int, str]] = []

    @staticmethod
    def _is_type_call(node: ast.AST) -> bool:
        return (isinstance(node, ast.Call)
                and getattr(node.func, "id", None) == "type"
                and len(node.args) == 1)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        # `type(x).__name__` folds the value's type into the comparison, so
        # "1960" and 1960 compare unequal. This is the kw002 defect verbatim:
        # its grader keys a Counter on (type(item).__name__, item).
        if node.attr == "__name__" and self._is_type_call(node.value):
            self.type_identity.append((node.lineno, "type(x).__name__"))
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        fn = getattr(node.func, "id", None)
        if fn == "isinstance" and len(node.args) == 2:
            target = node.args[1]
            names = []
            if isinstance(target, ast.Tuple):
                names = [getattr(e, "id", "") for e in target.elts]
            else:
                names = [getattr(target, "id", "")]
            names = [n for n in names if n]
            if names and set(names) <= {"int", "float"}:
                self.strict_types.append((node.lineno, "/".join(names)))
        self.generic_visit(node)

    def visit_Compare(self, node: ast.Compare) -> None:
        for op, comp in zip(node.ops, node.comparators):
            if isinstance(op, (ast.Is, ast.IsNot, ast.Eq)) and (
                    self._is_type_call(node.left) or self._is_type_call(comp)):
                self.type_identity.append((node.lineno, "type(x) is T"))
            if not isinstance(op, ast.Eq):
                continue
            if isinstance(comp, ast.Constant):
                if isinstance(comp.value, str) and len(comp.value) > 3:
                    self.exact_strings.append((node.lineno, comp.value))
                elif isinstance(comp.value, float):
                    self.float_equality.append(node.lineno)
        self.generic_visit(node)


def _normalisation(ctx: GateContext) -> tuple[list[Finding], dict]:
    """Traps must catch faulty reasoning, not a correct answer written differently.

    kw002 stored candidate years as numbers and rejected the string "1960",
    although the public instruction never required numeric typing and the
    published shape used a string placeholder. The model was right; the grader
    was narrow.
    """
    findings: list[Finding] = []
    evidence: dict[str, Any] = {"strict_types": [], "exact_strings": [],
                                "float_equality": [], "type_identity": []}
    for path, source in _grader_sources(ctx):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue        # reported by the enumeration gate
        finder = _ComparisonFinder()
        finder.visit(tree)
        rel = _rel(ctx, path)
        for lineno, names in finder.strict_types:
            evidence["strict_types"].append({"file": rel, "line": lineno, "types": names})
            findings.append(Finding(
                Severity.WARN, "numeric-only-type-check",
                f"isinstance(..., {names}) rejects an equivalent numeric string; "
                "accept both forms or state the canonical type in the instruction",
                f"{rel}:{lineno}"))
        for lineno, value in finder.exact_strings:
            evidence["exact_strings"].append({"file": rel, "line": lineno,
                                              "value": value[:60]})
            findings.append(Finding(
                Severity.WARN, "exact-string-compare",
                f"equality against {value[:40]!r} without normalisation; five tasks in "
                "one corpus scored exactly 0.125 because a verbatim stamp differed by "
                "one dash character", f"{rel}:{lineno}"))
        for lineno, kind in finder.type_identity:
            evidence["type_identity"].append({"file": rel, "line": lineno,
                                              "pattern": kind})
            findings.append(Finding(
                Severity.BLOCKER, "type-sensitive-compare",
                f"{kind} makes an equivalent value of another type compare unequal "
                "(\"1960\" != 1960). Unless the instruction states the canonical "
                "type, this rejects a correct answer written differently",
                f"{rel}:{lineno}"))
        for lineno in finder.float_equality:
            evidence["float_equality"].append({"file": rel, "line": lineno})
            findings.append(Finding(
                Severity.BLOCKER, "float-equality",
                "exact equality against a float; use a tolerance",
                f"{rel}:{lineno}"))
    return findings, evidence


# --------------------------------------------------------------------------
# kw003 -- the answer key must be recomputed, not typed in
# --------------------------------------------------------------------------

def _oracle(ctx: GateContext) -> tuple[list[Finding], dict]:
    """A hand-authored expected value is a defect waiting to happen.

    kw003's rubric expected 26 removals where the truth was 27. The number was
    typed in. The control is not "be careful": it is that the expected value must
    be *computed from the fixture at grade time*, by an implementation
    independent of the one the agent is being asked to write.
    """
    findings: list[Finding] = []
    key_dir = ctx.path("tests/key")
    oracle = ctx.path("tests/oracle.py")
    declarative = ctx.path("tests/checks.json")
    evidence = {"key_dir": key_dir.is_dir(), "oracle_module": oracle.exists(),
                "declarative": declarative.exists()}

    # Preferred form: declarative checks whose targets are expressions evaluated
    # against the fixture at grade time. There is then no answer key to get
    # wrong -- the 26-vs-27 defect is not a mistake available in this shape.
    if declarative.exists():
        checks = json.loads(declarative.read_text()).get("checks", [])
        literals, derived = [], 0
        for check in checks:
            if check.get("kind") != "objective":
                continue
            target = check.get("target")
            if target is None:
                continue
            if target.get("op") == "literal":
                literals.append({"check": check["id"],
                                 "why": target.get("why", "")})
            else:
                derived += 1
        evidence.update(derived_targets=derived, literal_targets=literals)
        for lit in literals:
            if not lit["why"].strip():
                findings.append(Finding(
                    Severity.BLOCKER, "unjustified-literal-target",
                    f"check {lit['check']!r} has a hand-typed target with no 'why'. "
                    "A literal expected value is how an answer key comes to say 26 "
                    "when the truth is 27", "tests/checks.json"))
            else:
                findings.append(Finding(
                    Severity.WARN, "literal-target",
                    f"check {lit['check']!r} uses a literal target: {lit['why'][:90]}",
                    "tests/checks.json"))
        if derived == 0 and not literals:
            findings.append(Finding(
                Severity.BLOCKER, "no-derived-targets",
                "no objective declares a target; nothing is scored against the "
                "fixture", "tests/checks.json"))
        return findings, evidence

    if not (key_dir.is_dir() or oracle.exists()):
        findings.append(Finding(
            Severity.BLOCKER, "no-oracle",
            "no tests/checks.json, no tests/oracle.py and no tests/key/ -- expected "
            "values cannot be shown to be recomputed rather than typed in", "tests/"))
        return findings, evidence

    # A key file that is a bare literal is exactly the kw003 failure.
    literal_keys = []
    for path in sorted(key_dir.glob("*.json")) if key_dir.is_dir() else []:
        try:
            data = json.loads(path.read_text())
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict) and data.get("derivation") is None:
            literal_keys.append(_rel(ctx, path))
    for rel in literal_keys:
        findings.append(Finding(
            Severity.BLOCKER, "literal-answer-key",
            f"{rel} carries expected values with no 'derivation' field naming how they "
            "were recomputed from the fixture", rel))
    evidence["literal_keys"] = literal_keys
    return findings, evidence


# --------------------------------------------------------------------------
# kw003 -- step isolation
# --------------------------------------------------------------------------

def _verbatim_files(ctx: GateContext) -> set[str]:
    """Fixture paths the provenance ledger records as lifted or anonymized from
    the trace (the ledger gate verifies those records against the bytes)."""
    try:
        ledger = json.loads(ctx.path("provenance/ledger.json").read_text())
    except (OSError, ValueError):
        return set()
    return {e["path"] for e in ledger.get("entries") or []
            if isinstance(e, dict) and isinstance(e.get("path"), str)
            and e.get("origin") in ("lifted", "anonymized")}


def _step_isolation(ctx: GateContext) -> tuple[list[Finding], dict]:
    """Step N+1's material must be unreachable while step N is being graded.

    kw003 shipped with rollback material readable during step 1, so an agent
    could do step-2 work before step 1 had been graded, and step 1's score was
    taken from state step 2 had already moved.
    """
    import tomllib as _t
    with ctx.path("task.toml").open("rb") as fh:
        task = _t.load(fh)
    steps = task.get("steps") or []
    findings: list[Finding] = []
    evidence: dict[str, Any] = {"n_steps": len(steps)}
    if len(steps) < 2:
        return findings, {**evidence, "note": "single-step bundle; gate not applicable"}

    names = [s.get("name") for s in steps]
    evidence["steps"] = names

    # 1. Each step's verifier must be told which step it is.
    for step in steps:
        env = ((step.get("verifier") or {}).get("env") or {})
        if env.get('ARENA_STEP') != step.get('name'):
            findings.append(Finding(
                Severity.BLOCKER, "unmarked-step",
                f"step {step.get('name')!r} passes no matching ARENA_STEP marker to its verifier; the "
                "grader cannot tell which step's state it is scoring", "task.toml"))

    # 2. The current runners commit completed-step outputs at execution time.
    # A checked-in handoff note neither creates nor proves those snapshots.
    # Check the reproducible package contract here; release separately verifies
    # immutable rollout/native history evidence from actual execution.
    try:
        from ..author.contracts import compile_steps, strict_json
        from ..assurance import generated_problems
        spec = strict_json(ctx.path('authoring', 'spec.json').read_text())
        declared = compile_steps(spec)
        if [s['name'] for s in declared] != names:
            raise ValueError('declared step order differs from task.toml')
        owners = {name: [o['file'] for o in spec.get('outputs', []) if o['step'] == name]
                  for name in names}
        if any(not files for files in owners.values()):
            raise ValueError('every step needs its own declared output files')
        if errors := generated_problems(ctx.task_dir):
            raise ValueError('; '.join(errors))
        evidence['handoff'] = {'mode': 'harness-committed-artifacts', 'outputs_by_step': owners}
        evidence['runtime_scope'] = ('Static package contract only. Immutable completed-step '
                                     'snapshots and native history receipts must be verified '
                                     'separately before release.')
    except (ValueError, KeyError, TypeError, OSError) as exc:
        findings.append(Finding(
            Severity.BLOCKER, "unverified-step-contract",
            f"cannot bind step isolation to a current generated output contract: {exc}; "
            "a handoff note alone cannot establish immutable submissions", "steps/"))

    # 3. Later-step material must not sit in the initial fixture -- unless the
    # spec withholds it, in which case the runtime never copies it into step 1's
    # workspace and the document is genuinely unreachable there. This gate's own
    # advice was "unlock it with the step that needs it"; `step_files` is that
    # unlock, so a withheld path is not a leak.
    from ..author import step_files as _step_files
    try:
        _spec = strict_json(ctx.path('authoring', 'spec.json').read_text())
    except (OSError, ValueError):
        _spec = {}
    withheld = set(_step_files.withheld_from(_spec, names[0], names))
    evidence["withheld_from_first_step"] = sorted(withheld)

    fixture = next((ctx.path("environment", n) for n in ("files", "fixtures")
                    if ctx.path("environment", n).is_dir()), None)
    leaked = []
    if fixture is not None:
        later = [n for n in names[1:] if n]
        for path in fixture.rglob("*"):
            if not path.is_file():
                continue
            rel = str(path.relative_to(fixture))
            if rel in withheld:
                continue
            if any(n.lower() in rel.lower() for n in later):
                leaked.append(rel)
    if leaked:
        findings.append(Finding(
            Severity.BLOCKER, "later-step-material-in-fixture",
            f"fixture contains file(s) named for a later step: {leaked[:5]}; gate them "
            "on the step marker instead", "environment/files"))
    evidence["leaked"] = leaked

    # 4. ...and by what the files hold and who uses them, not only their names.
    # kw003's rollback material would have passed step 3 under any neutral
    # file name; the name is the one thing an author controls for free.
    if fixture is not None:
        try:
            content = _later_step_content(ctx, fixture, names)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            content = {"error": str(exc)}
        evidence["content_leaks"] = content
        if content.get("error"):
            findings.append(Finding(
                Severity.BLOCKER, "unverified-step-content",
                f"cannot check fixture content against later steps: {content['error']}",
                "environment/files"))
        for rel, reasons in sorted((content.get("files") or {}).items()):
            if rel in withheld:
                continue
            findings.append(Finding(
                Severity.BLOCKER, "later-step-material-in-fixture",
                f"{rel} is readable during step {names[0]!r} but carries later-step material: "
                + "; ".join(reasons[:3]) + ". Unlock it with the step that needs it",
                f"environment/files/{rel}"))
        # The cautions a reader judges -- step-1 material numbering its own
        # procedure, a generic "next step" -- were computed and then dropped:
        # a signal with no reader is decoration. They warn; they never block.
        for rel, notes in sorted((content.get("forward_reference") or {}).items()):
            if rel in withheld or rel in (content.get("files") or {}):
                continue
            findings.append(Finding(
                Severity.WARN, "possible-forward-reference",
                f"{rel}: " + "; ".join(notes[:2]), f"environment/files/{rel}"))
    return findings, evidence


#: A fixture document that talks about a later step by name. "Stage"/"phase"
#: are deliberately absent -- they are ordinary words in a schedule.
_LATER_STEP_WORDS = re.compile(
    r"\b(?:step\s*(?:2|3|4|two|three|four|ii|iii)|second\s+step|later\s+step"
    r"|follow[- ]?up\s+step|revision\s+step|step[- ]two)\b", re.I)

#: "Next step" is ordinary English -- "the following action" -- and recovered
#: agent transcripts are full of it. It used to block on its own: an e2e build
#: (2026-09-26) was stopped by a recovered README's "## Recommended next step --
#: ask me to continue again", in a file neither step used, which the designer
#: could not edit (recovered files are immutable), so the finding survived its
#: repair and ended the task. It is a caution a reader judges, never a blocker.
_GENERIC_STEP_WORDS = re.compile(r"\bnext\s+step\b", re.I)


def _files_read(expr: Any, out: set[str]) -> set[str]:
    if isinstance(expr, dict):
        if isinstance(expr.get("file"), str):
            out.add(expr["file"])
        for value in expr.values():
            _files_read(value, out)
    elif isinstance(expr, list):
        for value in expr:
            _files_read(value, out)
    return out


def _later_step_content(ctx: GateContext, fixture: Path, names: list[str]) -> dict:
    """Fixture files that step 1 can read but only a later step uses, or that
    carry a later step's identifiers or answers.

    Three content signals, each cheap and each citable:
      usage     -- named by, or read by the checks of, a later step only
      mention   -- the file itself refers to a later step ("for step two ...")
      values    -- a file nothing in step 1 reads holds a later step's answer
                   value or an identifier only the later instruction uses
    Files the first step's instruction names or its checks read are its own
    material: steps that share a document legitimately share its contents."""
    from ..author.contracts import compile_steps, strict_json
    spec = strict_json(ctx.path("authoring", "spec.json").read_text())
    steps = compile_steps(json.loads(json.dumps(spec)))
    first, later = steps[0]["name"], [s["name"] for s in steps[1:]]
    if not later:
        return {"files": {}}
    files = {p.relative_to(fixture).as_posix(): p for p in fixture.rglob("*") if p.is_file()}

    # projection name -> fixture files it reads
    sources: dict[str, set[str]] = {}
    for proj in spec.get("projections") or []:
        if not isinstance(proj, dict) or not proj.get("as"):
            continue
        read = set()
        if proj.get("file"):
            read.add(proj["file"])
        for key in ("left", "right", "paper"):
            if proj.get(key):
                read |= sources.get(proj[key], set())
        for key, label in (proj.get("sources") or {}).items():
            read |= sources.get(key, sources.get(f"{key}.jsonl", set()))
            if isinstance(label, str) and label in files:
                read.add(label)
        sources[proj["as"]] = read

    def resolve(refs: set[str]) -> set[str]:
        out = set()
        for ref in refs:
            out |= sources.get(ref, {ref} if ref in files else set())
        return out

    def named(text: str) -> set[str]:
        return {rel for rel in files if rel in text or Path(rel).name in text}

    used: dict[str, set[str]] = {name: set() for name in [first, *later]}
    for check in spec.get("checks") or []:
        if isinstance(check, dict) and check.get("step") in used and check.get("assertion") != "fixture_intact":
            used[check["step"]] |= resolve(_files_read(check.get("target"), set()))
    by_check = {c.get("id"): c.get("step") for c in spec.get("checks") or [] if isinstance(c, dict)}
    for decision in (spec.get("quality") or {}).get("decisions") or []:
        for cid in decision.get("checks") or []:
            if by_check.get(cid) in used:
                used[by_check[cid]] |= {f for f in decision.get("sources") or [] if f in files}
    text = {s["name"]: s.get("instruction") or "" for s in steps}
    mine = named(text[first]) | used[first]
    theirs = set().union(*(named(text[n]) | used[n] for n in later))

    first_text = text[first]
    later_text = " ".join([text[n] for n in later] + [
        str(s.get("new_information") or "") for s in steps[1:]])
    # identifiers only a later instruction uses: backticked or code-like tokens
    identifiers = set()
    # A bare number (a year, a count, a date) identifies nothing: a step-2
    # instruction mentioning 2024 and 2025 flagged an unused thesis chapter as
    # later-step material (a-066, build 2026-09-26). Code-like tokens need a
    # letter; a backticked token is kept whatever it holds.
    code_like = [t for t in re.findall(
        r"\b[A-Za-z]*\d+[A-Za-z0-9_.-]*[A-Za-z0-9]\b|\b[A-Z][A-Z0-9_-]{3,}\b", later_text)
        if re.search(r"[A-Za-z]", t)]
    for token in re.findall(r"`([^`\n]{3,80})`", later_text) + code_like:
        token = token.strip()
        # A fixture file's own name is not later-step material: the file is
        # judged on its own (usage, above), and documents cite each other.
        if (len(token) >= 4 and token not in first_text
                and token not in files and Path(token).name not in {Path(f).name for f in files}):
            identifiers.add(token)
    # ...and that step 1's own material does not already carry. A token found in
    # a file step 1's instruction names or its checks read is the shared world's
    # vocabulary: steps that share a document share its contents (docstring).
    # Without this, a step-2 instruction naming an existing rule or process
    # (`RULE_7_2`, `01_discover`, found in 6 and 8 step-1 documents) flagged
    # every background spec file as later-step material, and the designer spent
    # both repairs of an e2e build (2026-09-26) on a leak that was not there.
    first_corpus = []
    for rel in mine:
        path = files.get(rel)
        try:
            if path is not None and path.stat().st_size <= 2_000_000:
                first_corpus.append(path.read_text(errors="replace"))
        except OSError:
            continue
    first_corpus = "\n".join(first_corpus)
    identifiers = {token for token in identifiers if token not in first_corpus}

    # later-step answer values that step 1's reference never states
    def leaves(node, out):
        if isinstance(node, dict):
            for v in node.values():
                leaves(v, out)
        elif isinstance(node, list):
            for v in node:
                leaves(v, out)
        elif isinstance(node, str) and len(node.strip()) >= 6 and re.search(r"[\d\s]|[^\x00-\x7f]", node):
            out.add(node.strip())
        return out
    owners = {o.get("file"): o.get("step") for o in spec.get("outputs") or [] if isinstance(o, dict)}
    step_names = [s["name"] for s in steps]
    for f, st in list(owners.items()):
        if isinstance(st, int) and 1 <= st <= len(step_names):
            owners[f] = step_names[st - 1]
    answers: dict[str, set[str]] = {name: set() for name in step_names}
    solution = ctx.path("solution", "submission")
    for f, st in owners.items():
        path = solution / str(f)
        if st in answers and path.is_file():
            try:
                leaves(json.loads(path.read_text()), answers[st])
            except (ValueError, OSError):
                continue
    later_values = set().union(*(answers[n] for n in later)) - answers[first]
    later_values = {v for v in later_values if v not in first_text}

    flagged: dict[str, list[str]] = {}
    forward: dict[str, list[str]] = {}
    verbatim = _verbatim_files(ctx)
    for rel, path in sorted(files.items()):
        reasons = []
        if rel in theirs and rel not in mine:
            reasons.append("only a later step's instruction or checks use it")
        try:
            body = path.read_text(errors="replace") if path.stat().st_size <= 2_000_000 else ""
        except OSError:
            body = ""
        mention = _LATER_STEP_WORDS.search(body)
        if mention and rel not in mine and rel not in verbatim:
            reasons.append(f"it refers to a later step ({mention.group(0)!r})")
        elif mention and rel not in mine:
            # Lifted verbatim from the trace, so written before this task
            # existed: its "STEP 2" numbers its own procedure. The designer may
            # not edit recovered bytes, so as a blocker this had no repair and
            # ended a-005 (build 2026-09-26) on a rescue README. The signals
            # that do show a leak -- only a later step uses it, later answer
            # values, later-only identifiers -- still block below.
            forward.setdefault(rel, []).append(
                f"it refers to a later step ({mention.group(0)!r}); the file is lifted "
                "verbatim from the trace and predates this task, so check that this is "
                "its own numbering")
        elif mention:
            # Step-1 material that says "step 2" is usually numbering its OWN
            # procedure -- a repair guide's "STEP 2: Install ...", a thesis's
            # "Step5 配电网潮流计算". This signal alone used to BLOCK such a file,
            # unlike its three siblings here which all guard on `rel not in
            # mine`, and the bundle then had no way out: the document is read by
            # step 1's own checks, so it cannot be withheld, and in one case
            # step 1's prose names it explicitly, so hiding it would promise the
            # agent a file it could not see. Rewriting the fixture to dodge the
            # regex broke ~30 controls and dropped a reference from 0.98 to 0.0.
            #
            # It is still worth saying: a step-1 document that genuinely points
            # forward does leak. So the signal survives as a caution a reader
            # judges, rather than a blocker with no available repair.
            forward.setdefault(rel, []).append(
                f"it refers to a later step ({mention.group(0)!r}); this is step-1 "
                "material, so check whether that is its own numbering or a real "
                "forward reference")
        elif generic := _GENERIC_STEP_WORDS.search(body):
            forward.setdefault(rel, []).append(
                f"it says {generic.group(0)!r}; ordinary English for 'the following "
                "action', so check it does not describe this task's later step")
        if rel not in mine:
            values = sorted(v for v in later_values if v in body)
            if values:
                reasons.append(f"it states later-step answer value(s) {values[:3]}")
            ids = sorted(i for i in identifiers if i in body)
            if len(ids) >= 2 and rel in verbatim:
                # A lifted file predates the task, so words the later step also
                # uses are the source's own vocabulary: a-024's Italian CRM
                # pages contain `aggiunte` and `motivo`, which step 2 named as
                # output fields (build 2026-09-26). Later answer values and
                # "only a later step uses it" still block.
                forward.setdefault(rel, []).append(
                    f"it carries words a later instruction uses {ids[:3]}; the file is "
                    "lifted verbatim from the trace, so check they are its own vocabulary")
            elif len(ids) >= 2:
                reasons.append(f"it carries identifiers only a later instruction uses {ids[:3]}")
        if reasons:
            flagged[rel] = reasons
    return {"files": flagged, "forward_reference": forward,
            "first_step_material": sorted(mine),
            "later_step_material": sorted(theirs)}


# --------------------------------------------------------------------------
# kw003b -- a simulated counterparty must obey its own published policy
# --------------------------------------------------------------------------

def _policy_consistency(ctx: GateContext) -> tuple[list[Finding], dict]:
    """kw003b's client resolved an equal-priority conflict arbitrarily and then
    demanded a replacement its own published policy forbade. A scripted
    counterparty is part of the environment, and an environment that breaks its
    own rules manufactures failures the agent cannot avoid.

    This gate cannot read intent. It requires that any interactive counterparty
    ships a policy file and a self-test, and fails when it ships neither.
    """
    findings: list[Finding] = []
    client = [p for p in ctx.task_dir.rglob("*.py")
              if "__pycache__" not in p.parts
              and re.search(r"(client|counterparty|reviewer|simulat)", p.name, re.I)]
    evidence = {"counterparty_modules": [_rel(ctx, p) for p in client]}
    if not client:
        return findings, {**evidence, "note": "no scripted counterparty; not applicable"}

    policy = list(ctx.task_dir.rglob("*polic*")) + list(ctx.task_dir.rglob("*rules*"))
    if not policy:
        findings.append(Finding(
            Severity.BLOCKER, "counterparty-without-policy",
            f"{len(client)} scripted counterparty module(s) but no published policy "
            "file; its behaviour cannot be checked against a stated rule",
            evidence["counterparty_modules"][0]))
    selftest = [p for p in ctx.path("tests").rglob("*.py")
                if re.search(r"(policy|client|counterparty)", p.name, re.I)]
    if not selftest:
        findings.append(Finding(
            Severity.WARN, "counterparty-untested",
            "no self-test asserting the counterparty never requests something its "
            "published policy forbids", "tests/"))
    evidence["policy_files"] = [_rel(ctx, p) for p in policy][:5]
    return findings, evidence


completeness_gate = FunctionGate("contract.completeness", _completeness,
                                 requires=("bundle.structure",))
enumeration_gate = FunctionGate("contract.enumeration", _enumeration,
                                requires=("bundle.structure",))
ambiguity_gate = FunctionGate("contract.ambiguity", _ambiguity,
                              requires=("bundle.structure",))
normalisation_gate = FunctionGate("grader.normalisation", _normalisation,
                                  requires=("bundle.structure",))
oracle_gate = FunctionGate("grader.oracle", _oracle, requires=("bundle.structure",))
step_isolation_gate = FunctionGate("env.step_isolation", _step_isolation,
                                   requires=("bundle.structure",))
policy_gate = FunctionGate("env.policy_consistency", _policy_consistency,
                           requires=("bundle.structure",))


def _controls(ctx: GateContext) -> tuple[list[Finding], dict]:
    """Run the control suite the release stage runs, but here, for free.

    `assurance.controls` had exactly one reader: `release.py`, which is reached
    after native calibration at ~$39.52 a task. So a bundle could pass
    `./arena gate` GREEN carrying a counterexample that patches a field to the
    reference's own value, and source cases naming checks their corrected answer
    never moves -- decorative controls that establish nothing. One shipped that
    way in this batch and was only caught by hand.

    Controls are cheap and local: no model call, no Docker. Running them here
    means a broken counterexample is a build error, not a delivery surprise.
    """
    try:
        from ..assurance import controls
        from ..artifacts import policy_identity
        implementation = policy_identity()
        report = controls(ctx.task_dir)
    except Exception as exc:                      # noqa: BLE001
        return [Finding(
            Severity.BLOCKER, "controls-unrunnable",
            f"the control suite could not be run ({type(exc).__name__}: {exc}); "
            "'could not check' is not 'nothing wrong'", "authoring/spec.json")], {}

    findings = [Finding(Severity.BLOCKER, "control-failed", str(problem),
                        "authoring/spec.json")
                for problem in (report.get("errors") or [])]
    findings += [Finding(Severity.WARN, "control-advisory", str(problem),
                         "authoring/spec.json")
                 for problem in (report.get("advisories") or [])]
    return findings, {"schema": report.get("schema"),
                      "artifact_sha256": report.get("artifact_sha256"),
                      "policy_sha256": implementation,
                      "ok": bool(report.get("ok")),
                      "errors": len(report.get("errors") or []),
                      "scope": "counterexamples, alternatives, source cases and "
                               "invariants, run against the shipped grader"}


controls_gate = FunctionGate("quality.controls", _controls,
                             requires=("bundle.structure",))
