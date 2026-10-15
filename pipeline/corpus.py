"""A local release catalog: related tasks cannot silently become new releases.

Session identity and weighted exact source overlap are conservative family
signals. They do not prove semantic novelty; the independent critic does that.
"""
from __future__ import annotations
import os
from pathlib import Path
from .artifacts import atomic_json, bundle_lock, identity
from .author.contracts import strict_json


def registry_root() -> Path:
    return Path(os.environ.get("ARENA_RELEASE_REGISTRY", str(
        Path(__file__).resolve().parents[1] / "pipeline-artifacts/releases"))).resolve()


def signature(bundle: Path) -> dict:
    import hashlib
    spec = strict_json((bundle / "authoring/spec.json").read_text())
    source = spec.get("source", {})
    files = {}
    for path in (bundle / "environment/files").rglob("*"):
        if path.is_symlink():
            raise ValueError("source family cannot contain symlinks")
        if path.is_file():
            raw = path.read_bytes()
            files[hashlib.sha256(raw).hexdigest()] = len(raw)
    return {"artifact_sha256": identity(bundle), "session_id": source.get("session_id"),
            "fixture_hashes": files, "bundle": str(bundle.resolve())}


def related(left: dict, right: dict) -> bool:
    if left.get("session_id") and left["session_id"] == right.get("session_id"):
        return True
    a, b = left["fixture_hashes"], right["fixture_hashes"]
    denominator = min(sum(a.values()), sum(b.values()))
    return bool(denominator and sum(a[h] for h in a.keys() & b.keys()) / denominator >= .8)


def problems(candidate: dict, registry: Path) -> list[str]:
    errors = []
    for path in registry.glob("*.json"):
        other = strict_json(path.read_text())
        if other.get("artifact_sha256") != candidate["artifact_sha256"] and related(candidate, other):
            errors.append(f"related task is already released: {path.stem}; retire/supersede it explicitly before publishing this version")
    return errors


def delivered_copy_of(peer: Path, artifact_sha256: str) -> bool:
    """Is `peer` a delivered copy of exactly this task version?

    Delivery rewrites two files inside the identity (the package name and the
    ledger's level), so frozen bytes no longer match the source. The copy is
    still this task, not a same-source competitor: its receipt's accepted
    inventory hashes to `artifact_sha256`, and every other file is still
    byte-identical to it (the proof `deliverable.acceptance_problems` makes).
    """
    import hashlib
    import json
    from .artifacts import inventory
    receipt = Path(peer) / "verification/delivery.json"
    if not receipt.is_file():
        return False
    try:
        source = strict_json(receipt.read_text()).get("source_inventory")
        current = inventory(peer)
    except (OSError, ValueError):
        return False
    if not isinstance(source, dict):
        return False
    digest = hashlib.sha256(json.dumps(source, sort_keys=True, separators=(",", ":"))
                            .encode()).hexdigest()
    rewritten = {"task.toml", "provenance/ledger.json"}
    return digest == artifact_sha256 and all(
        source.get(rel) == current.get(rel) for rel in set(source) | set(current)
        if rel not in rewritten)


def source_briefs(session_id: str, bundle: Path, workspace: Path | None = None) -> dict:
    """Give an author same-session questions before a new world is constructed.

No reference answers, target expressions or solver trajectories are exposed.
This bounded preflight cannot replace the semantic novelty review.
"""
    from .config import bundle_paths
    workspace = workspace or Path(__file__).resolve().parents[1]
    roots = [root for root in workspace.glob("envs*") if root.is_dir()]
    roots += [workspace / "reference", workspace / "reference/prior-delivery"]
    seen, briefs = set(), []
    for root in roots:
        candidates = set(bundle_paths(root)) | {entry.parent for entry in root.glob("*/task.toml")}
        for peer in sorted(candidates):
            if peer.resolve() == bundle.resolve() or not (peer / "authoring/spec.json").is_file():
                continue
            spec = strict_json((peer / "authoring/spec.json").read_text())
            if spec.get("source", {}).get("session_id") != session_id:
                continue
            questions = [decision["question"] for decision in (spec.get("quality") or {}).get("decisions", [])
                         if isinstance(decision, dict) and isinstance(decision.get("question"), str)]
            brief = {"name": peer.name, "novelty": spec.get("novelty"), "questions": questions}
            key = (brief["novelty"], tuple(questions))
            if key not in seen:
                seen.add(key)
                briefs.append(brief)
    return {"session_id": session_id, "same_session_designs": len(briefs),
            "peers": briefs[:8], "truncated": len(briefs) > 8,
            "basis": "same-session professional questions only; semantic review remains required"}


def _retained_predecessor_paths(bundle: Path, predecessors: set[str]) -> list[Path]:
    import re

    receipt = bundle / 'provenance/retained-ancestry.json'
    if not receipt.is_file():
        return []
    retained = strict_json(receipt.read_text())
    paths = retained.get('retained_paths')
    artifacts = retained.get('retained_artifacts')
    if (retained.get('schema') != 'arena-pipeline/predecessor-retention/1'
            or not isinstance(paths, dict) or not isinstance(artifacts, list)
            or any(not isinstance(value, str) or not re.fullmatch(r'[0-9a-f]{64}', value)
                   for value in artifacts)
            or len(set(artifacts)) != len(artifacts) or set(paths) != set(artifacts)
            or not predecessors <= set(paths)):
        raise ValueError('invalid exact predecessor retention receipt')
    result = []
    for fingerprint in sorted(predecessors):
        value = paths[fingerprint]
        if not isinstance(value, str) or not Path(value).is_absolute():
            raise ValueError('retained predecessor must identify an absolute archive path')
        path = Path(value)
        if (path.resolve() == bundle.resolve() or not (path / 'authoring/spec.json').is_file()
                or not (path / 'task.toml').is_file()):
            raise ValueError('retained predecessor is missing or changed')
        if identity(path) != fingerprint:
            raise ValueError('retained predecessor is missing or changed')
        result.append(path)
    return result


def review_context(bundle: Path, workspace: Path | None = None) -> dict:
    """Retrieve source-related and textually similar peers for the critic."""
    import re
    from .config import bundle_paths
    workspace = workspace or Path(__file__).resolve().parents[1]
    candidate = signature(bundle)
    lineage_path = bundle / 'provenance/replacement.json'
    predecessors = set()
    if lineage_path.exists():
        lineage = strict_json(lineage_path.read_text())
        values = lineage.get('predecessors')
        if (lineage.get('schema') != 'arena-pipeline/replacement/1'
                or not isinstance(lineage.get('reason'), str) or not lineage['reason'].strip()
                or not isinstance(values, list) or not 1 <= len(values) <= 8
                or any(not isinstance(v, str) or not re.fullmatch(r'[0-9a-f]{64}', v) for v in values)
                or len(set(values)) != len(values)):
            raise ValueError('invalid version-bound replacement declaration')
        predecessors = set(values)
    spec = strict_json((bundle / "authoring/spec.json").read_text())
    def words(value):
        return set(re.findall(r"\w+", str(value).casefold()))
    vocabulary = words(spec.get("novelty", "") + " " + spec.get("instruction", ""))
    peers = []
    retained = _retained_predecessor_paths(bundle, predecessors)
    roots = [p for p in workspace.glob("envs*") if p.is_dir()]
    roots += [workspace / "reference", workspace / "reference/prior-delivery"]
    roots += [peer.parent for peer in retained]
    seen, seen_artifacts, found_predecessors = set(), set(), set()
    for root in roots:
        candidates = (set(bundle_paths(root)) | {p.parent for p in root.glob("*/task.toml")}
                      | {peer for peer in retained if peer.parent == root})
        for peer in sorted(candidates):
            if peer.resolve() == bundle.resolve() or not (peer / "authoring/spec.json").is_file():
                continue
            if peer.resolve() in seen:
                continue
            seen.add(peer.resolve())
            other = strict_json((peer / "authoring/spec.json").read_text())
            peer_signature = signature(peer)
            peer_sha = peer_signature['artifact_sha256']
            # A transferred or staged copy is still this candidate, not a
            # competing task. Deduplicate peers by frozen bytes as well.
            if peer_sha == candidate['artifact_sha256'] or peer_sha in seen_artifacts:
                continue
            if delivered_copy_of(peer, candidate['artifact_sha256']):
                continue
            seen_artifacts.add(peer_sha)
            relation = related(candidate, peer_signature)
            is_predecessor = peer_sha in predecessors
            if is_predecessor:
                if not relation:
                    raise ValueError('declared predecessor belongs to an unrelated source family')
                found_predecessors.add(peer_sha)
            tokens = words(other.get("novelty", "") + " " + other.get("instruction", ""))
            similarity = len(tokens & vocabulary) / max(1, len(tokens | vocabulary))
            peers.append({"artifact_sha256": peer_sha, "name": peer.name,
                          "source_related": relation, "similarity": round(similarity, 4),
                          "relationship": "predecessor" if is_predecessor else "peer",
                          "novelty": other.get("novelty"),
                          "instructions": [p.read_text() for p in sorted((peer / "steps").glob("*/instruction.md"))],
                          "checks": other.get("checks", [])})
    if found_predecessors != predecessors:
        raise ValueError('declared predecessor is missing or changed; retain the exact baseline for review')
    peers.sort(key=lambda p: (-int(p['relationship'] == 'predecessor'),
                             -int(p["source_related"]), -p["similarity"],
                             p["artifact_sha256"], p["name"]))
    relevant = [p for p in peers if p["source_related"] or p["similarity"] >= .2]
    return {"method": "session/source overlap or lexical Jaccard >=0.2; critic must assess semantic novelty",
            "design_mode": "replacement" if predecessors else "new_task",
            "replacement_reason": lineage['reason'] if predecessors else None,
            "peers_considered": len(peers), "peers": relevant[:8]}


def register(bundle: Path, release: dict, registry: Path | None = None) -> list[str]:
    """Serialize duplicate detection and registration across worker processes."""
    if release.get("release_ready") is not True or release.get("artifact_sha256") != identity(bundle):
        raise ValueError("only verified exact artifacts may enter the release catalog")
    root = registry or registry_root()
    candidate = signature(bundle)
    with bundle_lock(root):
        errors = problems(candidate, root)
        if not errors:
            atomic_json(root / (candidate["artifact_sha256"] + ".json"), {
                **candidate, "policy_sha256": release["policy_sha256"],
                "release_receipt": str(bundle / "verification/release.json")})
        return errors
