#!/usr/bin/env python3
from __future__ import annotations

import os
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from bob.driver import BobRuntime
from bob.errors import BobError

BASE_DIR = Path(__file__).resolve().parent
app = Flask(__name__, static_folder=str(BASE_DIR / "frontend"), static_url_path="")
CORS(app)

runtime = BobRuntime(
    workspace_dir=os.environ.get("BOB_WORKSPACE_DIR", str(BASE_DIR / "workspaces"))
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


@app.post("/bob/approve")
def approve():
    data = request.get_json(force=True) or {}
    result = runtime.approve(str(data["pending_id"]))
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
    port = int(os.environ.get("BOB_PORT", "5002"))
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
