from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from .errors import ProtocolError

BLOCK_RE = re.compile(r"```bob\s*(\{.*?\})\s*```", re.DOTALL)
ALLOWED_TYPES = {"BOB.READ", "BOB.EFFECT", "BOB.ASK", "BOB.DONE"}


@dataclass(frozen=True)
class BobMessage:
    type: str
    id: str
    tool: str | None
    args: dict[str, Any]
    raw: dict[str, Any]


@dataclass(frozen=True)
class ParsedResponse:
    visible_text: str
    messages: tuple[BobMessage, ...]


def parse_model_response(text: str) -> ParsedResponse:
    messages: list[BobMessage] = []

    def replace(match: re.Match[str]) -> str:
        payload_text = match.group(1)
        try:
            payload = json.loads(payload_text)
        except json.JSONDecodeError as exc:
            raise ProtocolError(f"invalid BOB JSON: {exc}") from exc
        if not isinstance(payload, dict):
            raise ProtocolError("BOB block must contain a JSON object")
        msg_type = payload.get("type")
        if msg_type not in ALLOWED_TYPES:
            raise ProtocolError(f"unsupported BOB message type: {msg_type}")
        msg_id = payload.get("id")
        if not isinstance(msg_id, str) or not msg_id.strip():
            raise ProtocolError("BOB message requires non-empty string id")
        tool = payload.get("tool")
        if msg_type in {"BOB.READ", "BOB.EFFECT"} and (not isinstance(tool, str) or not tool):
            raise ProtocolError(f"{msg_type} requires tool")
        args = payload.get("args") or {}
        if not isinstance(args, dict):
            raise ProtocolError("BOB args must be an object")
        messages.append(BobMessage(msg_type, msg_id, tool, args, payload))
        return ""

    visible = BLOCK_RE.sub(replace, text).strip()
    return ParsedResponse(visible_text=visible, messages=tuple(messages))


def make_result(request_id: str, tool: str, status: str, data: Any = None, error: str | None = None) -> str:
    payload = {
        "type": "BOB.RESULT",
        "request_id": request_id,
        "tool": tool,
        "status": status,
    }
    if data is not None:
        payload["data"] = data
    if error is not None:
        payload["error"] = error
    return "```bob-result\n" + json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n```"


def make_workspace_packet(workspace: dict[str, Any], capabilities: dict[str, list[str]]) -> str:
    payload = {
        "type": "BOB.WORKSPACE",
        "workspace": workspace,
        "capabilities": capabilities,
        "rule": "External effects are not true until a BOB.RESULT reports verified state.",
    }
    return "```bob-context\n" + json.dumps(payload, ensure_ascii=False, indent=2) + "\n```"
