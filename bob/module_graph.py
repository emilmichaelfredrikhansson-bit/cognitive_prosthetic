from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from .errors import ConfigurationError


BOB_MODULE_GRAPH_SCHEMA = "BOB_MODULE_GRAPH_V1"
BOB_TOKEN_ESTIMATE_SCHEMA = "BOB_TOKEN_ESTIMATE_V1"


def estimate_tokens(text: str) -> int:
    """Deterministic conservative token estimate used for hard-cap enforcement.

    GPT product tokenization is not exposed to Bob locally. V1 deliberately uses
    UTF-8 bytes / 3, rounded up, which is conservative for ordinary source/code.
    The measurement contract is versioned so a future exact tokenizer can replace
    it without silently changing historical receipts.
    """
    if not isinstance(text, str):
        raise TypeError("text must be str")
    return math.ceil(len(text.encode("utf-8")) / 3)


@dataclass(frozen=True)
class ModuleNode:
    module_id: str
    purpose: str
    source_paths: tuple[str, ...]
    test_paths: tuple[str, ...]
    contract_paths: tuple[str, ...]
    producers: tuple[str, ...]
    consumers: tuple[str, ...]
    invariants: tuple[str, ...]
    status: str

    @property
    def owned_paths(self) -> tuple[str, ...]:
        return self.source_paths + self.test_paths + self.contract_paths

    def summary_dict(self) -> dict[str, Any]:
        return {
            "id": self.module_id,
            "purpose": self.purpose,
            "producers": list(self.producers),
            "consumers": list(self.consumers),
            "invariants": list(self.invariants),
            "status": self.status,
        }


@dataclass(frozen=True)
class ModuleGraph:
    workspace_code: str
    repository_id: int
    modules: tuple[ModuleNode, ...]
    coverage: str = "PARTIAL"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ModuleGraph":
        if data.get("schema") != BOB_MODULE_GRAPH_SCHEMA:
            raise ConfigurationError(f"module graph schema must be {BOB_MODULE_GRAPH_SCHEMA}")
        workspace_code = str(data.get("workspace_code") or "").strip()
        repository_id = data.get("repository_id")
        if not workspace_code:
            raise ConfigurationError("module graph requires workspace_code")
        if not isinstance(repository_id, int) or repository_id <= 0:
            raise ConfigurationError("module graph repository_id must be a positive integer")

        raw_modules = data.get("modules")
        if not isinstance(raw_modules, list) or not raw_modules:
            raise ConfigurationError("module graph requires at least one module")

        modules: list[ModuleNode] = []
        seen_ids: set[str] = set()
        owned: dict[str, str] = {}
        for raw in raw_modules:
            if not isinstance(raw, dict):
                raise ConfigurationError("module entries must be objects")
            module_id = str(raw.get("id") or "").strip()
            purpose = str(raw.get("purpose") or "").strip()
            if not module_id or not purpose:
                raise ConfigurationError("each module requires id and purpose")
            if module_id in seen_ids:
                raise ConfigurationError(f"duplicate module id: {module_id}")
            seen_ids.add(module_id)

            def paths(key: str) -> tuple[str, ...]:
                values = tuple(str(v).strip() for v in (raw.get(key) or ()))
                if any(not v or v.startswith("/") or ".." in v.split("/") for v in values):
                    raise ConfigurationError(f"module {module_id} has invalid {key}")
                return values

            node = ModuleNode(
                module_id=module_id,
                purpose=purpose,
                source_paths=paths("source_paths"),
                test_paths=paths("test_paths"),
                contract_paths=paths("contract_paths"),
                producers=tuple(str(v) for v in (raw.get("producers") or ())),
                consumers=tuple(str(v) for v in (raw.get("consumers") or ())),
                invariants=tuple(str(v) for v in (raw.get("invariants") or ())),
                status=str(raw.get("status") or "PLANNED"),
            )
            if not node.owned_paths:
                raise ConfigurationError(f"module {module_id} owns no paths")
            for path in node.owned_paths:
                previous = owned.get(path)
                if previous:
                    raise ConfigurationError(
                        f"path {path} is owned by both {previous} and {module_id}"
                    )
                owned[path] = module_id
            modules.append(node)

        ids = {m.module_id for m in modules}
        for module in modules:
            unknown = (set(module.producers) | set(module.consumers)) - ids
            if unknown:
                raise ConfigurationError(
                    f"module {module.module_id} references unknown modules: {sorted(unknown)}"
                )

        return cls(
            workspace_code=workspace_code,
            repository_id=repository_id,
            modules=tuple(modules),
            coverage=str(data.get("coverage") or "PARTIAL"),
        )

    def require_workspace(self, workspace: Any) -> None:
        if self.workspace_code.lower() != workspace.code.lower():
            raise ConfigurationError(
                f"module graph workspace mismatch: {self.workspace_code} != {workspace.code}"
            )
        if self.repository_id != workspace.github_repository_id:
            raise ConfigurationError(
                "module graph repository_id does not match workspace repository identity"
            )

    def get(self, module_id: str) -> ModuleNode:
        matches = [m for m in self.modules if m.module_id.lower() == module_id.strip().lower()]
        if len(matches) != 1:
            raise ConfigurationError(f"module not found or ambiguous: {module_id}")
        return matches[0]

    def neighbors(self, module: ModuleNode) -> tuple[ModuleNode, ...]:
        ids = set(module.producers) | set(module.consumers)
        return tuple(m for m in self.modules if m.module_id in ids)


@dataclass(frozen=True)
class ModuleFootprint:
    module_id: str
    token_count: int
    measurement: str
    files: tuple[dict[str, Any], ...]

    def public_dict(self) -> dict[str, Any]:
        return {
            "module_id": self.module_id,
            "token_count": self.token_count,
            "measurement": self.measurement,
            "files": list(self.files),
        }


def measure_module(
    workspace: Any,
    module: ModuleNode,
    github: Any,
    ref: str,
    preloaded: dict[str, dict[str, Any]] | None = None,
) -> ModuleFootprint:
    files: list[dict[str, Any]] = []
    total = 0
    for path in module.owned_paths:
        result = preloaded[path] if preloaded is not None else github.read_file(workspace, path, ref)
        content = result.get("content")
        if not isinstance(content, str):
            raise ConfigurationError(f"module path has no text content: {path}")
        tokens = estimate_tokens(content)
        total += tokens
        files.append({
            "path": path,
            "sha": result.get("sha"),
            "tokens": tokens,
        })
    return ModuleFootprint(
        module_id=module.module_id,
        token_count=total,
        measurement=BOB_TOKEN_ESTIMATE_SCHEMA,
        files=tuple(files),
    )
