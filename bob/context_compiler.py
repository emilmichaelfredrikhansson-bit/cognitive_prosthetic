from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from .cognition_policy import CognitionPolicy, DEFAULT_COGNITION_POLICY
from .module_graph import ModuleFootprint, ModuleGraph, ModuleNode, estimate_tokens


@dataclass(frozen=True)
class CompiledContext:
    prompt: str
    token_count: int
    classification: str
    source_pointers: tuple[str, ...]

    def public_dict(self) -> dict[str, Any]:
        return {
            "token_count": self.token_count,
            "classification": self.classification,
            "source_pointers": list(self.source_pointers),
        }


class ContextCompiler:
    """Compile a self-contained fresh-cognition problem from durable Bob state."""

    def __init__(self, policy: CognitionPolicy = DEFAULT_COGNITION_POLICY):
        self.policy = policy

    def compile_module_problem(
        self,
        *,
        workspace: Any,
        graph: ModuleGraph,
        module: ModuleNode,
        footprint: ModuleFootprint,
        problem: str,
        ref: str,
        continuation: tuple[str, ...] = (),
        architecture_repair: bool = False,
    ) -> CompiledContext:
        neighbors = graph.neighbors(module)
        pointers = tuple(dict.fromkeys(
            module.owned_paths
            + tuple(path for n in neighbors for path in n.owned_paths)
        ))

        packet = {
            "schema": "BOB_COMPILED_CONTEXT_V1",
            "mode": "ARCHITECTURE_REPAIR" if architecture_repair else "MODULE_WORK",
            "workspace": {
                "code": workspace.code,
                "repository": workspace.github_repository,
                "repository_id": workspace.github_repository_id,
                "ref": ref,
            },
            "hard_invariants": {
                "module_hard_cap_tokens": self.policy.module_hard_cap_tokens,
                "compiled_context_hard_limit_tokens": self.policy.hard_limit_tokens,
                "fresh_chat_per_request": True,
                "github_is_implementation_truth": True,
            },
            "module": {
                **module.summary_dict(),
                "footprint": footprint.public_dict(),
                "source_paths": list(module.source_paths),
                "test_paths": list(module.test_paths),
                "contract_paths": list(module.contract_paths),
            },
            "neighbors": [n.summary_dict() for n in neighbors],
            "source_pointers": list(pointers),
            "problem": problem.strip(),
            "continuation_results": list(continuation),
        }

        instructions = (
            "You are one fresh Bob cognition process. Do not rely on prior chat history.\n"
            "The connected GitHub repository is authoritative implementation truth. "
            "Use the supplied repo/ref/source pointers and inspect GitHub directly whenever "
            "code/history/tests are needed. Bob summaries are navigation, not a substitute "
            "for source truth.\n"
            "A Bob module may never exceed 15,000 measured tokens. Treat a solution that "
            "would violate that cap as invalid; reorganize responsibilities/contracts instead.\n"
            "Solve the bounded problem and check material impact on direct contracts/neighbors "
            "and product intent before completion. Ask the operator only for genuine "
            "product/vision/end-goal or authority decisions.\n"
            "Use BOB protocol messages only for Bob-owned reads/effects/ASK/DONE. "
            "Repository inspection through your connected GitHub integration does not need "
            "a BOB.READ round-trip.\n\n"
            "BOB.COMPILED_CONTEXT\n"
            + json.dumps(packet, ensure_ascii=False, sort_keys=True, indent=2)
        )

        token_count = estimate_tokens(instructions)
        self.policy.require_fit(token_count)
        return CompiledContext(
            prompt=instructions,
            token_count=token_count,
            classification=self.policy.classify(token_count),
            source_pointers=pointers,
        )
