"""Execute the exported verifier in a clean process, never import the live grader."""
from __future__ import annotations

import math
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from .author.contracts import strict_json, contained


def exported_grade(bundle: Path, submitted: Path, step: str, source: Path | None = None) -> dict:
    with tempfile.TemporaryDirectory(prefix="arena-grade-") as tmp:
        root = Path(tmp)
        for path in (bundle / "tests").rglob("*"):
            contained(bundle / "tests", path.relative_to(bundle / "tests").as_posix())
        shutil.copytree(bundle / "tests", root / "tests", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        # Only the reviewed data interpreter may execute on the trusted host.
        # A modified/custom grader must be reviewed or run in native isolation.
        from .author.build import CRITERIA_RUNNER
        from .author import runtime
        expected = {"criteria.py": CRITERIA_RUNNER.encode(),
                    **{f"{runtime.PACKAGE}/{rel}": content
                       for rel, content in runtime.expected().items()}}
        for rel, content in expected.items():
            path = root / "tests" / rel
            if not path.is_file() or path.read_bytes() != content:
                raise RuntimeError(f"unaudited or stale host evaluator: {rel}; rebuild before local execution")
        for path in (root / "tests").glob("*.py"):
            if path.name != "criteria.py":
                raise RuntimeError("unreviewed Python module can shadow host verifier imports")
        reward = root / "reward.json"
        env = {"PATH": os.defpath, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": "",
               "ARENA_SOURCE": str((source or bundle / "environment/files").resolve()),
               "ARENA_SUBMITTED": str(submitted.resolve()), "ARENA_STEP": step,
               "ARENA_REWARD": str(reward)}
        proc = subprocess.run([sys.executable, "-s", str(root / "tests/criteria.py")],
                              cwd=root, env=env, capture_output=True, text=True, timeout=120)
        if proc.returncode:
            raise RuntimeError(f"exported grader failed: {proc.stderr[-1500:]}")
        result = strict_json(proc.stdout)
        score = strict_json(reward.read_text()).get("reward")
        if type(score) not in (int, float) or not math.isfinite(score) or not 0 <= score <= 1:
            raise ValueError("grader produced invalid reward")
        if result.get("reward") != score or not isinstance(result.get("checks"), dict):
            raise ValueError("grader details disagree with reward")
        return result
