from __future__ import annotations

from flask import Blueprint, jsonify, request

from .selfdev_checkpoints import SelfDevelopmentCheckpoints
from .errors import ProtocolError
from .selfdev_execution import SelfDevelopmentExecution


def create_selfdev_control_blueprint(
    selfdev: SelfDevelopmentExecution,
    checkpoints: SelfDevelopmentCheckpoints,
) -> Blueprint:
    blueprint = Blueprint("bob_selfdev_control", __name__)

    @blueprint.get("/bob/self-development/checkpoints")
    def checkpoint_status():
        return jsonify({"success": True, **checkpoints.snapshot()})

    @blueprint.post(
        "/bob/self-development/items/<item_id>/checkpoints"
    )
    def checkpoint_create(item_id):
        data = request.get_json(silent=True) or {}
        verification = data.get("verification") or {}
        if not isinstance(verification, dict):
            raise ProtocolError("checkpoint verification must be an object")
        checkpoint = checkpoints.create(
            str(item_id),
            label=None if data.get("label") in (None, "") else str(data["label"]),
            verification=dict(verification),
        )
        return jsonify({"success": True, "checkpoint": checkpoint})

    @blueprint.post(
        "/bob/self-development/items/<item_id>/checkpoints/<checkpoint_id>/revert"
    )
    def checkpoint_revert(item_id, checkpoint_id):
        result = checkpoints.revert(str(item_id), str(checkpoint_id))
        return jsonify({"success": True, **result})
    @blueprint.post("/bob/self-development/items/<item_id>/discard")
    def selfdev_discard(item_id):
        data = request.get_json(silent=True) or {}
        result = checkpoints.discard(
            str(item_id),
            reason=str(data.get("reason") or ""),
        )
        return jsonify({"success": True, **result})

    @blueprint.post(
        "/bob/self-development/items/<item_id>/resume-preempted"
    )
    def selfdev_resume_preempted(item_id):
        result = selfdev.resume_preempted(str(item_id))
        return jsonify({"success": True, **result})

    return blueprint
