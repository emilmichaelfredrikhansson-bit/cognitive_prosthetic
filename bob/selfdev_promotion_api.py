from __future__ import annotations

from flask import Blueprint, jsonify, request

from .errors import ProtocolError
from .selfdev_promotion import SelfDevelopmentPromotionGate


def create_selfdev_promotion_blueprint(
    gate: SelfDevelopmentPromotionGate,
) -> Blueprint:
    blueprint = Blueprint("bob_selfdev_promotion", __name__)

    @blueprint.get("/bob/self-development/promotions")
    def promotion_status():
        return jsonify({"success": True, **gate.snapshot()})

    @blueprint.post(
        "/bob/self-development/items/<item_id>/promotion-proposals"
    )
    def promotion_create(item_id):
        proposal = gate.create(str(item_id))
        return jsonify({"success": True, "proposal": proposal})

    @blueprint.post(
        "/bob/self-development/promotions/<proposal_id>/revalidate"
    )
    def promotion_revalidate(proposal_id):
        proposal = gate.revalidate(str(proposal_id))
        return jsonify({"success": True, "proposal": proposal})

    @blueprint.post(
        "/bob/self-development/promotions/<proposal_id>/approve"
    )
    def promotion_approve(proposal_id):
        data = request.get_json(silent=True) or {}
        candidate = str(data.get("candidate_head_sha") or "").strip()
        canonical = str(data.get("canonical_sha") or "").strip()
        if not candidate or not canonical:
            raise ProtocolError(
                "promotion approval requires candidate_head_sha and canonical_sha"
            )
        proposal = gate.approve(
            str(proposal_id),
            expected_candidate_head_sha=candidate,
            expected_canonical_sha=canonical,
        )
        return jsonify({"success": True, "proposal": proposal})

    @blueprint.post(
        "/bob/self-development/promotions/<proposal_id>/reject"
    )
    def promotion_reject(proposal_id):
        data = request.get_json(silent=True) or {}
        proposal = gate.reject(
            str(proposal_id),
            reason=str(data.get("reason") or ""),
        )
        return jsonify({"success": True, "proposal": proposal})

    return blueprint
