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


def _parse_message_payload(payload: Any) -> BobMessage:
    if not isinstance(payload, dict):
        raise ProtocolError("BOB message must contain a JSON object")
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
    return BobMessage(msg_type, msg_id, tool, args, payload)


def parse_model_response(text: str) -> ParsedResponse:
    messages: list[BobMessage] = []

    def replace(match: re.Match[str]) -> str:
        payload_text = match.group(1)
        try:
            payload = json.loads(payload_text)
        except json.JSONDecodeError as exc:
            raise ProtocolError(f"invalid BOB JSON: {exc}") from exc
        messages.append(_parse_message_payload(payload))
        return ""

    visible = BLOCK_RE.sub(replace, text).strip()

    # ChatGPT's visible Copy action can normalize a response that consists only
    # of one fenced JSON block into the raw JSON payload (without markdown
    # fences). Accept that transport representation only when the *entire*
    # copied response is one BOB protocol object.
    if not messages and visible:
        try:
            raw_payload = json.loads(visible)
        except json.JSONDecodeError:
            raw_payload = None
        if isinstance(raw_payload, dict):
            msg_type = raw_payload.get("type")
            if msg_type in ALLOWED_TYPES:
                messages.append(_parse_message_payload(raw_payload))
                visible = ""
            elif isinstance(msg_type, str) and msg_type.startswith("BOB."):
                # Preserve fail-closed semantics for unknown protocol types even
                # when markdown fences were stripped by the UI transport.
                _parse_message_payload(raw_payload)

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
