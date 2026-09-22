from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .errors import ConfigurationError


@dataclass(frozen=True)
class Workspace:
    code: str
    name: str
    github_repository: str
    github_repository_id: int
    default_branch: str
    entry_documents: tuple[str, ...]
    providers: dict[str, Any]
    effects: dict[str, bool]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Workspace":
        if data.get("schema") != "BUILDER_WORKSPACE_V1":
            raise ConfigurationError("workspace schema must be BUILDER_WORKSPACE_V1")
        project = data.get("project") or {}
        github = data.get("github") or {}
        context = data.get("context") or {}
        required = {
            "project.name": project.get("name"),
            "project.code": project.get("code"),
            "github.repository": github.get("repository"),
            "github.repository_id": github.get("repository_id"),
        }
        missing = [key for key, value in required.items() if value in (None, "")]
        if missing:
            raise ConfigurationError(f"workspace missing required fields: {', '.join(missing)}")
        repo_id = github["repository_id"]
        if not isinstance(repo_id, int) or repo_id <= 0:
            raise ConfigurationError("github.repository_id must be a positive integer")
        return cls(
            code=str(project["code"]),
            name=str(project["name"]),
            github_repository=str(github["repository"]),
            github_repository_id=repo_id,
            default_branch=str(github.get("default_branch") or "main"),
            entry_documents=tuple(context.get("entry_documents") or ()),
            providers=dict(data.get("providers") or {}),
            effects={str(k): bool(v) for k, v in (data.get("effects") or {}).items()},
        )

    def public_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "name": self.name,
            "github": {
                "repository": self.github_repository,
                "repository_id": self.github_repository_id,
                "default_branch": self.default_branch,
            },
            "entry_documents": list(self.entry_documents),
            "providers": self.providers,
            "effects": self.effects,
        }


class WorkspaceRegistry:
    def __init__(self, directory: str | Path):
        self.directory = Path(directory)

    def list(self) -> list[Workspace]:
        if not self.directory.exists():
            return []
        result: list[Workspace] = []
        for path in sorted(self.directory.glob("*.json")):
            if path.name.startswith("_"):
                continue
            result.append(self._load_path(path))
        return result

    def get(self, code: str) -> Workspace:
        normalized = code.strip().lower()
        matches = [w for w in self.list() if w.code.lower() == normalized]
        if len(matches) != 1:
            raise ConfigurationError(f"workspace not found or ambiguous: {code}")
        return matches[0]

    def _load_path(self, path: Path) -> Workspace:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ConfigurationError(f"invalid workspace file {path}: {exc}") from exc
        return Workspace.from_dict(data)
