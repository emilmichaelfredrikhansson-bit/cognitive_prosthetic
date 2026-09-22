from __future__ import annotations

from typing import Any

from bob.errors import ProtocolError
from bob.workspaces import Workspace
from .http import JsonHttp


class CloudflareAdapter:
    def __init__(self, api_token: str):
        self.http = JsonHttp(
            "https://api.cloudflare.com/client/v4",
            headers={
                "Authorization": f"Bearer {api_token}",
                "Content-Type": "application/json",
            },
        )

    def capabilities(self) -> list[str]:
        return [
            "cloudflare.pages_project",
            "cloudflare.pages_deployments",
            "cloudflare.pages_deployment",
            "cloudflare.pages_retry",
            "cloudflare.pages_rollback",
        ]

    def _cfg(self, workspace: Workspace) -> tuple[str, str]:
        cfg = workspace.providers.get("cloudflare") or {}
        account_id = cfg.get("account_id")
        project_name = cfg.get("project_name") or cfg.get("resource")
        if not account_id or not project_name:
            raise ProtocolError("workspace requires Cloudflare account_id and project_name")
        return str(account_id), str(project_name)

    @staticmethod
    def _unwrap(payload: Any) -> Any:
        if isinstance(payload, dict) and "success" in payload:
            if not payload.get("success"):
                raise ProtocolError(f"Cloudflare API reported failure: {payload.get('errors')}")
            return payload.get("result")
        return payload

    def read(self, workspace: Workspace, tool: str, args: dict[str, Any]) -> Any:
        account_id, project = self._cfg(workspace)
        root = f"/accounts/{account_id}/pages/projects/{project}"
        if tool == "cloudflare.pages_project":
            return self._unwrap(self.http.request("GET", root))
        if tool == "cloudflare.pages_deployments":
            params = {}
            if args.get("env"):
                params["env"] = args["env"]
            return self._unwrap(self.http.request("GET", root + "/deployments", params=params or None))
        if tool == "cloudflare.pages_deployment":
            deployment_id = args.get("deployment_id")
            if not deployment_id:
                raise ProtocolError("cloudflare.pages_deployment requires deployment_id")
            return self._unwrap(self.http.request("GET", root + f"/deployments/{deployment_id}"))
        raise ProtocolError(f"unsupported Cloudflare read tool: {tool}")

    def effect(self, workspace: Workspace, tool: str, args: dict[str, Any]) -> Any:
        account_id, project = self._cfg(workspace)
        deployment_id = args.get("deployment_id")
        if tool in {"cloudflare.pages_retry", "cloudflare.pages_rollback"} and not deployment_id:
            raise ProtocolError(f"{tool} requires deployment_id")
        root = f"/accounts/{account_id}/pages/projects/{project}/deployments/{deployment_id}"
        if tool == "cloudflare.pages_retry":
            return self._unwrap(self.http.request("POST", root + "/retry", json_body={}))
        if tool == "cloudflare.pages_rollback":
            return self._unwrap(self.http.request("POST", root + "/rollback", json_body={}))
        raise ProtocolError(f"unsupported Cloudflare effect tool: {tool}")
