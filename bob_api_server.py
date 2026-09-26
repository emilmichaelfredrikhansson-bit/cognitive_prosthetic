#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory
from bob.campaign_work_executor import CampaignWorkExecutor
from bob.campaign_work_executor_api import create_campaign_work_executor_blueprint
from bob.driver import BobRuntime
from bob.errors import BobError
from bob.selfdev_checkpoints import SelfDevelopmentCheckpoints
from bob.selfdev_control import SelfDevelopmentControl
from bob.selfdev_control_api import create_selfdev_control_blueprint
from bob.selfdev_execution import SelfDevelopmentExecution
from bob.selfdev_promotion import SelfDevelopmentPromotionGate
from bob.selfdev_promotion_api import create_selfdev_promotion_blueprint
from bob.work_campaigns import WorkCampaignManager
from bob.work_campaign_api import create_work_campaign_blueprint
from bob.work_campaign_queue import WorkCampaignQueue
from bob.work_campaign_queue_api import create_work_campaign_queue_blueprint
from bob.work_campaign_worker import WorkCampaignWorker
from bob.work_campaign_worker_api import create_work_campaign_worker_blueprint
from bob.worktree_coordination import RepositoryCoordinatorRegistry

BASE_DIR = Path(__file__).resolve().parent
app = Flask(__name__, static_folder=str(BASE_DIR / "frontend"), static_url_path="")
runtime = BobRuntime(
    workspace_dir=os.environ.get("BOB_WORKSPACE_DIR", str(BASE_DIR / "workspaces"))
)
_bob_workspace = runtime.registry.get("BOB")
execution_registry = RepositoryCoordinatorRegistry.from_json(
    runtime.registry,
    os.environ.get("BOB_REPOSITORY_BINDINGS_JSON"),
    default_bindings={
        _bob_workspace.github_repository_id: {
            "repository_full_name": _bob_workspace.github_repository,
            "repository_id": _bob_workspace.github_repository_id,
            "repo_root": BASE_DIR,
            "canonical_ref": os.environ.get("BOB_CANONICAL_REF", "feat/bob-core-v1"),
            "state_path": os.environ.get("BOB_EXECUTION_LEDGER_PATH") or None,
            "worktree_root": os.environ.get("BOB_EXECUTION_WORKTREE_ROOT") or None,
        }
    },
    max_parallel_runs_per_repository=int(
        os.environ.get("BOB_MAX_PARALLEL_RUNS_PER_REPOSITORY", "3")
    ),
)
if runtime.selfdev_queue is None:
    raise RuntimeError("Bob API requires BOB self-development queue state")
selfdev_execution = SelfDevelopmentExecution(
    runtime.selfdev_queue,
    execution_registry.coordinator_for_workspace("BOB"),
)
selfdev_checkpoints = SelfDevelopmentCheckpoints(
    os.environ.get("BOB_SELFDEV_CHECKPOINT_PATH")
    or BASE_DIR / ".bob" / "runtime" / "selfdev_checkpoints.json",
    runtime.selfdev_queue,
    execution_registry.coordinator_for_workspace("BOB"),
)
selfdev_control = SelfDevelopmentControl(
    selfdev_execution,
    selfdev_checkpoints,
)
app.register_blueprint(
    create_selfdev_control_blueprint(
        selfdev_execution,
        selfdev_checkpoints,
    )
)
selfdev_promotion = SelfDevelopmentPromotionGate(
    os.environ.get("BOB_SELFDEV_PROMOTION_PATH")
    or BASE_DIR / ".bob" / "runtime" / "selfdev_promotions.json",
    runtime.selfdev_queue,
    execution_registry.coordinator_for_workspace("BOB"),
)
app.register_blueprint(
    create_selfdev_promotion_blueprint(selfdev_promotion)
)
work_campaigns = WorkCampaignManager(
    os.environ.get("BOB_WORK_CAMPAIGN_PATH")
    or BASE_DIR / ".bob" / "runtime" / "work_campaigns.json",
    runtime.registry,
    execution_registry,
)
app.register_blueprint(
    create_work_campaign_blueprint(work_campaigns)
)
work_campaign_queue = WorkCampaignQueue(
    os.environ.get("BOB_WORK_CAMPAIGN_QUEUE_PATH")
    or BASE_DIR / ".bob" / "runtime" / "work_campaign_queue.json",
    work_campaigns,
    execution_registry,
)
app.register_blueprint(
    create_work_campaign_queue_blueprint(work_campaign_queue)
)
work_campaign_worker = WorkCampaignWorker(
    os.environ.get("BOB_WORK_CAMPAIGN_WORKER_PATH")
    or BASE_DIR / ".bob" / "runtime" / "work_campaign_worker.json",
    work_campaigns,
    work_campaign_queue,
    execution_registry,
)
app.register_blueprint(
    create_work_campaign_worker_blueprint(work_campaign_worker)
)
campaign_work_executor = CampaignWorkExecutor(
    os.environ.get("BOB_CAMPAIGN_WORK_EXECUTOR_PATH")
    or BASE_DIR / ".bob" / "runtime" / "campaign_work_executor.json",
    runtime,
    work_campaigns,
    work_campaign_queue,
    work_campaign_worker,
    execution_registry,
    verification_commands_by_repository={
        _bob_workspace.github_repository_id: [
            [
                sys.executable,
                "-m",
                "unittest",
                "discover",
                "-s",
                "tests",
            ]
        ]
    },
)
app.register_blueprint(
    create_campaign_work_executor_blueprint(campaign_work_executor)
)


@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.errorhandler(BobError)
def handle_bob_error(exc: BobError):
    return jsonify({"success": False, "error": str(exc), "type": type(exc).__name__}), 400


@app.errorhandler(Exception)
def handle_unexpected_error(exc: Exception):
    return jsonify({"success": False, "error": str(exc), "type": type(exc).__name__}), 500


@app.get("/bob/health")
def health():
    return jsonify({
        "success": True,
        "status": "running",
        "workspaces": [w.code for w in runtime.registry.list()],
        "capabilities": runtime.capabilities(),
        "chatgpt_bridge": runtime.bridge.base_url,
    })


@app.get("/bob/workspaces")
def workspaces():
    return jsonify({
        "success": True,
        "workspaces": [w.public_dict() for w in runtime.registry.list()],
    })


@app.post("/bob/qualify")
def qualify():
    data = request.get_json(force=True) or {}
    result = runtime.qualify_workspace(str(data["workspace"]))
    return jsonify({"success": True, **result})


@app.post("/bob/new-chat")
def new_chat():
    data = request.get_json(force=True) or {}
    return jsonify({"success": True, **runtime.start_chat(str(data["workspace"]))})


@app.post("/bob/turn")
def turn():
    data = request.get_json(force=True) or {}
    result = runtime.turn(str(data["workspace"]), str(data["message"]))
    return jsonify({"success": True, **result})


@app.post("/bob/module-turn")
def module_turn():
    data = request.get_json(force=True) or {}
    result = runtime.module_turn(
        str(data["workspace"]),
        str(data["module"]),
        str(data["message"]),
        None if data.get("ref") in (None, "") else str(data["ref"]),
    )
    return jsonify({"success": True, **result})


@app.post("/bob/module-graph")
def module_graph():
    data = request.get_json(force=True) or {}
    result = runtime.module_graph_status(
        str(data["workspace"]),
        None if data.get("ref") in (None, "") else str(data["ref"]),
    )
    return jsonify({"success": True, **result})


@app.get("/bob/approvals")
def approvals():
    return jsonify({"success": True, **runtime.approval_status()})


@app.post("/bob/approve")
def approve():
    data = request.get_json(force=True) or {}
    result = runtime.approve(str(data["pending_id"]))
    return jsonify({"success": True, **result})


@app.post("/bob/reject")
def reject():
    data = request.get_json(force=True) or {}
    result = runtime.reject(str(data["pending_id"]))
    return jsonify({"success": True, **result})


@app.get("/bob/continuations")
def continuations():
    return jsonify({"success": True, **runtime.continuation_status()})


@app.post("/bob/continuations/<continuation_id>/resume")
def resume_continuation(continuation_id):
    result = runtime.resume_continuation(str(continuation_id))
    return jsonify({"success": True, **result})


@app.get("/bob/self-development")
def self_development_status():
    return jsonify({"success": True, **runtime.self_development_status()})


@app.post("/bob/self-development/items")
def self_development_enqueue():
    data = request.get_json(force=True) or {}
    item = runtime.enqueue_self_development(
        goal=str(data["goal"]),
        leases=[str(item) for item in (data.get("leases") or [])],
        expected_outcome=(
            None
            if data.get("expected_outcome") in (None, "")
            else str(data["expected_outcome"])
        ),
    )
    return jsonify({"success": True, "item": item})


@app.post("/bob/self-development/claim")
def self_development_claim():
    data = request.get_json(force=True) or {}
    result = selfdev_execution.claim_next(base_ref=str(data["base_ref"]))
    return jsonify({"success": True, **result})


@app.post("/bob/self-development/items/<item_id>/reconcile")
def self_development_reconcile(item_id):
    result = selfdev_execution.reconcile_item(str(item_id))
    return jsonify({"success": True, **result})


@app.post("/bob/self-development/items/<item_id>/finish")
def self_development_finish(item_id):
    data = request.get_json(force=True) or {}
    result = selfdev_execution.finish_item(
        str(item_id),
        state=str(data["state"]),
        verification=dict(data.get("verification") or {}),
        reason=None if data.get("reason") in (None, "") else str(data["reason"]),
    )
    return jsonify({"success": True, **result})


@app.post("/bob/read")
def direct_read():
    data = request.get_json(force=True) or {}
    result = runtime.direct_read(
        str(data["workspace"]),
        str(data["tool"]),
        dict(data.get("args") or {}),
    )
    return jsonify({"success": True, "result": result})


@app.post("/bob/project-search")
def project_search():
    data = request.get_json(force=True) or {}
    result = runtime.search_project_context(
        str(data["workspace"]),
        str(data.get("query") or ""),
        data.get("limit", 20),
    )
    return jsonify({"success": True, **result})


@app.get("/bob/execution")
def execution_status():
    return jsonify({"success": True, **execution_registry.snapshot()})


@app.post("/bob/execution/runs")
def execution_create_run():
    data = request.get_json(force=True) or {}
    workspace_code = str(data["workspace"])
    workspace = runtime.registry.get(workspace_code)
    execution = execution_registry.coordinator_for_workspace(workspace_code)
    lane = str(data.get("lane") or "interactive")
    authority = {
        "workspace": workspace.code,
        "repository": workspace.github_repository,
        "repository_id": workspace.github_repository_id,
        "effects": dict(workspace.effects),
    }
    if lane == "interactive":
        result = selfdev_control.create_interactive(
            execution,
            goal=str(data["goal"]),
            workspace=workspace_code,
            base_ref=str(data["base_ref"]),
            leases=[str(item) for item in (data.get("leases") or [])],
            depends_on=[str(item) for item in (data.get("depends_on") or [])],
            authority=authority,
        )
        campaign_preemption = work_campaign_worker.preempt_for_interactive(
            execution,
            result["run"]["run_id"],
        )
        result["run"] = execution.ledger.get_run(result["run"]["run_id"])
        return jsonify({
            "success": True,
            **result,
            "campaign_preemption": campaign_preemption,
        })
    result = execution.create_run(
        goal=str(data["goal"]),
        workspace=workspace_code,
        base_ref=str(data["base_ref"]),
        leases=[str(item) for item in (data.get("leases") or [])],
        depends_on=[str(item) for item in (data.get("depends_on") or [])],
        lane=lane,
        authority=authority,
    )
    return jsonify({"success": True, "run": result})


@app.get("/bob/execution/runs/<run_id>")
def execution_get_run(run_id):
    execution = execution_registry.coordinator_for_run(run_id)
    return jsonify({"success": True, "run": execution.ledger.get_run(run_id)})


@app.post("/bob/execution/runs/<run_id>/cognitions")
def execution_begin_cognition(run_id):
    data = request.get_json(force=True) or {}
    execution = execution_registry.coordinator_for_run(run_id)
    result = execution.ledger.begin_cognition(
        run_id,
        purpose=str(data["purpose"]),
        request_id=None if data.get("request_id") in (None, "") else str(data["request_id"]),
    )
    return jsonify({"success": True, "cognition": result})


@app.post("/bob/execution/cognitions/<cognition_id>/finish")
def execution_finish_cognition(cognition_id):
    data = request.get_json(force=True) or {}
    execution = execution_registry.coordinator_for_cognition(cognition_id)
    result = execution.ledger.finish_cognition(
        cognition_id,
        success=bool(data.get("success")),
        summary=None if data.get("summary") is None else str(data.get("summary")),
        error=None if data.get("error") is None else str(data.get("error")),
    )
    return jsonify({"success": True, "cognition": result})


@app.post("/bob/execution/runs/<run_id>/awaiting-approval")
def execution_awaiting_approval(run_id):
    execution = execution_registry.coordinator_for_run(run_id)
    return jsonify({
        "success": True,
        "run": execution.ledger.mark_awaiting_approval(run_id),
    })


@app.post("/bob/execution/runs/<run_id>/resume")
def execution_resume(run_id):
    execution = execution_registry.coordinator_for_run(run_id)
    return jsonify({
        "success": True,
        "run": execution.ledger.resume_after_approval(run_id),
    })


@app.post("/bob/execution/runs/<run_id>/ready")
def execution_ready(run_id):
    data = request.get_json(force=True) or {}
    execution = execution_registry.coordinator_for_run(run_id)
    result = execution.mark_ready_for_integration(
        run_id,
        verified_base_sha=str(data["verified_base_sha"]),
        verification=dict(data.get("verification") or {}),
    )
    return jsonify({"success": True, "run": result})


@app.post("/bob/execution/runs/<run_id>/reverified")
def execution_reverified(run_id):
    data = request.get_json(force=True) or {}
    execution = execution_registry.coordinator_for_run(run_id)
    result = execution.record_rebase_verification(
        run_id,
        canonical_ref=str(data["canonical_ref"]),
        verification=dict(data.get("verification") or {}),
    )
    return jsonify({"success": True, "run": result})


@app.post("/bob/execution/integration/plan")
def execution_integration_plan():
    data = request.get_json(force=True) or {}
    execution = execution_registry.coordinator_for_workspace(str(data["workspace"]))
    result = execution.integration_plan(
        None if data.get("canonical_ref") in (None, "") else str(data["canonical_ref"])
    )
    return jsonify({"success": True, **result})


@app.post("/bob/execution/integration/claim")
def execution_integration_claim():
    data = request.get_json(force=True) or {}
    run_id = str(data["run_id"])
    execution = execution_registry.coordinator_for_run(run_id)
    result = execution.begin_integration(
        run_id,
        canonical_ref=None if data.get("canonical_ref") in (None, "") else str(data["canonical_ref"]),
    )
    return jsonify({"success": True, "run": result})


@app.post("/bob/execution/runs/<run_id>/integrated")
def execution_integrated(run_id):
    data = request.get_json(force=True) or {}
    execution = execution_registry.coordinator_for_run(run_id)
    result = execution.complete_integration(
        run_id,
        canonical_ref=None if data.get("canonical_ref") in (None, "") else str(data["canonical_ref"]),
    )
    release = None
    campaign_release = None
    if result.get("lane") == "interactive":
        if execution.repository_id == selfdev_execution.execution.repository_id:
            release = selfdev_control.resume_after_interactive(run_id)
        campaign_release = work_campaign_worker.resume_after_interactive(run_id)
    return jsonify({
        "success": True,
        "run": result,
        "preemption_release": release,
        "campaign_preemption_release": campaign_release,
    })


@app.post("/bob/execution/runs/<run_id>/cancel")
def execution_cancel(run_id):
    data = request.get_json(silent=True) or {}
    execution = execution_registry.coordinator_for_run(run_id)
    result = execution.cancel_run(
        run_id,
        reason=str(data.get("reason") or "cancelled"),
    )
    release = None
    campaign_release = None
    if result.get("lane") == "interactive":
        if execution.repository_id == selfdev_execution.execution.repository_id:
            release = selfdev_control.resume_after_interactive(run_id)
        campaign_release = work_campaign_worker.resume_after_interactive(run_id)
    return jsonify({
        "success": True,
        "run": result,
        "preemption_release": release,
        "campaign_preemption_release": campaign_release,
    })


@app.post("/bob/relay/start")
def relay_start():
    data = request.get_json(force=True) or {}
    result = runtime.relay_start(
        str(data["workspace"]),
        str(data["message"]),
    )
    return jsonify({"success": True, **result})


@app.post("/bob/relay")
def relay():
    data = request.get_json(force=True) or {}
    result = runtime.relay_model_response(
        str(data["workspace"]),
        str(data["model_response"]),
    )
    return jsonify({"success": True, **result})


@app.post("/bob/relay/approve")
def relay_approve():
    data = request.get_json(force=True) or {}
    result = runtime.relay_approve(str(data["pending_id"]))
    return jsonify({"success": True, **result})


if __name__ == "__main__":
    host = os.environ.get("BOB_HOST", "127.0.0.1").strip() or "127.0.0.1"
    port = int(os.environ.get("BOB_PORT", "5002"))
    app.run(host=host, port=port, debug=False, threaded=True)
