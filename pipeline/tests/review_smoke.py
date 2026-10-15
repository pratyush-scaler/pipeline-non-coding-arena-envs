"""Opt-in independent review: a plausible but incorrect derived target must be rejected."""
import argparse
import json
from pathlib import Path
from pipeline.artifacts import atomic_json
from pipeline.author.build import build
from pipeline.cli import load_keys
from pipeline.review import review
from pipeline.tests.test_production import synthetic_bundle


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    root = args.out.resolve()
    root.mkdir(parents=True, exist_ok=False)
    bundle = synthetic_bundle(root)
    spec = json.loads((bundle / "authoring/spec.json").read_text())
    spec["_producer"] = {"model": "claude-opus-5", "effort": "xhigh"}
    # A reference-consistent but semantically wrong task: count instead of sum.
    for check in spec["checks"]:
        if check["id"] == "total_effort":
            check["target"]["op"] = "count"
            check["target"].pop("field", None)
    spec["solution"]["summary.json"]["total_effort"] = 2
    build(spec, bundle)
    load_keys(prompt_if_missing=False)
    report = review(bundle, "gpt-5.6-sol")
    doc = json.loads((bundle / report["work_dir"] / "deliverables/review.json").read_text())
    caught = any(r.get("id") == "total_effort" and r.get("verdict") == "revise" for r in doc.get("checks", []))
    expected = ("semantic reviewer requested revision", "unresolved review findings:")
    valid = all(error.startswith(expected) or ": check not independently justified" in error
                for error in report["errors"])
    result = {"passed": caught and not report["ok"] and valid, "verdict": doc.get("verdict"),
              "execution_evidence_valid": valid,
              "caught_wrong_derived_target": caught, "errors": report["errors"]}
    atomic_json(root / "validation.json", result)
    print(json.dumps(result), flush=True)
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
