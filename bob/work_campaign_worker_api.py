from __future__ import annotations

from flask import Blueprint, jsonify, request

from .work_campaign_worker import WorkCampaignWorker


def create_work_campaign_worker_blueprint(
    worker: WorkCampaignWorker,
) -> Blueprint:
    blueprint = Blueprint("bob_work_campaign_worker", __name__)

    @blueprint.get("/bob/campaigns/<campaign_id>/worker")
    def worker_digest(campaign_id):
        return jsonify({
            "success": True,
            **worker.digest(str(campaign_id)),
        })

    @blueprint.post("/bob/campaigns/<campaign_id>/worker/cycle")
    def worker_cycle(campaign_id):
        data = request.get_json(silent=True) or {}
        result = worker.cycle(
            str(campaign_id),
            max_admissions=data.get("max_admissions", 3),
        )
        return jsonify({"success": True, **result})

    @blueprint.post("/bob/campaign-work/<item_id>/checkpoint")
    def worker_checkpoint(item_id):
        data = request.get_json(silent=True) or {}
        verification = data.get("verification")
        if verification is not None and not isinstance(verification, dict):
            from .errors import ProtocolError
            raise ProtocolError("campaign checkpoint verification must be an object")
        checkpoint = worker.checkpoint(
            str(item_id),
            label=None if data.get("label") in (None, "") else str(data["label"]),
            verification=verification,
        )
        return jsonify({"success": True, "checkpoint": checkpoint})

    @blueprint.post("/bob/campaign-work/<item_id>/park")
    def worker_park(item_id):
        data = request.get_json(silent=True) or {}
        result = worker.park(
            str(item_id),
            reason=str(data.get("reason") or ""),
        )
        return jsonify({"success": True, **result})

    @blueprint.post("/bob/campaign-work/<item_id>/resume")
    def worker_resume(item_id):
        result = worker.resume(str(item_id))
        return jsonify({"success": True, **result})

    return blueprint
