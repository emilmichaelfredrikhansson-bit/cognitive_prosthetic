from __future__ import annotations

import copy
import hashlib
import json
import os
import subprocess
import tempfile
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .errors import ConfigurationError, ProtocolError
from .selfdev_queue import SelfDevelopmentQueue
from .worktree_coordination import ExecutionCoordinator


SCHEMA = "BOB_SELF_DEVELOPMENT_PROMOTION_V1"
PENDING = "PENDING_OPERATOR_REVIEW"
APPROVED = "APPROVED_FOR_MANUAL_PROMOTION"
REJECTED = "REJECTED"
STALE = "STALE_REVALIDATION_REQUIRED"
REBASE = "REBASE_REVERIFY_REQUIRED"
PROPOSAL_STATES = {PENDING, APPROVED, REJECTED, STALE, REBASE}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return f"promotion-{uuid.uuid4().hex[:12]}"


def _digest(value: Any) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class SelfDevelopmentPromotionGate:
    """Durable operator-review gate; never performs promotion itself."""

    def __init__(
        self,
        path: str | Path,
        queue: SelfDevelopmentQueue,
        execution: ExecutionCoordinator,
    ):
        self.path = Path(path)
        self.queue = queue
        self.execution = execution
        self._lock = threading.RLock()
        if (
            queue.repository_id != execution.repository_id
            or queue.repository_full_name.casefold()
            != execution.repository_full_name.casefold()
            or queue.canonical_ref != execution.canonical_ref
        ):
            raise ConfigurationError(
                "self-development promotion repository binding mismatch"
            )
        self._state = self._load()

    def _identity(self) -> dict[str, Any]:
        return {
            "id": self.queue.repository_id,
            "full_name": self.queue.repository_full_name,
            "canonical_ref": self.queue.canonical_ref,
        }

    def _empty(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "repository": self._identity(),
            "proposals": {},
            "order": [],
            "updated_at": _now(),
        }

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return self._empty()
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ConfigurationError(
                f"invalid self-development promotion store: {self.path}"
            ) from exc
        if data.get("schema") != SCHEMA:
            raise ConfigurationError("self-development promotion schema mismatch")
        if data.get("repository") != self._identity():
            raise ConfigurationError(
                "self-development promotion repository identity mismatch"
            )
        proposals = data.get("proposals")
        order = data.get("order")
        if not isinstance(proposals, dict) or not isinstance(order, list):
            raise ConfigurationError("invalid self-development promotion state")
        if len(order) != len(set(order)) or set(order) != set(proposals):
            raise ConfigurationError("promotion proposal order/state mismatch")
        for proposal in proposals.values():
            if proposal.get("state") not in PROPOSAL_STATES:
                raise ConfigurationError("invalid promotion proposal state")
        return data

    @staticmethod
    def _write_fsync(path: Path, payload: str) -> None:
        with path.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())

    def _persist(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._state["updated_at"] = _now()
        payload = json.dumps(self._state, indent=2, sort_keys=True) + "\n"
        fd, temp_name = tempfile.mkstemp(
            prefix=self.path.name + ".",
            suffix=".tmp",
            dir=str(self.path.parent),
            text=True,
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            try:
                os.replace(temp_name, self.path)
            except PermissionError:
                if os.name != "nt":
                    raise
                self._write_fsync(self.path, payload)
                if self.path.read_text(encoding="utf-8") != payload:
                    raise ConfigurationError(
                        "Windows promotion persistence verification failed"
                    )
        finally:
            try:
                os.unlink(temp_name)
            except FileNotFoundError:
                pass

    def _item(self, item_id: str) -> dict[str, Any]:
        for item in self.queue.snapshot()["items"]:
            if item["item_id"] == str(item_id):
                return item
        raise ProtocolError(f"unknown self-development item: {item_id}")

    def _proposal(self, proposal_id: str) -> dict[str, Any]:
        with self._lock:
            proposal = self._state["proposals"].get(str(proposal_id))
            if proposal is None:
                raise ProtocolError(f"unknown promotion proposal: {proposal_id}")
            return copy.deepcopy(proposal)

    def _is_ancestor(self, ancestor: str, descendant: str) -> bool:
        process = subprocess.run(
            ["git", "merge-base", "--is-ancestor", ancestor, descendant],
            cwd=str(self.execution.repo_root),
            check=False,
            capture_output=True,
            text=True,
        )
        if process.returncode not in {0, 1}:
            raise ConfigurationError(
                (process.stderr or process.stdout or "git ancestry check failed").strip()
            )
        return process.returncode == 0

    def _qualified_candidate(self, item_id: str) -> dict[str, Any]:
        item = self._item(item_id)
        if item.get("state") != "QUALIFIED":
            raise ProtocolError(
                "promotion proposal requires QUALIFIED self-development"
            )
        verification = item.get("verification")
        if not isinstance(verification, dict) or not verification:
            raise ProtocolError("qualified self-development has no verification")
        receipt = verification.get("execution")
        if not isinstance(receipt, dict):
            raise ProtocolError("qualification lacks execution receipt")
        run_id = str(item.get("execution_run_id") or "")
        if receipt.get("run_id") != run_id:
            raise ProtocolError("qualification execution receipt/run binding mismatch")
        run = self.execution.ledger.get_run(run_id)
        authority = run.get("authority") or {}
        if (
            run.get("lane") != "selfdev"
            or authority.get("selfdev_item_id") != item["item_id"]
            or authority.get("promotion_authority") != "NONE"
            or receipt.get("promotion_authority") != "NONE"
        ):
            raise ProtocolError("candidate does not preserve no-promotion authority")
        if run.get("state") != "CANCELLED":
            raise ProtocolError("qualified candidate execution must be CANCELLED")
        if receipt.get("branch") != run.get("branch"):
            raise ProtocolError("qualification branch receipt mismatch")
        qualified_head = str(receipt.get("head_sha") or "")
        if not qualified_head:
            raise ProtocolError("qualification lacks candidate head SHA")
        actual_head = self.execution.worktrees.branch_head(run["branch"])
        if actual_head != qualified_head:
            raise ProtocolError(
                "qualified candidate branch moved after verification"
            )
        return {
            "item": item,
            "run": run,
            "candidate_head_sha": actual_head,
            "qualification_hash": _digest(verification),
        }

    def _fresh_state(
        self,
        proposal: dict[str, Any],
    ) -> tuple[str, str | None, str]:
        try:
            candidate = self._qualified_candidate(proposal["item_id"])
        except (ProtocolError, ConfigurationError) as exc:
            return STALE, f"QUALIFICATION_STALE:{type(exc).__name__}", ""
        if (
            candidate["run"]["run_id"] != proposal["run_id"]
            or candidate["run"]["branch"] != proposal["branch"]
            or candidate["candidate_head_sha"] != proposal["candidate_head_sha"]
            or candidate["qualification_hash"] != proposal["qualification_hash"]
        ):
            return STALE, "CANDIDATE_OR_QUALIFICATION_CHANGED", ""
        canonical_sha = self.execution.worktrees.resolve_ref(
            self.queue.canonical_ref
        )
        if canonical_sha == proposal["candidate_head_sha"]:
            return STALE, "CANDIDATE_ALREADY_CANONICAL", canonical_sha
        if not self._is_ancestor(canonical_sha, proposal["candidate_head_sha"]):
            return REBASE, "CANONICAL_NOT_ANCESTOR_OF_CANDIDATE", canonical_sha
        if (
            proposal.get("state") == APPROVED
            and proposal.get("approved_canonical_sha") != canonical_sha
        ):
            return STALE, "APPROVED_CANONICAL_MOVED", canonical_sha
        return proposal["state"], None, canonical_sha

    def create(self, item_id: str) -> dict[str, Any]:
        candidate = self._qualified_candidate(item_id)
        with self._lock:
            for proposal in self._state["proposals"].values():
                if (
                    proposal.get("item_id") == candidate["item"]["item_id"]
                    and proposal.get("state") in {PENDING, APPROVED}
                ):
                    raise ProtocolError(
                        "self-development item already has an open promotion proposal"
                    )
        canonical_sha = self.execution.worktrees.resolve_ref(
            self.queue.canonical_ref
        )
        if canonical_sha == candidate["candidate_head_sha"]:
            raise ProtocolError("qualified candidate is already canonical")
        state = (
            PENDING
            if self._is_ancestor(canonical_sha, candidate["candidate_head_sha"])
            else REBASE
        )
        proposal = {
            "proposal_id": _new_id(),
            "item_id": candidate["item"]["item_id"],
            "run_id": candidate["run"]["run_id"],
            "branch": candidate["run"]["branch"],
            "candidate_head_sha": candidate["candidate_head_sha"],
            "qualification_hash": candidate["qualification_hash"],
            "canonical_ref": self.queue.canonical_ref,
            "canonical_sha_at_proposal": canonical_sha,
            "canonical_sha_current": canonical_sha,
            "state": state,
            "stale_reason": (
                None if state == PENDING else "CANONICAL_NOT_ANCESTOR_OF_CANDIDATE"
            ),
            "merge_authority": "NONE",
            "provider_effect_performed": False,
            "created_at": _now(),
            "reviewed_at": None,
            "review_reason": None,
            "approved_candidate_head_sha": None,
            "approved_canonical_sha": None,
        }
        with self._lock:
            self._state["proposals"][proposal["proposal_id"]] = proposal
            self._state["order"].append(proposal["proposal_id"])
            self._persist()
        return copy.deepcopy(proposal)

    def revalidate(self, proposal_id: str) -> dict[str, Any]:
        proposal = self._proposal(proposal_id)
        if proposal["state"] == REJECTED:
            return proposal
        state, reason, canonical_sha = self._fresh_state(proposal)
        with self._lock:
            stored = self._state["proposals"][proposal["proposal_id"]]
            if canonical_sha:
                stored["canonical_sha_current"] = canonical_sha
            if reason:
                stored["state"] = state
                stored["stale_reason"] = reason
            elif stored["state"] in {STALE, REBASE}:
                # Stale qualification/candidate identity cannot be revived in place.
                pass
            else:
                stored["stale_reason"] = None
            self._persist()
            return copy.deepcopy(stored)

    def approve(
        self,
        proposal_id: str,
        *,
        expected_candidate_head_sha: str,
        expected_canonical_sha: str,
    ) -> dict[str, Any]:
        proposal = self._proposal(proposal_id)
        if proposal["state"] != PENDING:
            raise ProtocolError("only pending promotion proposals can be approved")
        fresh = self.revalidate(proposal_id)
        if fresh["state"] != PENDING:
            raise ProtocolError(
                f"promotion proposal is not fresh: {fresh['state']}"
            )
        expected_candidate_head_sha = str(expected_candidate_head_sha or "").strip()
        expected_canonical_sha = str(expected_canonical_sha or "").strip()
        if not expected_candidate_head_sha or not expected_canonical_sha:
            raise ProtocolError("promotion approval requires exact candidate/canonical SHAs")
        if expected_candidate_head_sha != fresh["candidate_head_sha"]:
            raise ProtocolError("promotion candidate SHA approval mismatch")
        if expected_canonical_sha != fresh["canonical_sha_current"]:
            raise ProtocolError("promotion canonical SHA approval mismatch")
        with self._lock:
            stored = self._state["proposals"][proposal_id]
            stored["state"] = APPROVED
            stored["reviewed_at"] = _now()
            stored["review_reason"] = "OPERATOR_APPROVED_REVIEW_ONLY"
            stored["approved_candidate_head_sha"] = expected_candidate_head_sha
            stored["approved_canonical_sha"] = expected_canonical_sha
            stored["merge_authority"] = "NONE"
            stored["provider_effect_performed"] = False
            self._persist()
            return copy.deepcopy(stored)

    def reject(self, proposal_id: str, *, reason: str) -> dict[str, Any]:
        reason = str(reason or "").strip()
        if not reason:
            raise ProtocolError("promotion rejection requires a reason")
        proposal = self._proposal(proposal_id)
        if proposal["state"] not in {PENDING, STALE, REBASE}:
            raise ProtocolError("promotion proposal cannot be rejected from this state")
        with self._lock:
            stored = self._state["proposals"][proposal_id]
            stored["state"] = REJECTED
            stored["reviewed_at"] = _now()
            stored["review_reason"] = reason
            stored["merge_authority"] = "NONE"
            stored["provider_effect_performed"] = False
            self._persist()
            return copy.deepcopy(stored)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            proposals = [
                copy.deepcopy(self._state["proposals"][proposal_id])
                for proposal_id in self._state["order"]
            ]
            counts = {state: 0 for state in sorted(PROPOSAL_STATES)}
            for proposal in proposals:
                counts[proposal["state"]] += 1
            return {
                "schema": SCHEMA,
                "repository": copy.deepcopy(self._state["repository"]),
                "proposals": proposals,
                "counts": counts,
                "updated_at": self._state.get("updated_at"),
            }
