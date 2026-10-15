"""R3 agent-habit research: discovery and trajectory normalisation.

Read-only over arena-envs-tasks-large-dump/pipeline-artifacts. Writes only under
arena-envs-non-coding-v2/research/scripts/out/.
"""
from __future__ import annotations

import ast
import html
import json
import os
import re
import tomllib
from functools import lru_cache

ART = "/Users/pratyushmohanty/Downloads/arena-envs-tasks-large-dump/pipeline-artifacts"
OUT = "/Users/pratyushmohanty/Downloads/arena-envs-non-coding-v2/research/scripts/out"
MODEL_SHORT = {"anthropic/claude-fable-5-1": "fable", "openai/gpt-6-astra": "astra"}
FIX_ROOT = "/app/environment/files/"


def load_json(p, default=None):
    try:
        with open(p) as f:
            return json.load(f)
    except Exception:
        return default


@lru_cache(maxsize=None)
def campaign_report(cdir: str) -> dict:
    return load_json(os.path.join(cdir, "report.json"), {}) or {}


def package_dir(cdir: str) -> str:
    p = os.path.join(cdir, "package")
    if os.path.isdir(p):
        return p
    return os.path.join(os.path.dirname(cdir), "source")


@lru_cache(maxsize=None)
def task_name(pkg: str) -> str:
    p = os.path.join(pkg, "task.toml")
    try:
        with open(p, "rb") as f:
            t = tomllib.load(f)
        n = t.get("task", {}).get("name", "")
        st = (t.get("metadata", {}) or {}).get("source_trace") or ""
        return (n.split("/", 1)[-1] or "?") + ("" if not re.match(r"^v\d+$", n.split("/", 1)[-1]) else "@" + st[:8])
    except Exception:
        return "?"


@lru_cache(maxsize=None)
def fixture_files(pkg: str) -> tuple:
    root = os.path.join(pkg, "environment", "files")
    out = []
    for dp, dn, fn in os.walk(root):
        for f in fn:
            full = os.path.join(dp, f)
            out.append(os.path.relpath(full, root))
    return tuple(sorted(out))


def read_fixture(pkg: str, rel: str) -> str:
    try:
        with open(os.path.join(pkg, "environment", "files", rel), encoding="utf-8", errors="replace") as f:
            return f.read()
    except Exception:
        return ""


@lru_cache(maxsize=None)
def instruction(pkg: str, step: str) -> str:
    p = os.path.join(pkg, "steps", step, "instruction.md")
    try:
        return open(p, encoding="utf-8").read()
    except Exception:
        return ""


@lru_cache(maxsize=None)
def checks(pkg: str) -> dict:
    c = load_json(os.path.join(pkg, "tests", "checks.json"), {}) or {}
    cl = c["checks"] if isinstance(c, dict) and "checks" in c else (c if isinstance(c, list) else [])
    return {x["id"]: x for x in cl if isinstance(x, dict) and "id" in x}


@lru_cache(maxsize=None)
def projections(pkg: str) -> dict:
    p = load_json(os.path.join(pkg, "tests", "projections.json"), {}) or {}
    out = {}
    for x in p.get("projections", []) if isinstance(p, dict) else []:
        if isinstance(x, dict) and x.get("as"):
            src = x.get("file") or x.get("files") or x.get("glob")
            out[x["as"]] = {"src": src, "parser": x.get("parser"), "op": x.get("op")}
    return out


def target_sources(pkg: str, check: dict) -> set:
    """Fixture files a check's target expression reads (through projections)."""
    proj = projections(pkg)
    files = set()

    def walk(o):
        if isinstance(o, dict):
            if "file" in o and isinstance(o["file"], str) and o.get("op") != "field":
                files.add(o["file"])
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    walk(check.get("target"))
    srcs = set()
    for f in files:
        p = proj.get(f)
        if p:
            s = p["src"]
            if isinstance(s, list):
                srcs.update(s)
            elif s:
                srcs.add(s)
        else:
            srcs.add(f)
    return srcs


# ---------------------------------------------------------------- trajectories

_CMD_RE = re.compile(r'cmd\s*:\s*("(?:[^"\\]|\\.)*")', re.S)
_CMD_TPL_RE = re.compile(r'cmd\s*:\s*`((?:[^`\\]|\\.)*)`', re.S)
_PATCH_RE = re.compile(r'apply_patch\(\s*("(?:[^"\\]|\\.)*")', re.S)
_PATCH_TPL_RE = re.compile(r'apply_patch\(\s*`((?:[^`\\]|\\.)*)`', re.S)
_MAXTOK_RE = re.compile(r'max_output_tokens"?\s*:\s*(\d+)')


def _js_str(lit: str) -> str:
    try:
        return json.loads(lit)
    except Exception:
        return lit[1:-1]


def split_codex_input(inp: str):
    parts = []
    for m in _CMD_RE.finditer(inp):
        parts.append(("cmd", _js_str(m.group(1))))
    for m in _CMD_TPL_RE.finditer(inp):
        parts.append(("cmd", m.group(1).replace("\\`", "`")))
    for m in _PATCH_RE.finditer(inp):
        parts.append(("patch", _js_str(m.group(1))))
    for m in _PATCH_TPL_RE.finditer(inp):
        parts.append(("patch", m.group(1)))
    if not parts:
        parts.append(("js", inp))
    return parts


def _jl(s):
    if isinstance(s, str):
        try:
            return json.loads(s)
        except Exception:
            return s
    return s


def decode_codex_obs(c: str) -> tuple[str, bool]:
    """Return (decoded text, truncated?) for a Codex exec observation."""
    trunc = "tokens truncated" in c or "Warning: truncated output" in c
    texts = []
    try:
        items = ast.literal_eval(c)
        if isinstance(items, list):
            for it in items:
                if isinstance(it, dict) and "text" in it:
                    texts.append(str(it["text"]))
        else:
            texts.append(c)
    except Exception:
        texts.append(c)
    out = []
    for t in texts:
        # inner payloads are JSON lines with an "output" field; decode where possible
        done = False
        for line in t.split("\n"):
            s = line.strip()
            if s.startswith("{") and '"output"' in s:
                try:
                    o = json.loads(s)
                    v = o.get("value", o) if isinstance(o, dict) else o
                    if isinstance(v, dict) and "output" in v:
                        out.append(str(v["output"]))
                        done = True
                        continue
                    if isinstance(o, dict) and "output" in o:
                        out.append(str(o["output"]))
                        done = True
                        continue
                except Exception:
                    pass
            out.append(line)
        if not done:
            pass
    return "\n".join(out), trunc


def events(traj: dict):
    """Flatten an ATIF trajectory: kinds user/text/call/obs. Calls carry tool + text (+path)."""
    ev = []
    agent = (traj.get("agent") or {}).get("name")
    for s in traj.get("steps", []):
        src = s.get("source")
        msg = s.get("message") or ""
        if isinstance(msg, list):
            msg = " ".join(str(x.get("text", x)) if isinstance(x, dict) else str(x) for x in msg)
        if src == "user":
            ev.append({"kind": "user", "text": msg})
            continue
        if src != "agent":
            continue
        if msg.strip():
            ev.append({"kind": "text", "text": msg})
        for tc in _jl(s.get("tool_calls")) or []:
            fn = tc.get("function_name")
            args = _jl(tc.get("arguments")) or {}
            cid = tc.get("tool_call_id")
            if fn == "exec" and isinstance(args, dict) and "input" in args:
                inp = args["input"]
                mt = [int(x) for x in _MAXTOK_RE.findall(inp)]
                for kind, txt in split_codex_input(inp):
                    ev.append({"kind": "call", "tool": kind, "text": txt, "id": cid, "maxtok": mt})
            elif fn == "Bash":
                ev.append({"kind": "call", "tool": "cmd", "text": args.get("command", ""), "id": cid})
            elif fn == "Read":
                ev.append({"kind": "call", "tool": "read", "path": args.get("file_path", ""),
                           "text": "READ " + args.get("file_path", ""), "offset": args.get("offset"),
                           "limit": args.get("limit"), "id": cid})
            elif fn in ("Grep", "Glob"):
                ev.append({"kind": "call", "tool": fn.lower(), "text": json.dumps(args, ensure_ascii=False), "id": cid})
            elif fn == "Write":
                ev.append({"kind": "call", "tool": "write", "path": args.get("file_path", ""),
                           "text": args.get("content", ""), "id": cid})
            elif fn in ("Edit", "MultiEdit"):
                edits = args.get("edits") or [{"old_string": args.get("old_string", ""), "new_string": args.get("new_string", "")}]
                for e in edits:
                    ev.append({"kind": "call", "tool": "edit", "path": args.get("file_path", ""),
                               "text": f"{e.get('old_string','')}\n=>\n{e.get('new_string','')}", "id": cid})
            else:
                ev.append({"kind": "call", "tool": str(fn), "text": json.dumps(args, ensure_ascii=False)[:4000], "id": cid})
        obs = _jl(s.get("observation")) or {}
        if isinstance(obs, dict):
            for res in obs.get("results", []) or []:
                c = res.get("content")
                if not isinstance(c, str):
                    c = json.dumps(c, ensure_ascii=False)
                trunc = False
                persisted = False
                if agent == "codex":
                    c, trunc = decode_codex_obs(c)
                else:
                    if "<persisted-output>" in c and "Output too large" in c:
                        persisted = True
                        # ATIF appends the full raw stdout after the model-visible block; the
                        # model itself saw only the 2 KB preview inside <persisted-output>.
                        end = c.find("</persisted-output>")
                        c = c[: end + len("</persisted-output>")] if end >= 0 else c.split("\n[stdout]\n", 1)[0]
                    elif "\n[stdout]\n" in c and c.split("\n[stdout]\n", 1)[0].strip():
                        # visible text precedes a duplicate raw-stdout block; keep the visible part
                        c = c.split("\n[stdout]\n", 1)[0]
                ev.append({"kind": "obs", "text": c, "id": res.get("source_call_id"),
                           "truncated": trunc, "persisted": persisted})
    return ev


# ---------------------------------------------------------------- normalisation for exposure

_TAG = re.compile(r"<[^<>]{0,400}>")
_ESC = re.compile(r"\\+[ntr]")
_UESC = re.compile(r"\\+u([0-9a-fA-F]{4})")


def norm(s: str, strip_tags: bool = False) -> str:
    s = _UESC.sub(lambda m: chr(int(m.group(1), 16)), s)
    s = _ESC.sub(" ", s)
    if strip_tags:
        s = _TAG.sub(" ", s)
        s = html.unescape(s)
    return "".join(ch for ch in s.lower() if ch.isalnum())
