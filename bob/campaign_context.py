from __future__ import annotations

import json
from typing import Iterable

MAX_CONTINUATION_CONTEXT_CHARS = 40_000
RECENT_FULL_BUDGET_CHARS = 28_000
MAX_HISTORY_SUMMARY_CHARS = 280


def _json_payload(result: str) -> dict:
    text = str(result)
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        return {}
    try:
        payload = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _history_summary(result: str) -> str:
    payload = _json_payload(result)
    request_id = str(payload.get("request_id") or "?")
    tool = str(payload.get("tool") or "?")
    status = str(payload.get("status") or "?")
    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    details = []
    if tool == "repo.read_file":
        if data.get("path"):
            details.append(f"path={data['path']}")
        if data.get("start_line") is not None:
            details.append(
                f"lines={data.get('start_line')}-{data.get('end_line')}"
            )
        if data.get("content_sha256"):
            details.append(f"sha256={data['content_sha256']}")
    elif tool == "repo.search":
        if data.get("query"):
            details.append(f"query={data['query']!r}")
        if data.get("prefix"):
            details.append(f"prefix={data['prefix']}")
        if isinstance(data.get("results"), list):
            details.append(f"matches={len(data['results'])}")
    elif tool == "repo.list_files":
        if data.get("prefix"):
            details.append(f"prefix={data['prefix']}")
        if isinstance(data.get("files"), list):
            details.append(f"files={len(data['files'])}")

    verified = data.get("verified_effect")
    if isinstance(verified, dict):
        details.append(f"effect={verified.get('tool')}")
        details.append(f"path={verified.get('path')}")
        details.append(f"head={verified.get('head_sha')}")
    for key in ("head_sha", "base_sha", "branch", "clean", "truncated"):
        value = data.get(key)
        if value not in (None, "", [], {}):
            details.append(f"{key}={value}")

    summary = (
        f"[history] request_id={request_id} tool={tool} status={status}"
        + ((" " + " ".join(details)) if details else "")
    )
    if len(summary) > MAX_HISTORY_SUMMARY_CHARS:
        summary = summary[: MAX_HISTORY_SUMMARY_CHARS - 1] + "…"
    return summary


def bounded_continuation_results(
    results: Iterable[str],
) -> list[str]:
    raw = [str(result) for result in results]
    if sum(len(result) for result in raw) <= MAX_CONTINUATION_CONTEXT_CHARS:
        return raw

    recent: list[str] = []
    recent_chars = 0
    split_at = len(raw)
    for index in range(len(raw) - 1, -1, -1):
        candidate = raw[index]
        if recent and recent_chars + len(candidate) > RECENT_FULL_BUDGET_CHARS:
            break
        if len(candidate) > RECENT_FULL_BUDGET_CHARS:
            candidate = candidate[-RECENT_FULL_BUDGET_CHARS:]
        recent.insert(0, candidate)
        recent_chars += len(candidate)
        split_at = index

    older = [_history_summary(result) for result in raw[:split_at]]
    marker = (
        "[continuation compacted: full durable history remains in Bob state; "
        f"durable_results={len(raw)} older_summarized={len(older)}]"
    )
    compacted = [marker, *older, *recent]

    while (
        sum(len(result) for result in compacted)
        > MAX_CONTINUATION_CONTEXT_CHARS
        and older
    ):
        older.pop(0)
        compacted = [marker, *older, *recent]

    if sum(len(result) for result in compacted) > MAX_CONTINUATION_CONTEXT_CHARS:
        available = max(
            0,
            MAX_CONTINUATION_CONTEXT_CHARS
            - len(marker)
            - sum(len(result) for result in older),
        )
        recent_text = "\n".join(recent)
        recent = [recent_text[-available:]] if available else []
        compacted = [marker, *older, *recent]
    return compacted


def compile_campaign_prompt(envelope: dict) -> str:
    return (
        "Continue this Bob campaign work item from the supplied durable "
        "state; do not restart it.\n\n"
        "EXECUTION ENVELOPE\n"
        + json.dumps(envelope, indent=2, sort_keys=True)
        + "\n\nHARD RULES\n"
        "- Work only on this exact repository/run/branch/worktree.\n"
        "- Never request merge, push, promotion, production mutation, spend, "
        "secrets, or authority expansion.\n"
        "- Emit exactly one BOB protocol message per response.\n"
        "- READ tools: repo.read_file, repo.list_files, repo.search, "
        "repo.status, repo.verify.\n"
        "- EFFECT tools: repo.create_file, repo.replace_file, "
        "repo.delete_file. Effects are isolated branch writes only.\n"
        "- Before replace/delete, read the file and use content_sha256 as "
        "expected_sha256.\n"
        "- BOB.DONE is advisory; Bob performs deterministic verification "
        "before successful completion.\n"
        "- continuation_results already happened; do not treat them as requested work.\n"
        "- Use BOB.ASK only for a genuine operator decision.\n\n"
        "Return one raw JSON BOB object or one fenced BOB object. Examples:\n"
        '{"type":"BOB.READ","id":"r1","tool":"repo.read_file",'
        '"args":{"path":"CURRENT_WORK.md"}}\n'
        '{"type":"BOB.EFFECT","id":"e1","tool":"repo.replace_file",'
        '"args":{"path":"x.py","content":"...","expected_sha256":"..."}}\n'
        '{"type":"BOB.DONE","id":"d1","args":{"summary":"candidate ready"}}'
        "\n\nNEXT ACTION: Continue from continuation_results above. "
        "Use a new id, never repeat a PASS READ, and advance toward the goal."
    )
