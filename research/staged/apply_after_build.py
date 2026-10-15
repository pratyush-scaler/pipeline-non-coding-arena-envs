"""Staged DSL-friction fixes (a-009 stall, 2026-10-02). Apply ONLY when no build runs.

1. Unknown-operation errors list the operations that exist (the designer probed
   with 'nonexistent_op_list_please' to discover them).
2. Projection joins accept a composite key (`on: [a, b]`), which crashed with
   TypeError: unhashable type: 'list'.
3. Exploratory evaluate() failures are normal while learning the language:
   allow 12 consecutive all-failed turns before a design is called stalled.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def edit(rel, old, new):
    p = ROOT / rel; s = p.read_text()
    assert old in s, (rel, old[:60]); p.write_text(s.replace(old, new, 1))

edit("pipeline/author/checks.py",
     '    raise CheckError(f"unknown operation {op!r}")',
     '    raise CheckError(f"unknown operation {op!r}; target operations are: "\n'
     '                     + ", ".join(sorted(TARGET_OPS | SCALAR_OPS)))')
edit("pipeline/author/checks.py",
     'SCALAR_OPS = {"only", "extract", "number", "range_bound", "parse_date", "date_add", "days_between", "compare"}',
     'SCALAR_OPS = {"only", "extract", "number", "range_bound", "parse_date", "date_add", "days_between", "compare"}\n'
     '#: Operations `evaluate` accepts besides SCALAR_OPS (named in its unknown-op error).\n'
     'TARGET_OPS = {"add", "bind_rows", "count", "derive_rows", "difference", "divide", "exists", "field",\n'
     '              "filter", "intersection", "latest", "literal", "max", "min", "multiply", "pluck",\n'
     '              "record", "round", "rows", "select", "set", "subtract", "sum", "text", "unique"}')
edit("pipeline/author/checks.py",
     '    raise CheckError(f"unsupported row operation: {op}")',
     '    raise CheckError(f"unsupported row operation: {op}; row expressions support field, literal, if, "\n'
     '                     "add/subtract/multiply/divide, round and the scalar operations "\n'
     '                     + ", ".join(sorted(SCALAR_OPS)))')
edit("pipeline/author/oracle.py",
     '''    index = {r[on]: r for r in right}
    if len(index) != len(right):
        raise ValueError(f"{name}: ambiguous join: duplicate right-hand key {on!r}")
    out = []
    for row in left:
        other = index.get(row[on], {})
        merged = {on: row[on]}''',
     '''    keys = list(on) if isinstance(on, (list, tuple)) else [on]
    def key(row):
        return tuple(row.get(k) for k in keys)
    index = {key(r): r for r in right}
    if len(index) != len(right):
        raise ValueError(f"{name}: ambiguous join: duplicate right-hand key {on!r}")
    out = []
    for row in left:
        other = index.get(key(row), {})
        merged = {k: row.get(k) for k in keys}''')
edit("pipeline/author/agent_designer.py",
     "MAX_CONSECUTIVE_TOOL_ERRORS = 6\n",
     "#: v2: exploratory evaluate() calls fail often while a designer learns the\n"
     "#: expression language; six in a row stalled a-009 after 27 turns.\n"
     "MAX_CONSECUTIVE_TOOL_ERRORS = 12\n")
print("applied")
