"""Staged: keep the designer's request under the model's context window (a-018 HTTP 400,
2026-10-02, conversation 2.85M chars). Apply ONLY when no build runs.

Elides the bodies of OLD tool results in the request (never in the stored conversation),
oldest first, keeping every tool_use/tool_result pair and the newest messages intact.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
p = ROOT / "pipeline/author/agent_designer.py"
s = p.read_text()
helper = '''

#: v2 (2026-10-02): the request budget, in serialized characters, for the
#: designer's conversation. A dense design that read a long constitution and
#: its analyses reached 2.85M characters and the provider refused it (HTTP 400,
#: a-018). Old tool-result bodies are elided from the REQUEST only -- the stored
#: conversation keeps them, so resume and audit see everything.
REQUEST_CHAR_BUDGET = 1_800_000
ELIDED_RESULT = ("[elided from this request to fit the context window; the call and "
                 "its arguments are above -- re-read the source with read_fixture, "
                 "read_trace or read_evidence if you need it again]")
KEEP_RECENT_MESSAGES = 24


def within_context_budget(messages: list, budget: int = REQUEST_CHAR_BUDGET) -> list:
    """A copy of `messages` whose old tool results are elided until it fits."""
    import json as _json
    size = len(_json.dumps(messages, ensure_ascii=False))
    if size <= budget:
        return messages
    out = [dict(m) for m in messages]
    cutoff = max(0, len(out) - KEEP_RECENT_MESSAGES)
    for index in range(cutoff):
        if size <= int(budget * 0.75):
            break
        content = out[index].get("content")
        if out[index].get("role") != "user" or not isinstance(content, list):
            continue
        new_content = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "tool_result":
                before = len(_json.dumps(block.get("content"), ensure_ascii=False))
                if before > len(ELIDED_RESULT) + 200:
                    block = {**block, "content": ELIDED_RESULT}
                    size -= before - len(_json.dumps(ELIDED_RESULT))
            new_content.append(block)
        out[index]["content"] = new_content
    return out
'''
anchor = "\ndef with_cache_breakpoints(body: dict) -> dict:"
assert anchor in s and "within_context_budget" not in s
s = s.replace(anchor, helper + anchor, 1)
old = '"tools": tools, "messages": messages})'
assert s.count(old) == 1, s.count(old)
s = s.replace(old, '"tools": tools, "messages": within_context_budget(messages)})')
p.write_text(s)
print("applied")
