from __future__ import annotations

from dataclasses import dataclass


# Canonical initial engineering defaults for Bob cognition.
#
# These values deliberately target cognitive headroom rather than the maximum
# context a model may technically accept. They are learnable parameters:
# future evidence may justify changing the numbers, but callers must not
# silently exceed the hard limit.
DEFAULT_MODULE_TARGET_TOKENS = 14_900
DEFAULT_MODULE_HARD_CAP_TOKENS = 15_000
DEFAULT_COMPILED_CONTEXT_TARGET_TOKENS = 20_000
DEFAULT_COMPILED_CONTEXT_HARD_LIMIT_TOKENS = 25_000


@dataclass(frozen=True)
class CognitionPolicy:
    """Bounded-context policy for one stateless cognition request."""

    module_target_tokens: int = DEFAULT_MODULE_TARGET_TOKENS
    module_hard_cap_tokens: int = DEFAULT_MODULE_HARD_CAP_TOKENS
    target_tokens: int = DEFAULT_COMPILED_CONTEXT_TARGET_TOKENS
    hard_limit_tokens: int = DEFAULT_COMPILED_CONTEXT_HARD_LIMIT_TOKENS
    fresh_chat_per_request: bool = True

    def __post_init__(self) -> None:
        if self.module_target_tokens <= 0:
            raise ValueError("module_target_tokens must be positive")
        if self.module_hard_cap_tokens < self.module_target_tokens:
            raise ValueError("module_hard_cap_tokens must be >= module_target_tokens")
        if self.target_tokens <= 0:
            raise ValueError("target_tokens must be positive")
        if self.hard_limit_tokens < self.target_tokens:
            raise ValueError("hard_limit_tokens must be >= target_tokens")
        if not self.fresh_chat_per_request:
            raise ValueError(
                "Bob cognition policy requires a fresh ChatGPT conversation per request"
            )

    def classify(self, compiled_input_tokens: int) -> str:
        """Classify a measured compiled input against the cognition envelope.

        Token counting is intentionally delegated to the cognition/model adapter
        so Bob can use an exact tokenizer when one is available.
        """
        if compiled_input_tokens < 0:
            raise ValueError("compiled_input_tokens must be >= 0")
        if compiled_input_tokens > self.hard_limit_tokens:
            return "REJECT"
        if compiled_input_tokens > self.target_tokens:
            return "ABOVE_TARGET"
        return "FIT"

    def require_fit(self, compiled_input_tokens: int) -> None:
        """Fail closed when a compiled cognition packet exceeds the hard ceiling."""
        status = self.classify(compiled_input_tokens)
        if status == "REJECT":
            raise ValueError(
                "compiled cognition context exceeds hard limit: "
                f"{compiled_input_tokens} > {self.hard_limit_tokens} tokens"
            )

    def require_module_size(self, module_tokens: int) -> None:
        """Fail closed when a module itself exceeds the canonical 15k hard cap."""
        if module_tokens < 0:
            raise ValueError("module_tokens must be >= 0")
        if module_tokens > self.module_hard_cap_tokens:
            raise ValueError(
                "module exceeds hard cap: "
                f"{module_tokens} > {self.module_hard_cap_tokens} tokens"
            )


DEFAULT_COGNITION_POLICY = CognitionPolicy()
