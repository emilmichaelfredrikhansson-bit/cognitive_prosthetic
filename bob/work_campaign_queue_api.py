from __future__ import annotations

from flask import Blueprint, jsonify, request

from .errors import ProtocolError
from .work_campaign_queue import WorkCampaignQueue


def create_work_campaign_queue_blueprint(
    queue: WorkCampaignQueue,
) -> Blueprint:
    blueprint = Blueprint("bob_work_campaign_queue", __name__)

    @blueprint.get("/bob/campaigns/<campaign_id>/work")
    def work_status(campaign_id):
        return jsonify({
            "success": True,
            **queue.snapshot(str(campaign_id)),
        })

    @blueprint.post("/bob/campaigns/<campaign_id>/work")
    def work_enqueue(campaign_id):
        data = request.get_json(silent=True) or {}
        item = queue.enqueue(
            str(campaign_id),
            workspace=str(data.get("workspace") or ""),
            goal=str(data.get("goal") or ""),
            base_ref=str(data.get("base_ref") or ""),
            leases=[str(value) for value in (data.get("leases") or [])],
            depends_on=[
                str(value) for value in (data.get("depends_on") or [])
            ],
        )
        return jsonify({"success": True, "item": item})

    @blueprint.post("/bob/campaigns/<campaign_id>/tick")
    def work_tick(campaign_id):
        data = request.get_json(silent=True) or {}
        result = queue.tick(
            str(campaign_id),
            max_admissions=data.get("max_admissions", 3),
        )
        return jsonify({"success": True, **result})

    @blueprint.get("/bob/campaigns/<campaign_id>/digest")
    def work_digest(campaign_id):
        return jsonify({
            "success": True,
            **queue.digest(str(campaign_id)),
        })

    @blueprint.post("/bob/campaign-work/<item_id>/finish")
    def work_finish(item_id):
        data = request.get_json(silent=True) or {}
        success = data.get("success")
        if not isinstance(success, bool):
            raise ProtocolError("campaign work finish requires boolean success")
        verification = data.get("verification")
        if verification is not None and not isinstance(verification, dict):
            raise ProtocolError("campaign work verification must be an object")
        item = queue.finish(
            str(item_id),
            success=success,
            verification=verification,
            reason=None if data.get("reason") in (None, "") else str(data["reason"]),
        )
        return jsonify({"success": True, "item": item})

    @blueprint.post("/bob/campaign-work/<item_id>/cancel")
    def work_cancel(item_id):
        data = request.get_json(silent=True) or {}
        item = queue.cancel_unadmitted(
            str(item_id),
            reason=str(data.get("reason") or ""),
        )
        return jsonify({"success": True, "item": item})

    return blueprint
