"""Inventory what the fixtures of every calibrated package actually contain.

Answers: which file formats exist, and which 'hidden-semantics' constructs (struck text,
hidden HTML, comments, quoted email text, ambiguous dates, leading zeros) agents could
have met at all. Output: out/fixture_scan.json
"""
from __future__ import annotations

import json
import os
import re
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(__file__))
from r3_common import ART, OUT, package_dir, task_name, fixture_files, read_fixture

PAT = {
    "html_del_s_strike": r"<(del|s|strike)\b",
    "css_line_through": r"line-through",
    "html_hidden": r"display\s*:\s*none|visibility\s*:\s*hidden|\shidden[\s>=]|aria-hidden",
    "html_comment": r"<!--",
    "html_ins": r"<ins\b",
    "md_strike": r"~~[^~\n]+~~",
    "email_headers": r"^(From|De|Von|От|Subject|Asunto|Objet|Betreff|Тема|Date|Fecha):\s",
    "email_quoted_gt": r"^\s*>\s*\S",
    "email_original_msg": r"Original Message|Mensaje original|Message d'origine|Ursprüngliche Nachricht|Forwarded message|wrote:|escribió:|a écrit :|schrieb:",
    "date_slash_ambig": r"\b(0?[1-9]|1[0-2])/(0?[1-9]|1[0-2])/(19|20)?\d\d\b",
    "date_dotted": r"\b\d{1,2}\.\d{1,2}\.(19|20)\d\d\b",
    "iso_date": r"\b(19|20)\d\d-\d\d-\d\d\b",
    "time_with_tz": r"\b\d{1,2}:\d\d\s?(UTC|GMT|CET|CEST|EST|EDT|PST|PDT|BST|IST|JST|[+-]\d\d:?\d\d)\b",
    "money_comma_decimal": r"\b\d{1,3}(\.\d{3})+,\d{2}\b",
    "half_cent": r"\b\d+\.\d{2}5\b",
    "leading_zero_id": r"(^|,)0\d{3,}(,|$)",
    "supersede_words": r"supersed|replaces|obsolete|withdrawn|retired|void|cancel|revoked|substitu|remplac|ersetzt|anulad|annul|отмен",
    "todo_draft_words": r"\bDRAFT\b|\bBORRADOR\b|\bBROUILLON\b|\bENTWURF\b|ЧЕРНОВИК",
}
PAT = {k: re.compile(v, re.I | re.M) for k, v in PAT.items()}


def main():
    camps = [l.strip() for l in open(os.path.join(OUT, "campaigns.txt")) if l.strip()]
    seen = {}
    for c in camps:
        cdir = os.path.join(ART, c)
        pkg = package_dir(cdir)
        files = fixture_files(pkg)
        sig = (task_name(pkg), len(files), sum(os.path.getsize(os.path.join(pkg, "environment", "files", f)) for f in files))
        if sig in seen:
            continue
        seen[sig] = pkg
    ext_files = Counter()
    ext_pkgs = Counter()
    pat_pkgs = defaultdict(set)
    pat_files = Counter()
    examples = defaultdict(list)
    sizes = []
    nfiles = []
    for sig, pkg in seen.items():
        files = fixture_files(pkg)
        nfiles.append(len(files))
        tot = 0
        es = set()
        for rel in files:
            e = os.path.splitext(rel)[1].lower() or "(none)"
            ext_files[e] += 1
            es.add(e)
            txt = read_fixture(pkg, rel)
            tot += len(txt.encode())
            for k, rx in PAT.items():
                if rx.search(txt):
                    pat_files[k] += 1
                    pat_pkgs[k].add(sig[0])
                    if len(examples[k]) < 4:
                        m = rx.search(txt)
                        examples[k].append(f"{os.path.relpath(pkg, ART)}/environment/files/{rel}: {txt[max(0, m.start()-40):m.end()+40]!r}")
        sizes.append(tot)
        for e in es:
            ext_pkgs[e] += 1
    sizes.sort()
    nfiles.sort()
    out = {
        "n_packages": len(seen),
        "n_task_names": len({s[0] for s in seen}),
        "files_by_ext": ext_files.most_common(),
        "packages_by_ext": ext_pkgs.most_common(),
        "median_fixture_bytes": sizes[len(sizes) // 2],
        "median_files": nfiles[len(nfiles) // 2],
        "max_files": nfiles[-1],
        "pattern_packages": {k: len(v) for k, v in pat_pkgs.items()},
        "pattern_files": dict(pat_files),
        "examples": examples,
    }
    json.dump(out, open(os.path.join(OUT, "fixture_scan.json"), "w"), indent=1, ensure_ascii=False)
    print(json.dumps({k: v for k, v in out.items() if k != "examples"}, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
