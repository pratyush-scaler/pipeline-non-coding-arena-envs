"""Bounded, explicitly authored scenario data; recovered documents stay immutable."""
from __future__ import annotations

import hashlib
from pathlib import Path
import re
import tempfile

from .contracts import contained, strict_json

MANIFEST = 'provenance/scenario.json'
#: The disclosure of authored supplements, for Arena's reviewers. v2 (2026-10-02):
#: it lives with the provenance, OUTSIDE the agent's fixture. In v1 it was
#: `scenario/README.md` inside the fixture, listing exactly which files carried
#: the authored case facts; trajectory mining found Fable opened it in 97% of
#: steps and Astra in 88%, so every authored trap file was flagged to the
#: solver (research/R3). The ledger still marks each authored file per byte.
NOTICE = 'provenance/scenario-notice.md'
from ..policy import SCENARIO_MAX_FILE_BYTES as MAX_FILE_BYTES
from ..policy import SCENARIO_MAX_TOTAL_BYTES as MAX_TOTAL_BYTES
from ..policy import SCENARIO_EXTENSIONS
BOOTSTRAP = 'provenance/scenario-bootstrap.json'
CONTEXT = 'synthetic-context.md'


def _trace_context_problems(receipt: dict, trace: dict, session_id: str) -> list[str]:
    from ..ledger.grounding import alignment_problems
    witness = {"citation": receipt.get("citation"), "quote": receipt.get("quote"),
               "preserved": receipt.get("reason"), "checks": ["source_goal"]}
    spec = {"checks": [{"id": "source_goal", "kind": "objective"}],
            "quality": {"trace_alignment": {"goal": witness, "capability": witness}}}
    return alignment_problems(spec, trace, session_id, required=True)


def verify_bootstrap(bundle: Path, trace: dict | None = None,
                     session_id: str | None = None) -> dict:
    """Synthetic context never receives recovered-source credit."""
    path = contained(bundle, BOOTSTRAP)
    if not path.is_file():
        return {}
    receipt = strict_json(path.read_text())
    if receipt.get('schema') != 'arena-pipeline/scenario-bootstrap/1':
        raise ValueError('invalid synthetic context receipt')
    content = contained(bundle / 'environment/files', CONTEXT).read_bytes()
    if (receipt.get('sha256') != _hash(content) or receipt.get('bytes') != len(content)
            or len(content) > MAX_FILE_BYTES or not content.startswith(b'# Synthetic scenario context\n')):
        raise ValueError('synthetic context differs from its disclosed receipt')
    if trace is not None:
        if receipt.get('session_id') != session_id:
            raise ValueError('synthetic context belongs to another source session')
        if problems := _trace_context_problems(receipt, trace, session_id):
            raise ValueError('; '.join(problems))
    return {CONTEXT: {'note': 'Disclosed synthetic context grounded in a verified source request; zero recovered-source credit.'}}


def initialize(bundle: Path, *, context: str, reason: str, citation: str,
               quote: str, trace: dict, session_id: str, category: str) -> dict:
    """Bootstrap a source-grounded synthetic world when no artifact survives."""
    from ..artifacts import atomic_json
    from ..privacy import scan

    if category not in {'F0', 'F1', 'F2'}:
        raise ValueError('synthetic initialization is only for Inspired, Pattern or Scenario targets')
    fixture = bundle / 'environment/files'
    if _inventory(fixture) or (bundle / BOOTSTRAP).exists():
        raise ValueError('initialize only an empty fixture; recovered files are immutable')
    if not isinstance(context, str) or not context.strip() or not isinstance(reason, str) or len(reason.strip()) < 30:
        raise ValueError('provide a substantive synthetic context and its source-grounded purpose')
    raw = ('# Synthetic scenario context\n\nThis starting context is invented, not a recovered artifact.\n\n'
           + context).encode()
    if len(raw) > MAX_FILE_BYTES:
        raise ValueError('synthetic context exceeds the 32 KiB limit')
    receipt = {'schema': 'arena-pipeline/scenario-bootstrap/1', 'session_id': session_id,
               'citation': citation, 'quote': quote, 'reason': reason,
               'sha256': _hash(raw), 'bytes': len(raw)}
    if problems := _trace_context_problems(receipt, trace, session_id):
        raise ValueError('; '.join(problems))
    with tempfile.TemporaryDirectory(prefix='arena-context-check-') as temporary:
        (Path(temporary) / 'context.md').write_bytes(raw)
        if findings := scan(Path(temporary)):
            raise ValueError('synthetic context contains unsupported private data: '
                             + ', '.join(sorted({finding['kind'] for finding in findings})))
    fixture.mkdir(parents=True, exist_ok=True)
    target = contained(fixture, CONTEXT)
    target.write_bytes(raw)
    try:
        atomic_json(contained(bundle, BOOTSTRAP), receipt)
    except Exception:
        target.unlink(missing_ok=True)
        raise
    return {'path': CONTEXT, 'bytes': len(raw), 'recovered_source_credit': 0,
            'note': 'Add coherent disclosed scenario data grounded in this context; source alignment still requires review.'}


def _hash(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _inventory(fixture: Path) -> dict:
    result = {}
    for path in sorted(fixture.rglob('*')):
        if path.is_symlink():
            raise ValueError('scenario source inventory cannot contain symlinks')
        if path.is_dir():
            continue
        if not path.is_file():
            raise ValueError('scenario source inventory requires regular files')
        raw = path.read_bytes()
        result[path.relative_to(fixture).as_posix()] = {'sha256': _hash(raw), 'bytes': len(raw)}
    return result


def _notice(entries: dict) -> str:
    return ('# Authored scenario supplement\n\n'
            'The files listed below contain hypothetical case facts authored for this task. '
            'They are not recovered trace documents or evidence that real events occurred. '
            'Apply the assignment\'s scope and authority rules; the recovered documents remain unchanged.\n\n'
            + ''.join(f'- `{name}`\n' for name in sorted(entries)))


def verify(bundle: Path) -> dict:
    """Return declared authored files only after checking the complete receipt."""
    path = contained(bundle, MANIFEST)
    bootstrap = verify_bootstrap(bundle)
    if not path.exists():
        return bootstrap
    doc = strict_json(path.read_text())
    if (doc.get('schema') != 'arena-pipeline/scenario/1'
            or not isinstance(doc.get('base'), dict) or not doc['base']
            or not isinstance(doc.get('files'), dict) or not doc['files']):
        raise ValueError('invalid authored scenario receipt')
    fixture = bundle / 'environment/files'
    actual = _inventory(fixture)
    files, base = doc['files'], doc['base']
    if set(files) & set(base) or NOTICE in base or NOTICE in files:
        raise ValueError('scenario receipt overlaps recovered sources or its notice')
    expected = {**base, **{name: {'sha256': row['sha256'], 'bytes': row['bytes']}
                          for name, row in files.items()}}
    if actual != expected:
        raise ValueError('scenario or recovered source bytes differ from the authoring receipt')
    notice_path = contained(bundle, NOTICE)
    if not notice_path.is_file() or notice_path.read_text() != _notice(files):
        raise ValueError('authored scenario is missing its provenance disclosure')
    for name, row in files.items():
        _valid_name(name)
        _evidence(fixture, base, row.get('source_evidence'))
        if not isinstance(row.get('reason'), str) or not row['reason'].strip():
            raise ValueError('scenario addition has no grounded purpose')
    return {**bootstrap, **{name: {'note': 'Explicitly authored scenario supplement; no recovered-source credit.'}
                           for name in files}}


def _valid_name(name: str) -> None:
    # v2: authored documents sit where a real matter file would keep them
    # (correspondence/, policies/, exports/ ...), not in a folder whose name
    # tells the solver which files were written to carry the case facts.
    extensions = '|'.join(e.lstrip('.') for e in SCENARIO_EXTENSIONS)
    if (not isinstance(name, str) or name == NOTICE or name.startswith('provenance/')
            or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_. ()/-]*\.(?:' + extensions + ')', name)
            or any(not p or p.startswith('.') or p != p.strip() for p in name.split('/'))):
        raise ValueError('use a new text/data file at a natural relative path with one of '
                         f'{", ".join(SCENARIO_EXTENSIONS)}; provenance/ is reserved')


def reconcile_owned_revision(source: Path, bundle: Path, *, reason: str,
                             category: str | None = None) -> dict:
    """Record operator edits to existing owned supplements through the writer."""
    from ..artifacts import atomic_json

    source, bundle = Path(source).resolve(), Path(bundle).resolve()
    if source.is_relative_to(bundle) or bundle.is_relative_to(source):
        raise ValueError('scenario revision needs disjoint source and working copies')
    if not isinstance(reason, str) or len(reason.strip()) < 30:
        raise ValueError('scenario revision needs a substantive repair reason')
    verify(source)
    original = _inventory(source / 'environment/files')
    current = _inventory(bundle / 'environment/files')
    manifest = contained(source, MANIFEST)
    if not manifest.exists():
        if original != current:
            raise ValueError('operator revision cannot change unowned recovered evidence')
        return {'owned_changes': [], 'source_unchanged': True}
    document = strict_json(manifest.read_text())
    owned = set(document['files'])
    if any(current.get(name) != original[name] for name in set(original) - owned):
        raise ValueError('operator revision cannot change recovered evidence or synthetic context')
    working_manifest = contained(bundle, MANIFEST)
    working = strict_json(working_manifest.read_text())
    if working.get('base') != document['base']:
        raise ValueError('operator revision cannot reclassify recovered evidence')
    changed = sorted(name for name in owned if current.get(name) != original[name])
    if working != document:
        verify(bundle)
        return {'owned_changes': changed, 'source_unchanged': True,
                'receipt_already_verified': True}
    if set(current) != set(original):
        raise ValueError('operator revision cannot add undisclosed files')
    if not changed:
        verify(bundle)
        return {'owned_changes': [], 'source_unchanged': True}
    fixture = bundle / 'environment/files'
    targets = [contained(fixture, name) for name in changed] + [contained(bundle, NOTICE), working_manifest]
    previous = {path: path.read_bytes() for path in targets}
    contents = {name: contained(fixture, name).read_text() for name in changed}
    try:
        for name in changed:
            contained(fixture, name).write_bytes(contained(source / 'environment/files', name).read_bytes())
        verify(bundle)
        for name in changed:
            entry = document['files'][name]
            write(bundle, path=name, content=contents[name],
                  reason=entry['reason'] + ' Operator validity repair: ' + reason,
                  source_evidence=entry['source_evidence'], category=category)
        verify(bundle)
        if _inventory(source / 'environment/files') != original:
            raise ValueError('retained source changed during scenario revision')
        receipt = {'schema': 'arena-pipeline/owned-scenario-revision/1', 'source': str(source),
                   'reason': reason, 'source_unchanged': True, 'recovered_source_credit': 0,
                   'owned_changes': [{'file': name, 'before': original[name],
                                      'after': _inventory(fixture)[name]} for name in changed]}
        atomic_json(bundle / 'provenance/owned-scenario-revision.json', receipt)
        return receipt
    except Exception:
        for path, content in previous.items():
            path.write_bytes(content)
        raise


def _evidence(fixture: Path, base: dict, evidence) -> None:
    if not isinstance(evidence, list) or not evidence:
        raise ValueError('scenario additions need exact grounding in recovered public documents')
    for row in evidence:
        if (not isinstance(row, dict) or row.get('file') not in base
                or not isinstance(row.get('quote'), str) or len(row['quote'].strip()) < 15):
            raise ValueError('scenario evidence must name a recovered file and a substantive exact quote')
        if row['quote'] not in contained(fixture, row['file']).read_text():
            raise ValueError('scenario grounding quote is absent from the recovered public source')


def write(bundle: Path, *, path: str, content: str, reason: str,
          source_evidence: list, category: str | None = None) -> dict:
    """Create/revise owned supplements; never overwrite an undeclared file."""
    from ..artifacts import atomic_json
    from ..privacy import scan
    from ..select.priority import CATEGORY_FIXTURE_FLOOR
    _valid_name(path)
    fixture = bundle / 'environment/files'
    target = contained(fixture, path)
    manifest = contained(bundle, MANIFEST)
    if not isinstance(content, str) or not content.strip() or '\x00' in content:
        raise ValueError('scenario content must be nonempty UTF-8 text')
    raw = content.encode()
    if len(raw) > MAX_FILE_BYTES:
        raise ValueError(f'scenario file exceeds the {MAX_FILE_BYTES // 1024} KiB limit')
    if not isinstance(reason, str) or len(reason.strip()) < 30:
        raise ValueError('explain the source-grounded purpose of this addition')
    if target.suffix.lower() == '.json':
        strict_json(content)
    if manifest.exists():
        verify(bundle)
        doc = strict_json(manifest.read_text())
    else:
        base = _inventory(fixture)
        if not base:
            raise ValueError('need recovered sources (or an initialized synthetic context) first')
        doc = {'schema': 'arena-pipeline/scenario/1', 'base': base, 'files': {}}
    if target.exists() and path not in doc['files']:
        raise ValueError('cannot overwrite a recovered or unowned fixture')
    _evidence(fixture, doc['base'], source_evidence)
    doc['files'][path] = {'sha256': _hash(raw), 'bytes': len(raw),
                          'reason': reason, 'source_evidence': source_evidence}
    notice = _notice(doc['files']).encode()
    authored_bytes = sum(row['bytes'] for row in doc['files'].values()) + len(notice)
    source_bytes = sum(row['bytes'] for row in doc['base'].values())
    if authored_bytes > MAX_TOTAL_BYTES:
        raise ValueError(f'authored scenario exceeds the {MAX_TOTAL_BYTES // 1024} KiB total limit')
    upper_bound = source_bytes / (source_bytes + authored_bytes)
    if category in CATEGORY_FIXTURE_FLOOR and upper_bound < CATEGORY_FIXTURE_FLOOR[category]:
        raise ValueError('addition would exceed the category fidelity allowance even if every source byte earns full credit')
    # Check before writing. Return only finding kinds, never private values.
    with tempfile.TemporaryDirectory(prefix='arena-scenario-check-') as tmp:
        (Path(tmp) / 'content.txt').write_bytes(raw)
        (Path(tmp) / 'notice.txt').write_bytes(notice)
        if findings := scan(Path(tmp)):
            raise ValueError('scenario addition contains unsupported private data: '
                             + ', '.join(sorted({r['kind'] for r in findings})))
    doc['notice'] = {'sha256': _hash(notice), 'bytes': len(notice)}
    old_target = target.read_bytes() if target.exists() else None
    notice_path = contained(bundle, NOTICE)
    old_notice = notice_path.read_bytes() if notice_path.exists() else None
    old_manifest = manifest.read_bytes() if manifest.exists() else None
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        notice_path.parent.mkdir(parents=True, exist_ok=True)
        notice_path.write_bytes(notice)
        atomic_json(manifest, doc)
        verify(bundle)
    except Exception:
        for file, prior in ((target, old_target), (notice_path, old_notice), (manifest, old_manifest)):
            if prior is None:
                file.unlink(missing_ok=True)
            else:
                file.write_bytes(prior)
        raise
    return {'written': path, 'origin': 'authored', 'source_credit': 0,
            'authored_bytes': authored_bytes, 'source_bytes': source_bytes,
            'fidelity_upper_bound': round(upper_bound, 3),
            'note': 'Actual fidelity is independently recomputed by the ledger. Review and calibration remain required.'}


def remove(bundle: Path, *, path: str, reason: str) -> dict:
    """Remove an owned supplement and its disclosure, preserving recovered files."""
    from ..artifacts import atomic_json
    _valid_name(path)
    if not isinstance(reason, str) or len(reason.strip()) < 30:
        raise ValueError('explain why this authored supplement should be removed')
    manifest = contained(bundle, MANIFEST)
    if not manifest.is_file():
        raise ValueError('no owned scenario supplement to remove')
    verify(bundle)
    doc = strict_json(manifest.read_text())
    if path not in doc['files']:
        raise ValueError('cannot remove a recovered or unowned fixture')
    fixture = bundle / 'environment/files'
    target, notice_path = contained(fixture, path), contained(bundle, NOTICE)
    originals = {p: p.read_bytes() for p in (target, notice_path, manifest)}
    del doc['files'][path]
    try:
        target.unlink()
        if doc['files']:
            notice = _notice(doc['files']).encode()
            doc['notice'] = {'sha256': _hash(notice), 'bytes': len(notice)}
            notice_path.write_bytes(notice)
            atomic_json(manifest, doc)
            verify(bundle)
        else:
            notice_path.unlink()
            manifest.unlink()
            if _inventory(fixture) != doc['base']:
                raise ValueError('removing the final supplement changed recovered sources')
    except Exception:
        for file, prior in originals.items():
            file.write_bytes(prior)
        raise
    return {'removed': path, 'reason': reason,
            'remaining_supplements': sorted(doc['files']),
            'note': 'Update draft references and rebuild the ledger, grader and verification evidence before review.'}
