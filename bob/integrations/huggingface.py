from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from enum import Enum
from typing import Any

from huggingface_hub import HfApi

from bob.errors import ProtocolError
from bob.workspaces import Workspace


def _serializable(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return _serializable(asdict(value))
    if hasattr(value, "__dict__"):
        return {k: _serializable(v) for k, v in vars(value).items() if not k.startswith("_")}
    if isinstance(value, (list, tuple)):
        return [_serializable(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _serializable(v) for k, v in value.items()}
    return str(value)


class HuggingFaceAdapter:
    def __init__(self, token: str):
        self.api = HfApi(token=token)
        self.token = token

    def capabilities(self) -> list[str]:
        return [
            "hf.list_jobs",
            "hf.inspect_job",
            "hf.job_logs",
            "hf.run_job",
            "hf.cancel_job",
        ]

    def _namespace(self, workspace: Workspace) -> str | None:
        cfg = workspace.providers.get("hugging_face") or {}
        return cfg.get("namespace")

    def read(self, workspace: Workspace, tool: str, args: dict[str, Any]) -> Any:
        namespace = self._namespace(workspace)
        if tool == "hf.list_jobs":
            jobs = self.api.list_jobs(
                namespace=namespace,
                status=args.get("status"),
                token=self.token,
            )
            return [_serializable(job) for job in jobs]
        if tool == "hf.inspect_job":
            job_id = args.get("job_id")
            if not job_id:
                raise ProtocolError("hf.inspect_job requires job_id")
            return _serializable(
                self.api.inspect_job(str(job_id), namespace=namespace, token=self.token)
            )
        if tool == "hf.job_logs":
            job_id = args.get("job_id")
            if not job_id:
                raise ProtocolError("hf.job_logs requires job_id")
            logs = self.api.fetch_job_logs(str(job_id), namespace=namespace, token=self.token)
            return _serializable(list(logs) if not isinstance(logs, str) else logs)
        raise ProtocolError(f"unsupported Hugging Face read tool: {tool}")

    def effect(self, workspace: Workspace, tool: str, args: dict[str, Any]) -> Any:
        namespace = self._namespace(workspace)
        if tool == "hf.run_job":
            image = args.get("image")
            command = args.get("command")
            if not image or not isinstance(command, list) or not command:
                raise ProtocolError("hf.run_job requires image and non-empty command list")
            job = self.api.run_job(
                image=str(image),
                command=[str(x) for x in command],
                flavor=args.get("flavor"),
                namespace=namespace,
                env=args.get("env"),
                secrets=args.get("secrets"),
                labels=args.get("labels"),
                token=self.token,
            )
            return _serializable(job)
        if tool == "hf.cancel_job":
            job_id = args.get("job_id")
            if not job_id:
                raise ProtocolError("hf.cancel_job requires job_id")
            return _serializable(
                self.api.cancel_job(str(job_id), namespace=namespace, token=self.token)
            )
        raise ProtocolError(f"unsupported Hugging Face effect tool: {tool}")
