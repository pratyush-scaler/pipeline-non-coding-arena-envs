"""Reproducible offline Harbor package, with disjoint agent/verifier contexts."""
from __future__ import annotations
import shutil
from pathlib import Path
from .contracts import contained

# Official Docker multi-platform index resolved 2026-09-20. Updates are explicit
# version changes and invalidate every measurement through the artifact hash.
BASE_IMAGE = "python:3.11-slim-bookworm@sha256:a36c24f9cbdf4fd0f52d67f0823eeac19c2028c637cecc392d97f980d4fec56b"

#: Node for the calibration harness CLIs -- Claude Code 2.1.283 requires Node
#: >= 22 and Debian bookworm ships 18 -- copied from the official image pinned
#: by its multi-platform index digest (v22.23.3, npm 10.9.9; resolved
#: 2026-09-26). Like BASE_IMAGE, an update is an explicit version change.
NODE_IMAGE = "node:22-bookworm-slim@sha256:43ac6c60b8f89723f746e8a92ce91abd5017e627ce1ddfe4238355d3a30b772c"

#: Spec E4: "Define available tools and actions with machine-readable schemas."
#: Outside the build context (`environment/.dockerignore` admits only the
#: Dockerfile and `files/`), so the image the agent runs in is unchanged.
TOOL_SCHEMA = "environment/tools.json"
TOOL_SCHEMA_ID = "arena-pipeline/tool-schema/1"
INPUTS, OUTPUTS = "/app/environment/files", "/app/deliverables"

#: The one action Harbor 0.22.0's Terminus-2 exposes: a JSON reply whose
#: `commands` are tmux keystrokes (harbor/agents/terminus_2/templates/
#: terminus-json-plain.txt and terminus_json_plain_parser.py). Required and
#: optional fields, defaults and types are Harbor's, not ours.
TERMINUS_2_ACTION = {
    "name": "terminus_2_keystrokes",
    "description": ("Send a batch of keystrokes to the agent's tmux session and read the "
                    "resulting terminal screen. Each command's keystrokes are sent verbatim "
                    "(end a command with \\n to run it; tmux escapes such as C-c are "
                    "accepted); duration is the seconds to wait before the next command."),
    "input_schema": {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "required": ["analysis", "plan", "commands"],
        "properties": {
            "analysis": {"type": "string"},
            "plan": {"type": "string"},
            "commands": {"type": "array", "items": {
                "type": "object", "required": ["keystrokes"],
                "properties": {"keystrokes": {"type": "string"},
                               "duration": {"type": "number", "default": 1.0}}}},
            "task_complete": {"type": ["boolean", "string"], "default": False},
        },
    },
}


#: The calibration harnesses' tool surfaces (user, 2026-09-26: Fable 5.1 in
#: Claude Code, GPT 6 Astra in Codex). Each harness defines its own built-in
#: tools and their input schemas; the package records which harness, at which
#: pinned version, exposes them -- the schemas themselves are the CLI's, and
#: retyping them here would be a second, drifting copy.
def _policy():
    from .. import policy
    return policy


def harness_tools() -> list[dict]:
    from .. import policy
    return [{"model": model, "agent": agent, "version": policy.HARNESS_VERSIONS[agent],
             "reasoning_effort": policy.SPEC_CALIBRATION_EFFORT,
             "tools": "built-in tool set of the pinned CLI (its own input schemas)",
             "agent_phase_network": {"mode": "allowlist",
                                     "hosts": list(policy.HARNESS_API_HOSTS[agent])}}
            for model, agent in policy.CALIBRATION_HARNESS.items()]


def tool_schema(spec: dict) -> dict:
    """The machine-readable tool and workspace contract for one package."""
    outputs = sorted({(o["step"], o["file"]) for o in spec.get("outputs", [])
                      if isinstance(o, dict) and o.get("step") and o.get("file")})
    return {
        "schema": TOOL_SCHEMA_ID,
        "harness": {"framework": "harbor", "framework_version": "0.22.0",
                    "calibration": harness_tools(),
                    # A documented substitute model runs in its provider's harness.
                    "substitutes_by_provider": dict(_policy().PROVIDER_HARNESS)},
        "tools": harness_tools(),
        "workspace": {"user": "agent", "network": "none",
                      "agent_phase_network": "model API host only (see tools)",
                      "read_only": [INPUTS], "writable": [OUTPUTS],
                      "outputs": [{"step": step, "path": f"{OUTPUTS}/{file}"}
                                  for step, file in outputs]},
    }


def tool_schema_problems(bundle: Path) -> list[str]:
    """Why this package does not ship a valid tool schema; [] if it does."""
    import json
    import tomllib
    bundle = Path(bundle)
    path = bundle / TOOL_SCHEMA
    if not path.is_file():
        return [f"{TOOL_SCHEMA} is missing: the package declares no machine-readable tool schema"]
    try:
        doc = json.loads(path.read_text())
    except (OSError, ValueError) as exc:
        return [f"{TOOL_SCHEMA} is not JSON: {exc}"]
    issues = []
    if not isinstance(doc, dict) or doc.get("schema") != TOOL_SCHEMA_ID:
        return [f"{TOOL_SCHEMA} is not a {TOOL_SCHEMA_ID} document"]
    if doc.get("tools") != harness_tools():
        issues.append(f"{TOOL_SCHEMA} does not declare the calibration harnesses (Claude Code, "
                      "Codex) at their pinned versions; re-package this bundle")
    space = doc.get("workspace") if isinstance(doc.get("workspace"), dict) else {}
    if space.get("read_only") != [INPUTS] or space.get("writable") != [OUTPUTS] \
            or space.get("network") != "none":
        issues.append(f"{TOOL_SCHEMA} workspace contract must be {INPUTS} read-only, "
                      f"{OUTPUTS} writable, no network")
    outputs = space.get("outputs")
    if not isinstance(outputs, list) or any(
            not isinstance(o, dict) or not str(o.get("path", "")).startswith(OUTPUTS + "/")
            for o in outputs):
        issues.append(f"{TOOL_SCHEMA} declares an output outside {OUTPUTS}")
    try:
        meta = tomllib.loads((bundle / "task.toml").read_text()).get("metadata") or {}
    except (OSError, ValueError) as exc:
        return issues + [f"task.toml is unreadable: {exc}"]
    if meta.get("tool_schema") != TOOL_SCHEMA:
        issues.append(f"task.toml [metadata].tool_schema must reference {TOOL_SCHEMA!r}")
    return issues


def agent_dockerfile() -> str:
    """The agent image: Python base, pinned apt snapshot, pinned Node and harness CLIs.

    The harness layers come before `COPY files/`, so every task shares them in
    the build cache. Harbor finds each CLI at its pinned version and skips its
    own run-time installer, which would need internet the agent does not have.
    """
    from .. import policy
    versions = policy.HARNESS_VERSIONS
    return (
        f"FROM {NODE_IMAGE} AS node\n"
        f"FROM {BASE_IMAGE}\n"
        "RUN rm -f /etc/apt/sources.list.d/debian.sources && "
        "printf 'deb [check-valid-until=no] https://snapshot.debian.org/archive/debian/20260919T000000Z bookworm main\\n' > /etc/apt/sources.list && "
        "apt-get -o Acquire::Check-Valid-Until=false update && "
        "apt-get install -y --no-install-recommends tmux=3.3a-3 ripgrep procps ca-certificates && "
        "rm -rf /var/lib/apt/lists/*\n"
        "COPY --from=node /usr/local/bin/node /usr/local/bin/node\n"
        "COPY --from=node /usr/local/lib/node_modules/npm /usr/local/lib/node_modules/npm\n"
        "RUN ln -s ../lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm && "
        "ln -s ../lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx && "
        "npm install -g --no-audit --no-fund "
        f"@anthropic-ai/claude-code@{versions['claude-code']} @openai/codex@{versions['codex']} && "
        "npm cache clean --force && claude --version && codex --version\n"
        "RUN useradd --create-home --uid 1000 agent\n")


def harness_dockerfile_problems(bundle: Path) -> list[str]:
    """Why this package's agent image cannot host the calibration harnesses."""
    path = Path(bundle) / "environment/Dockerfile"
    try:
        text = path.read_text()
    except OSError as exc:
        return [f"environment/Dockerfile is unreadable: {exc}"]
    if not text.startswith(agent_dockerfile()):
        return ["environment/Dockerfile does not bake in the pinned calibration harnesses "
                "(Node 22, Claude Code, Codex); re-package this bundle"]
    return []


def write_native(spec: dict, bundle: Path) -> None:
    (bundle / "environment/Dockerfile").write_text(
        agent_dockerfile() +
        "WORKDIR /app\nCOPY files/ /app/environment/files/\n"
        "RUN chmod -R a-w /app/environment && mkdir -p /app/deliverables "
        "&& chown agent:agent /app/deliverables\n"
        "USER agent\nCMD [\"sleep\", \"infinity\"]\n")
    (bundle / "environment/.dockerignore").write_text("*\n!Dockerfile\n!files/\n!files/**\n")
    (bundle / "tests/Dockerfile").write_text(
        f"FROM {BASE_IMAGE}\nWORKDIR /app\nCOPY . /tests/\n"
        "RUN mkdir -p /logs/verifier /app/deliverables /app/environment/files\n"
        "CMD [\"sleep\", \"infinity\"]\n")
    script = bundle / "tests/test.sh"
    script.write_text("#!/bin/sh\nset -eu\nmkdir -p /logs/verifier\n"
                      "export ARENA_REWARD=/logs/verifier/reward.json\n"
                      "export ARENA_DETAILS=/logs/verifier/reward-details.json\n"
                      "python3 /tests/criteria.py > /logs/verifier/arena-grade.json\n")
    script.chmod(0o755)
    import json
    from ..naming import set_metadata
    (bundle / TOOL_SCHEMA).write_text(json.dumps(tool_schema(spec), indent=2) + "\n")
    toml = bundle / "task.toml"
    if toml.is_file():                      # absent: structure refuses the package anyway
        toml.write_text(set_metadata(toml.read_text(), "tool_schema", TOOL_SCHEMA))
    for step in spec["steps"]:
        dest = bundle / "steps" / step["name"] / "solution"
        if dest.exists():
            shutil.rmtree(dest)
        (dest / "submission").mkdir(parents=True)
        files = [o["file"] for o in spec.get("outputs", []) if o["step"] == step["name"]]
        if not spec.get("outputs"):
            files = sorted({c.get("actual", {}).get("file") for c in spec["checks"]
                            if c.get("step") == step["name"] and c.get("actual", {}).get("file")})
        for file in files:
            source = contained(bundle / "solution/submission", file)
            if source.is_file():
                target = contained(dest / "submission", file)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
        # A deriving reference, not a copy. `cp -R /solution/submission/.` is
        # the exact case Harbor's `hardcoded_solution` criterion fails, and the
        # spec asks for a *scripted* solution. `solution.stage` writes one that
        # projects the fixture and evaluates the declared targets. The stored
        # submission above stays: it is what `assurance` and the source
        # counterfactuals compare against, and it is the fallback if a step has
        # no field-assembling objectives to derive from.
        from . import solution as reference
        staged = reference.stage(bundle, spec, step["name"], dest)
        if not staged["objectives"]:
            solve = dest / "solve.sh"
            solve.write_text('#!/bin/sh\nset -eu\nmkdir -p /app/deliverables\n'
                             'cp -R /solution/submission/. /app/deliverables/\n')
            solve.chmod(0o755)
