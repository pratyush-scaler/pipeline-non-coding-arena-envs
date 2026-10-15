"""The oracle layer -- a normalised projection of the fixture, for targets only.

A check's target must be *derived from the fixture at grade time*, never typed
in. But a fixture is prose and plain text, and an expression language that can
parse arbitrary documents is an expression language that can do anything, which
defeats the point of having one.

So parsing is separated from evaluation. A small registry of named, reviewed
parsers projects fixture documents into rows; the projection is generated at
build time, stored verifier-side, and target expressions read only that. The
expression language stays tiny and general; the parsers stay explicit and
auditable; and nobody hand-types an expected value.

Three properties this buys, each of them a gate the chain can enforce:

* **Regeneration is deterministic.** `verify` re-runs every parser against the
  live fixture and compares. If they disagree, fixture and oracle have drifted
  and the bundle is refused -- the "freeze fixture, instruction and grader
  together" rule, mechanised.
* **The projection never reaches the agent.** It lives under `tests/derived/`,
  which `.dockerignore` excludes. A projection in the agent's workspace would
  hand over exactly the structure the task asks it to build.
* **The parser is the reviewable unit.** A reviewer checks that
  `numbered_key` reads `12. b` the way a person would, once, rather than
  re-reading a bespoke grader per task.

Adding a parser is a deliberate act: it is code, it is reviewed, and it is
shared across tasks. A task needing a parser nobody else needs is usually a task
whose fixture should be shaped differently.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Callable

Parser = Callable[[str], list[dict]]
REGISTRY: dict[str, Parser] = {}


def parser(name: str) -> Callable[[Parser], Parser]:
    def register(fn: Parser) -> Parser:
        REGISTRY[name] = fn
        return fn
    return register


@parser("numbered_key")
def numbered_key(text: str) -> list[dict]:
    """`12. b` / `12. ?` -> {item, answer, resolved}.

    An unresolved marker is kept as a value rather than dropped: "this reviewer
    did not decide" is information the task turns on, and a parser that silently
    omitted those rows would make the unresolved set underivable.
    """
    rows = []
    for line in text.splitlines():
        m = re.match(r"\s*(\d+)\s*[.)]\s*(\S+)\s*$", line)
        if not m:
            continue
        answer = m.group(2).strip().lower()
        rows.append({"item": int(m.group(1)), "answer": answer,
                     "resolved": answer not in ("?", "-", "n/a", "")})
    return rows


# Lexical observations are useful for locating evidence, but cannot decide
# whether a question is answerable or whether a visual is missing. In particular
# there are no task-specific phrases or privately enumerated gold question IDs.
_VISUAL_CUES = re.compile(r"\b(?:figures?|diagrams?|images?|charts?|graphs?|arrangement|venn)\b", re.I)


@parser("mcq_paper")
def mcq_paper(text: str) -> list[dict]:
    """A numbered paper -> printed options, stem and lexical visual cues.

    `visual_cues` is a location aid, never an answerability classifier. Any task
    grading semantic dependence on absent material needs independently reviewed
    evidence and a public decision rule; this parser supplies neither a private
    missing-visual answer nor an inferred certification verdict.
    """
    rows = []
    for block in re.split(r"\n(?=\d+\s*[.)]\s)", text):
        m = re.match(r"\s*(\d+)\s*[.)]", block)
        if not m:
            continue
        options = re.findall(r"^\s*([a-d])\s*\)", block, re.M)
        unique = sorted(set(options))
        stem = block.split("\n", 1)[0]
        stem = re.sub(r"^\s*\d+\s*[.)]\s*", "", stem).strip()
        rows.append({"item": int(m.group(1)), "stem": stem, "options": unique,
                     "option_count": len(unique),
                     "complete_options": unique == ["a", "b", "c", "d"],
                     "visual_cues": sorted({cue.lower() for cue in _VISUAL_CUES.findall(block)})})
    return rows


@parser("markdown_sections")
def markdown_sections(text: str) -> list[dict]:
    """Any ATX-headed markdown -> one row per section.

    The generic projection. Most professional documents are headed prose, and
    without this the registry only fits the one domain its first parsers came
    from -- which is how an automated designer ends up choosing `numbered_key`
    for a brand book and producing zero rows.
    """
    rows, current, body = [], None, []

    def flush():
        if current is not None:
            joined = "\n".join(body).strip()
            rows.append({"heading": current["heading"], "level": current["level"],
                         "index": len(rows) + 1, "text": joined,
                         "words": len(joined.split()), "empty": not joined})

    fence = None
    for line in text.splitlines():
        marker = re.match(r"^\s{0,3}(`{3,}|~{3,})", line)
        if marker:
            token = marker.group(1)
            if fence is None:
                fence = token
            elif token[0] == fence[0] and len(token) >= len(fence) and not line[marker.end():].strip():
                fence = None
            if current is not None:
                body.append(line)
            continue
        if fence:
            if current is not None:
                body.append(line)
            continue
        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            flush()
            current = {"heading": m.group(2).strip(), "level": len(m.group(1))}
            body = []
        elif current is not None:
            body.append(line)
    flush()
    return rows


@parser("numbered_sections")
def numbered_sections(text: str) -> list[dict]:
    """`1. HEADING` decimal-numbered plain-text sections -> one row per section.

    The plain-text counterpart of `markdown_sections`. Working notes, minutes
    and consultation logs number their sections rather than marking them with
    ATX hashes, and without this such a document projects to nothing at all.

    A heading is a line that begins with a decimal integer, a full stop and
    whitespace. The body is every line up to the next such heading, stripped;
    `words` counts whitespace-separated tokens in that body, matching
    `markdown_sections` so a word-count target reads the same either way.
    Anything before the first numbered heading is preamble and is not a row.
    """
    rows: list[dict] = []
    heads = [(i, m) for i, line in enumerate(text.splitlines())
             if (m := re.match(r"^(\d+)\.\s+(\S.*?)\s*$", line))]
    lines = text.splitlines()
    for k, (i, m) in enumerate(heads):
        end = heads[k + 1][0] if k + 1 < len(heads) else len(lines)
        body = "\n".join(lines[i + 1:end]).strip()
        rows.append({"number": int(m.group(1)), "heading": m.group(2).strip(),
                     "index": k + 1, "text": body,
                     "words": len(body.split()), "empty": not body})
    return rows


@parser("json_text_sections")
def json_text_sections(text: str) -> list[dict]:
    """Headed markdown carried inside a JSON record's `text` field -> one row per section.

    Trace evidence arrives as transcript records: a JSON object whose `text`
    holds the whole document, newlines and all, escaped. `markdown_sections`
    reading that file sees one line and no headings, so a document that governs
    the task projects to nothing while the decoy `.md` files beside it project
    cleanly -- which is how a word-count target ends up measuring the wrong
    client's deliverable. Sections and `words` are exactly `markdown_sections`,
    so a target reads the same either way.
    """
    data = json.loads(text)
    if isinstance(data, list):
        data = data[0] if data else {}
    body = data.get("text") if isinstance(data, dict) else None
    if not isinstance(body, str):
        raise ValueError("json_text_sections needs a record with a string 'text' field")
    return markdown_sections(body)


@parser("csv_table")
def csv_table(text: str) -> list[dict]:
    """A delimited table -> one row per record, values left as written."""
    import csv as _csv
    import io as _io
    sample = text[:4096]
    delim = "\t" if sample.count("\t") > sample.count(",") else ","
    rows = []
    for i, row in enumerate(_csv.DictReader(_io.StringIO(text), delimiter=delim), 1):
        clean = {(k or "").strip(): (v or "").strip() for k, v in row.items()}
        clean["row"] = i
        rows.append(clean)
    return rows


@parser("markdown_tables")
def markdown_tables(text: str) -> list[dict]:
    """Pipe tables with explicit headers -> keyed records, preserving row associations.

    Adds _table (1-based table number) and _row (1-based data row). Rejects
    ambiguous headers/ragged rows; ignores fenced examples. Escaped pipes work.
    """
    def cells(line):
        return [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", line.strip().strip("|"))]
    rows, lines, fence = [], [], None
    for line in text.splitlines():
        marker = re.match(r"^\s{0,3}(`{3,}|~{3,})", line)
        if marker:
            token = marker.group(1)
            if fence is None:
                fence = token
            elif token[0] == fence[0] and len(token) >= len(fence) and not line[marker.end():].strip():
                fence = None
            lines.append("")
        else:
            lines.append(line if fence is None else "")
    i, table = 0, 0
    while i + 1 < len(lines):
        if "|" not in lines[i] or not all(re.fullmatch(r":?-{3,}:?", c) for c in cells(lines[i + 1])):
            i += 1
            continue
        headers = cells(lines[i])
        if (len(set(h.casefold() for h in headers)) != len(headers) or not all(headers)
                or set(headers) & {"_table", "_row"}):
            raise ValueError("Markdown table has empty, duplicate or reserved headers")
        if len(cells(lines[i + 1])) != len(headers):
            raise ValueError("Markdown separator does not match the table headers")
        table += 1
        i += 2
        row = 0
        while i < len(lines) and "|" in lines[i] and lines[i].strip():
            values = cells(lines[i])
            if len(values) != len(headers):
                raise ValueError("ragged Markdown table row")
            row += 1
            rows.append({**dict(zip(headers, values)), "_table": table, "_row": row})
            i += 1
    return rows


@parser("jsonl_records")
def jsonl_records(text: str) -> list[dict]:
    """JSON Lines, or a JSON array/object of records."""
    rows = []
    stripped = text.strip()
    from .contracts import strict_json, ContractError
    try:
        data = strict_json(stripped)
    except ContractError:
        rows = [strict_json(line) for line in text.splitlines() if line.strip()]
        if not all(isinstance(row, dict) for row in rows):
            raise ValueError("JSONL rows must be objects")
        return rows
    else:
        if isinstance(data, list):
            if not all(isinstance(row, dict) for row in data):
                raise ValueError("JSON records must be objects")
            return data
        if not isinstance(data, dict):
            raise ValueError("JSON records must be objects")
        for value in data.values():
            if isinstance(value, list) and all(isinstance(v, dict) for v in value):
                return value
        return [data]


@parser("labelled_lines")
def labelled_lines(text: str) -> list[dict]:
    """`Label: value` lines -> {label, value, line}. Registers, specs, briefs."""
    rows = []
    for i, line in enumerate(text.splitlines(), 1):
        m = re.match(r"^\s*[-*]?\s*\*{0,2}([^\W\d_][\w \-/()]{0,80}?)\*{0,2}\s*[:：]\s*(.+?)\s*$",
                     line)
        if m:
            rows.append({"line": i, "label": m.group(1).strip(),
                         "value": m.group(2).strip()})
    return rows


@parser("svg_elements")
def svg_elements(text: str) -> list[dict]:
    """Declared SVG elements and attributes, without rendering or inference.

    Keep source order, duplicates, nearest Markdown heading and ancestor
    attributes. Transforms, CSS and defaults are NOT applied. Nested SVG roots
    and malformed XML are unsupported and fail explicitly.
    """
    import xml.etree.ElementTree as ET
    if re.search(r"<!\s*(?:DOCTYPE|ENTITY)\b", text, re.I):
        raise ValueError("SVG projection does not allow document types or entities")
    blocks = list(re.finditer(r"<svg\b[^>]*>[\s\S]*?</svg\s*>", text, re.I))
    if len(blocks) != len(re.findall(r"<svg\b", text, re.I)):
        raise ValueError("unclosed or nested SVG root")
    rows = []
    offsets, offset, fence = [], 0, None
    for line in text.splitlines(keepends=True):
        marker = re.match(r'^\s*(`{3,}|~{3,})', line)
        if marker:
            token = marker[1]
            if fence is None:
                fence = token
            elif token[0] == fence[0] and len(token) >= len(fence):
                fence = None
        elif fence is None and (heading := re.match(r'^(#{1,6})\s+(.*)', line)):
            offsets.append((offset, heading[2].strip()))
        offset += len(line)
    for index, block in enumerate(blocks, 1):
        try:
            root = ET.fromstring(block.group())
        except ET.ParseError as exc:
            raise ValueError(f"malformed SVG block {index}: {exc}") from exc
        heading = next((name for offset, name in reversed(offsets) if offset <= block.start()), '')
        def walk(element, ancestors):
            tag = element.tag.rsplit('}', 1)[-1]
            rows.append({'svg_index': index, 'section_heading': heading,
                'tag': tag, 'attributes': dict(element.attrib),
                'ancestors': ancestors, 'text': element.text or ''})
            for child in element:
                walk(child, [*ancestors, {'tag': tag, 'attributes': dict(element.attrib)}])
        walk(root, [])
    return rows


_TRANSCRIPT_HEADER = re.compile(
    r"^(?:#{1,6}[ \t]+)?(?:\*\*)?Question[ \t]+(?P<item>\d+)\b[^\r\n]*(?:\r?\n|$)", re.M)


@parser("transcript_answers")
def transcript_answers(text: str) -> list[dict]:
    """Every plain, bold or headed question block, including repeated IDs.

    Rows represent printed blocks, not a distinct-ID set. Consumers asking for
    source coverage must take the union of IDs across captures. Answer letters
    require an explicit A-D label; a prose answer beginning with B is not B.
    """
    rows = []
    headers = list(_TRANSCRIPT_HEADER.finditer(text))
    for i, header in enumerate(headers):
        block = text[header.end():headers[i + 1].start() if i + 1 < len(headers) else len(text)]
        stem = next((line.strip().strip("*") for line in block.splitlines() if line.strip()), "")
        ans = re.search(r"^[ \t]*(?:\*[ \t]+)?\*{0,2}Correct Answer\*{0,2}:\*{0,2}[ \t]*(?:\r?\n)?([^\r\n]+)", block, re.M)
        answer = ans[1].strip().strip("*") if ans else ""
        letter = re.match(r"^([A-Da-d])(?:[.)](?:\s|$)|$)", answer)
        rows.append({"item": int(header["item"]), "stem": stem,
                     "stated_answer": letter[1].lower() if letter else None,
                     "stated_answer_text": answer or None})
    return rows


def _norm_stem(text: str) -> str:
    import unicodedata
    normalized = unicodedata.normalize("NFKC", text or "").casefold()
    return " ".join("".join(c for c in normalized if c.isalnum() or c.isspace()).split())


def stem_overlap(paper: list[dict], others: dict[str, list[dict]]) -> list[dict]:
    """How many of each source's question stems appear in the paper.

    A source that keys a different paper overlaps it zero times, however
    confidently it states its answers. This is the fact that decides which
    supplied documents are evidence about the paper in hand -- and it is written
    in no file, so it has to be computed.
    """
    target = {_norm_stem(r.get("stem") or r.get("text") or "") for r in paper}
    target.discard("")
    rows = []
    for name, source_rows in others.items():
        stems = {_norm_stem(r.get("stem", "")) for r in source_rows}
        stems.discard("")
        shared = len(stems & target)
        rows.append({"source": name, "stems": len(stems), "shared": shared,
                     "keys_this_paper": shared > 0})
    return rows


def join(name: str, left: list[dict], right: list[dict], on: str,
         fields: dict[str, str]) -> list[dict]:
    """Join two projections on a key.

    A join lives here rather than in the expression language because it is the
    one operation that needs both sides at once, and doing it at build time
    keeps every target expression a single-file read.
    """
    keys = list(on) if isinstance(on, (list, tuple)) else [on]
    def key(row):
        return tuple(row.get(k) for k in keys)
    index = {key(r): r for r in right}
    if len(index) != len(right):
        raise ValueError(f"{name}: ambiguous join: duplicate right-hand key {on!r}")
    out = []
    for row in left:
        other = index.get(key(row), {})
        merged = {k: row.get(k) for k in keys}
        for alias, spec in fields.items():
            side, field = spec.split(".", 1)
            merged[alias] = (row if side == "left" else other).get(field)
        out.append(merged)
    return out


def _inside(root: Path, relative: str) -> Path:
    """Resolve a declared path without allowing traversal or symlink escapes.

    `spec["file"]` is written by the designer, so a projection declaring
    `../../solution/submission/audit.json` would read the reference answer
    straight into the task and nothing downstream could tell. Adopted from the
    upstream fork, which spotted the hole in this layer while we had guarded
    only the agent designer's own file tools.
    """
    from .contracts import contained
    return contained(root, relative)


def project(fixture: Path, projections: list[dict]) -> dict[str, list[dict]]:
    """Run every declared projection against the fixture."""
    out: dict[str, list[dict]] = {}
    for index, spec in enumerate(projections):
        if "as" not in spec:
            raise KeyError(
                f"projection {index} declares no 'as' name: {spec!r}. Every "
                "projection needs one -- it is what target expressions read as "
                "their `file`.")
        name = spec["as"]
        if spec.get("op") == "stem_overlap":
            # `sources` maps projection name -> the filename the agent sees, so
            # the derived answer names documents rather than internal projections.
            # Accept a source key with or without the .jsonl suffix. The
            # distinction carries no meaning and costs a repair round-trip
            # every time a designer drops it.
            sources = {}
            for key, label in spec["sources"].items():
                resolved = key if key in out else f"{key}.jsonl"
                if resolved not in out:
                    raise KeyError(
                        f"projection {name!r}: source {key!r} is not declared "
                        f"before it; declared: {sorted(out)}")
                sources[label] = out[resolved]
            out[name] = stem_overlap(out[spec["paper"]], sources)
            continue
        if spec.get("op") == "concat":
            # One corpus spread over several documents. Without this a
            # multi-document section set can only be expressed as one
            # projection per file, which understates its breadth: the model
            # faces the union, not the largest part of it.
            field = spec.get("field", "source")
            rows = []
            for key, label in spec["sources"].items():
                resolved = key if key in out else f"{key}.jsonl"
                if resolved not in out:
                    raise KeyError(
                        f"projection {name!r}: source {key!r} is not declared "
                        f"before it; declared: {sorted(out)}")
                rows.extend({**row, field: label} for row in out[resolved])
            out[name] = rows
            continue
        if spec.get("op") == "join":
            out[name] = join(name, out[spec["left"]], out[spec["right"]],
                             spec["on"], spec["fields"])
            for extra in spec.get("compute", []):
                for row in out[name]:
                    row[extra["field"]] = _compute(extra, row)
            continue
        fn = REGISTRY.get(spec["parser"])
        if fn is None:
            raise KeyError(f"unknown parser {spec['parser']!r}; "
                           f"registered: {sorted(REGISTRY)}")
        out[name] = fn(_inside(fixture, spec["file"]).read_text(errors="replace"))
    return out


def _compute(spec: dict, row: dict):
    kind = spec["kind"]
    if kind == "all_true":
        return all(bool(row.get(f)) for f in spec["fields"])
    if kind == "equal":
        a, b = (row.get(f) for f in spec["fields"])
        return a == b
    if kind == "both_resolved_and_equal":
        a, b = (row.get(f) for f in spec["fields"])
        return bool(row.get(spec["guard"])) and a == b
    raise KeyError(f"unknown computed field kind {kind!r}")


def write(projections: dict[str, list[dict]], dest: Path) -> list[str]:
    dest.mkdir(parents=True, exist_ok=True)
    written = []
    for name, rows in projections.items():
        _inside(dest, name).write_text(
            "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n")
        written.append(name)
    return written


def verify(fixture: Path, projections: list[dict], derived: Path) -> list[str]:
    """Re-run the parsers and report any drift from what is on disk."""
    fresh = project(fixture, projections)
    problems = []
    for name, rows in fresh.items():
        path = _inside(derived, name)
        if not path.is_file():
            problems.append(f"{name}: projection missing on disk")
            continue
        on_disk = [json.loads(line) for line in
                   path.read_text().splitlines() if line.strip()]
        if on_disk != rows:
            problems.append(
                f"{name}: fixture and oracle have drifted "
                f"({len(on_disk)} rows stored, {len(rows)} regenerated)")
    return problems
