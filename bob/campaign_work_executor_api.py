from __future__ import annotations

from flask import Blueprint, jsonify, request

from .campaign_work_executor import CampaignWorkExecutor


def create_campaign_work_executor_blueprint(
    executor: CampaignWorkExecutor,
) -> Blueprint:
    blueprint = Blueprint("bob_campaign_work_executor", __name__)

    @blueprint.get("/bob/campaigns/<campaign_id>/executor")
    def executor_digest(campaign_id):
        return jsonify(
            {
                "success": True,
                **executor.digest(str(campaign_id)),
            }
        )

    @blueprint.post("/bob/campaigns/<campaign_id>/executor/cycle")
    def executor_cycle(campaign_id):
        data = request.get_json(silent=True) or {}
        result = executor.cycle(
            str(campaign_id),
            max_admissions=data.get("max_admissions", 3),
            max_items=data.get("max_items", 1),
            max_rounds=data.get("max_rounds", 1),
        )
        return jsonify({"success": True, **result})

    return blueprint
