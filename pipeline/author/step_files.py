"""Which fixture files a step may see, so a later step's evidence can be withheld.

Every bundle shipped one fixture directory, copied whole into the agent's
workspace at every step (`environment/Dockerfile`: `COPY files/ ...`, and
`calibrate/agent.rollout`: `copytree(fixture, source)`). A two-step task
therefore handed the agent step 2's evidence during step 1.

Usually that is harmless, but not always. a-293's step 2 reveals that "the build
log you were given was not the last run" -- and the later run's log sat in the
fixture from the first moment. a-206 excludes `sources/post_cutoff/` from step 1
in prose while the directory is on disk the whole time. `env.step_isolation`
reports both, and neither could be repaired by editing the bundle: there was
nowhere else to put the file.

A spec now declares the withholding:

    "step_files": {"02-revision": ["sources/post_cutoff/maintenance_record.json"]}

`build` moves those paths out of `environment/files/` into
`environment/step-files/<step>/`, and a step's workspace is the base fixture
plus the overlays of that step and every step before it. Files are therefore
cumulative: step 2 still sees everything step 1 saw, which is what a revision
task means.

Withholding is a promise about visibility, not about grading. The grader reads
the whole fixture as it always did, so a check over a withheld file still works;
what changes is only when the agent can read it.
"""
from __future__ import annotations

import json
from pathlib import Path

#: Where `build` puts the files a step withholds. Outside `environment/files/`,
#: so the one directory the Dockerfile copies no longer carries them.
STEP_FILES = "environment/step-files"


def declared(spec: dict) -> dict[str, list[str]]:
    """`{step: [fixture-relative path, ...]}`, normalised and order-stable.

    A path is stored exactly as it sits under `environment/files/`. Anything
    that is not a plain relative path is dropped rather than guessed at: a
    silently mis-parsed withholding would put a file back in step 1 while the
    spec claimed otherwise, which is the failure this module exists to prevent.
    """
    raw = spec.get("step_files")
    if not isinstance(raw, dict):
        return {}
    out: dict[str, list[str]] = {}
    for step, paths in raw.items():
        if not isinstance(step, str) or not isinstance(paths, (list, tuple)):
            continue
        clean = []
        for path in paths:
            if not isinstance(path, str):
                continue
            rel = path.strip()
            # Reject BEFORE normalising. `lstrip("./")` strips any leading "."
            # or "/" character, so it silently turns "../evil" into "evil" and
            # a traversal check placed after it never fires.
            if not rel or rel.startswith("/") or ".." in Path(rel).parts:
                continue
            rel = rel[2:] if rel.startswith("./") else rel
            if not rel or rel.startswith("/") or ".." in Path(rel).parts:
                continue
            clean.append(rel)
        if clean:
            out[step] = sorted(dict.fromkeys(clean))
    return out


def withheld_from(spec: dict, step: str, order: list[str]) -> list[str]:
    """Paths a given step must NOT see: those released by any LATER step.

    `order` is the task's step sequence. A step sees its own overlay and every
    earlier one, so only the future is withheld.
    """
    schedule = declared(spec)
    if step not in order:
        return sorted({p for paths in schedule.values() for p in paths})
    later = order[order.index(step) + 1:]
    return sorted({p for name in later for p in schedule.get(name, ())})


def materialise(fixture: Path, destination: Path, withhold: list[str]) -> list[str]:
    """Copy the fixture for one step, omitting the paths that step may not see.

    Withholding at copy time rather than relocating the files keeps two
    properties that matter. `build` states it never touches the fixture, so
    moving documents out of `environment/files/` would break that contract and
    make a rebuild non-idempotent -- the second run would look for files the
    first had already moved. And the GRADER still reads the complete fixture, so
    a check over a withheld document keeps working; only the agent's view of it
    is deferred.

    Returns the paths actually omitted, so a caller can record what the agent
    could not see rather than assume the list applied cleanly.
    """
    import shutil

    fixture, destination = Path(fixture), Path(destination)
    wanted = {w.rstrip("/") for w in withhold}
    omitted: list[str] = []

    def ignore(directory, names):
        here = Path(directory).relative_to(fixture)
        drop = set()
        for name in names:
            rel = (here / name).as_posix()
            if rel in wanted:
                drop.add(name)
                omitted.append(rel)
        return drop

    shutil.copytree(fixture, destination, ignore=ignore)
    return sorted(omitted)


def plan(bundle: Path) -> dict:
    """What each step sees, for a reviewer and for the step-isolation gate."""
    bundle = Path(bundle)
    spec_path = bundle / "authoring/spec.json"
    if not spec_path.is_file():
        return {}
    spec = json.loads(spec_path.read_text())
    schedule = declared(spec)
    if not schedule:
        return {}
    steps = [s.get("name") for s in (spec.get("steps") or []) if isinstance(s, dict)]
    return {"schedule": schedule,
            "withheld_from": {name: withheld_from(spec, name, steps) for name in steps}}
