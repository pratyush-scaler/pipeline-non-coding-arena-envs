"""One naming convention, applied everywhere Arena sees a task.

    a_f3_<task-name>

The faithfulness level is part of the name, so a reviewer reading a task list,
a results table or a directory tree knows what kind of environment each one is
without opening its ledger. The same reason the delivery folders are
`F3-replay/` rather than `rich/`: the two Arena batch criteria that key on
faithfulness were previously invisible until someone joined four artefacts.

One constraint shapes the exact form. Harbor validates `[task] name` against

    ^[a-zA-Z0-9][a-zA-Z0-9._-]*/[a-zA-Z0-9][a-zA-Z0-9._-]*$

so the org prefix and its slash are mandatory -- `a_f3_x` alone is rejected
by `harbor tasks-check`, which the spec requires to pass on 100% of tasks.
Underscores are fine. Harbor exposes the segment after the slash as
`short_name`, which is what task lists and result tables display, so:

    full name   arena/a_f3_loksewa-key-reconciliation
    short_name        a_f3_loksewa-key-reconciliation   <- the convention
    directory         a_f3_loksewa-key-reconciliation
    delivered at      F3-replay/a_f3_loksewa-key-reconciliation/

The level in the name is a claim, and claims here are measured. `apply` refuses
to name a task at a level its ledger does not support, because a name is the
one piece of provenance that travels into every downstream table.
"""
from __future__ import annotations

import re
from pathlib import Path


#: Harbor's org segment. Lowercase, matching the existing package registry.
ORG = "arena"

#: The convention, as a pattern, so it can be checked rather than trusted.
SHORT_NAME = re.compile(r"^a_f[0-3]_[a-z0-9]+(?:-[a-z0-9]+)*$")

LEVELS = ("F0", "F1", "F2", "F3")


def slug(text: str) -> str:
    """The `<task-name>` segment: lowercase, hyphen-separated, no level prefix."""
    text = re.sub(r"^a_f[0-3]_", "", str(text))
    text = re.sub(r"^arena[/_-]", "", text, flags=re.IGNORECASE)
    # Bundles have historically been named `a-123-content-marketing-planning`;
    # the rank prefix is an artefact of our own ordering and means nothing to
    # a reader, so it does not travel into the delivered name.
    text = re.sub(r"^a-?\d+-", "", text)
    text = re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-").lower()
    return text or "task"


def short_name(level: str, name: str) -> str:
    """`a_f3_<task-name>`."""
    level = str(level).upper()
    if level not in LEVELS:
        raise ValueError(f"faithfulness level must be one of {LEVELS}, not {level!r}")
    return f"a_{level.lower()}_{slug(name)}"


def package_name(level: str, name: str) -> str:
    """The Harbor `[task] name`, whose `short_name` is the convention above."""
    return f"{ORG}/{short_name(level, name)}"


def parse(name: str) -> dict | None:
    """Recover the level and task name from either form, or None."""
    candidate = name.split("/")[-1]
    if not SHORT_NAME.match(candidate):
        return None
    _, level, rest = candidate.split("_", 2)
    return {"level": level.upper(), "task": rest, "short_name": candidate}


def problems(bundle: Path, level: str | None = None) -> list[str]:
    """Is this bundle named to convention, and does its name match its ledger?"""
    import tomllib

    from .author.contracts import strict_json

    issues = []
    try:
        config = tomllib.loads((Path(bundle) / "task.toml").read_text())
    except (OSError, ValueError) as exc:
        return [f"task.toml is unreadable: {exc}"]

    name = (config.get("task") or {}).get("name", "")
    parsed = parse(name)
    if parsed is None:
        issues.append(
            f"task name {name!r} does not follow a_f<level>_<task-name>; "
            f"expected something like {package_name('F2', Path(bundle).name)!r}")
        return issues

    if level is None:
        ledger_path = Path(bundle) / "provenance/ledger.json"
        if ledger_path.is_file():
            level = strict_json(ledger_path.read_text()).get("faithfulness_level")
    if level and parsed["level"] != str(level).upper():
        issues.append(
            f"task name claims faithfulness {parsed['level']} but the ledger "
            f"measures {str(level).upper()}. The level in the name is the one "
            "piece of provenance that reaches every downstream table")
    stamped = (config.get("metadata") or {}).get(LEVEL_KEY)
    if stamped is not None and str(stamped).upper() != parsed["level"]:
        issues.append(f"task.toml [metadata].{LEVEL_KEY} is {stamped!r} but the "
                      f"task name claims {parsed['level']}")
    return issues


def apply(bundle: Path, level: str) -> dict:
    """Rewrite `[task] name` to the convention for this bundle's measured level.

    Called once the ledger exists and the level has been assigned -- after
    `build`, before any gate, hash or campaign. Renaming later would invalidate
    the task identity every piece of retained evidence is bound to.
    """
    import tomllib

    from .artifacts import identity

    bundle = Path(bundle)
    path = bundle / "task.toml"
    if level not in LEVELS:
        return {"changed": False, "name": None, "skipped": f"unsupported faithfulness {level}"}
    if not path.is_file():
        # Nothing to rename yet. Renaming is not a correctness step in its own
        # right -- `problems()` runs in the grade phase and again at release and
        # blocks a task whose name does not carry its measured level -- so a
        # missing package must not kill a build that is otherwise sound.
        return {"changed": False, "name": None, "skipped": "no task.toml"}
    text = path.read_text()
    before = tomllib.loads(text)["task"]["name"]
    after = package_name(level, bundle.name)
    if before == after:
        return {"changed": False, "name": after}
    path.write_text(rename_text(text, after))
    try:
        sha = identity(bundle)
    except ValueError:
        sha = None                 # an incomplete bundle has no identity yet
    return {"changed": True, "previous": before, "name": after,
            "artifact_sha256": sha}


def rename_text(text: str, name: str) -> str:
    """`task.toml` text with only `[task] name` replaced.

    `[[steps]]` entries have their own names and are left alone. Kept separate
    from `apply` so `deliverable` can re-derive a delivered task.toml from the
    accepted one and prove the rename was the only change.
    """
    pattern = re.compile(r"(\[task\][^\[]*?\bname\s*=\s*)(\"[^\"]*\")", re.S)
    updated, count = pattern.subn(lambda m: m.group(1) + json_quote(name), text, count=1)
    if count != 1:
        raise ValueError("could not locate the [task] name in task.toml")
    return updated


def json_quote(value: str) -> str:
    import json
    return json.dumps(value, ensure_ascii=False)


#: The `[metadata]` key that carries the task's measured faithfulness level in a
#: delivered `task.toml` (spec M4: tagged per environment AND per task; the
#: ledger is the environment's tag, this is the task's).
LEVEL_KEY = "faithfulness_level"


def set_metadata(text: str, key: str, value: str) -> str:
    """`task.toml` text with `[metadata] <key> = "<value>"` set and nothing else.

    Inserts the key directly under the `[metadata]` header (appending the table
    when there is none), or replaces an existing single-line string value.
    Anything else is refused rather than guessed at, and the result is parsed
    and compared with the input so that one key is provably the only change.
    """
    import tomllib

    if not re.fullmatch(r"[a-z_][a-z0-9_]*", key) or not isinstance(value, str):
        raise ValueError(f"not a plain metadata key/value: {key!r}")
    before = tomllib.loads(text)
    line = f"{key} = {json_quote(value)}"
    header = re.search(r"^\[metadata\][ \t]*$", text, re.M)
    if header is None:
        if "metadata" in before:
            raise ValueError("[metadata] is not a plain table header in task.toml")
        updated = text + ("" if not text or text.endswith("\n") else "\n") \
            + f"\n[metadata]\n{line}\n"
    elif key in (before.get("metadata") or {}):
        pattern = re.compile(rf"^{key}[ \t]*=[ \t]*\"[^\"\\\n]*\"[ \t]*$", re.M)
        tail, count = pattern.subn(lambda _: line, text[header.end():], count=1)
        if count != 1:
            raise ValueError(f"[metadata].{key} is not a single-line string")
        updated = text[:header.end()] + tail
    else:
        updated = text[:header.end()] + "\n" + line + text[header.end():]
    expected = dict(before, metadata={**(before.get("metadata") or {}), key: value})
    if tomllib.loads(updated) != expected:
        raise ValueError(f"setting [metadata].{key} would change more than that key")
    return updated


def delivered_toml(text: str, name: str, level: str) -> str:
    """The delivered `task.toml`: the accepted text renamed, with its level stamped.

    The one definition of delivery's rewrite, so `deliver` writes it and
    `deliverable.acceptance_problems` re-derives it from the accepted original.
    """
    return set_metadata(rename_text(text, name), LEVEL_KEY, str(level).upper())


def unique_names(items: list[tuple[str, str]]) -> dict[str, str]:
    """Assign a distinct short name to each (level, bundle_name) pair.

    `slug` deliberately drops the `a-NNN-` rank prefix, because the rank is an
    artefact of our own ordering and means nothing to a reader. Measured on the
    real `envs-cat` tree that produces collisions: `a-002-brand-consulting` and
    `a-003-brand-consulting` both become `a_f2_brand-consulting`, and two
    different tasks cannot share a delivery path or a Harbor package name.

    Where a name is unique it is left clean. Where it is not, every member of
    the colliding group keeps its original rank as a discriminator -- suffixing
    only the later ones would make the first task's name depend on what else
    happened to be in the batch.
    """
    groups: dict[str, list[str]] = {}
    for level, name in items:
        groups.setdefault(short_name(level, name), []).append(name)

    out: dict[str, str] = {}
    for base, names in groups.items():
        if len(names) == 1:
            out[names[0]] = base
            continue
        for name in names:
            match = re.match(r"^a-?(\d+)-", name)
            suffix = match.group(1) if match else slug(name)[:4]
            out[name] = f"{base}-{suffix}"
    return out


def collisions(items: list[tuple[str, str]]) -> dict[str, list[str]]:
    """Bundles that would share a name, before disambiguation."""
    groups: dict[str, list[str]] = {}
    for level, name in items:
        groups.setdefault(short_name(level, name), []).append(name)
    return {base: sorted(names) for base, names in groups.items() if len(names) > 1}
