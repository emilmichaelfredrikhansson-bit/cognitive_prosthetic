from __future__ import annotations

from flask import Blueprint, jsonify, request

from .work_campaigns import WorkCampaignManager


def create_work_campaign_blueprint(
    campaigns: WorkCampaignManager,
) -> Blueprint:
    blueprint = Blueprint("bob_work_campaigns", __name__)

    @blueprint.get("/bob/campaigns")
    def campaign_status():
        return jsonify({"success": True, **campaigns.snapshot()})

    @blueprint.post("/bob/campaigns")
    def campaign_create():
        data = request.get_json(silent=True) or {}
        campaign = campaigns.create(
            goal=str(data.get("goal") or ""),
            workspace_codes=[
                str(value) for value in (data.get("workspaces") or [])
            ],
            duration_seconds=data.get("duration_seconds"),
        )
        return jsonify({"success": True, "campaign": campaign})

    @blueprint.post("/bob/campaigns/<campaign_id>/start")
    def campaign_start(campaign_id):
        campaign = campaigns.start(str(campaign_id))
        return jsonify({"success": True, "campaign": campaign})

    @blueprint.post("/bob/campaigns/<campaign_id>/runs")
    def campaign_create_run(campaign_id):
        data = request.get_json(silent=True) or {}
        result = campaigns.create_run(
            str(campaign_id),
            workspace_code=str(data.get("workspace") or ""),
            goal=str(data.get("goal") or ""),
            base_ref=str(data.get("base_ref") or ""),
            leases=[str(value) for value in (data.get("leases") or [])],
            depends_on=[
                str(value) for value in (data.get("depends_on") or [])
            ],
        )
        return jsonify({"success": True, **result})

    @blueprint.post("/bob/campaigns/<campaign_id>/reconcile")
    def campaign_reconcile(campaign_id):
        campaign = campaigns.reconcile_runs(str(campaign_id))
        runs = campaigns.run_states(str(campaign_id))
        return jsonify({
            "success": True,
            "campaign": campaign,
            "runs": runs,
        })

    @blueprint.post("/bob/campaigns/<campaign_id>/complete")
    def campaign_complete(campaign_id):
        result = campaigns.complete(str(campaign_id))
        return jsonify({"success": True, **result})

    @blueprint.post("/bob/campaigns/<campaign_id>/cancel")
    def campaign_cancel(campaign_id):
        data = request.get_json(silent=True) or {}
        result = campaigns.cancel(
            str(campaign_id),
            reason=str(data.get("reason") or ""),
        )
        return jsonify({"success": True, **result})

    return blueprint
