from __future__ import annotations

import os
from typing import Any

from bob.errors import IdentityMismatch, ProtocolError
from bob.workspaces import Workspace
from .http import JsonHttp


class CloudflareAdapter:
    """Thin Cloudflare API adapter for Pages and Workers.

    A workspace may bind a concrete account_id, or intentionally omit it and
    require CLOUDFLARE_ACCOUNT_ID at runtime. For SL-like workspaces the latter
    is verified against an immutable R2 bucket identity anchor before Worker
    state is trusted.
    """

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
            "cloudflare.identity",
            "cloudflare.r2_buckets",
            "cloudflare.worker",
            "cloudflare.worker_versions",
            "cloudflare.worker_deployments",
            "cloudflare.worker_deployment",
            "cloudflare.worker_deploy_version",
            "cloudflare.pages_project",
            "cloudflare.pages_deployments",
            "cloudflare.pages_deployment",
            "cloudflare.pages_retry",
            "cloudflare.pages_rollback",
        ]

    @staticmethod
    def _unwrap(payload: Any) -> Any:
        if isinstance(payload, dict) and "success" in payload:
            if not payload.get("success"):
                raise ProtocolError(f"Cloudflare API reported failure: {payload.get('errors')}")
            return payload.get("result")
        return payload

    def _provider(self, workspace: Workspace) -> dict[str, Any]:
        cfg = workspace.providers.get("cloudflare") or {}
        if not cfg:
            raise ProtocolError("workspace has no Cloudflare provider binding")
        return cfg

    def _account_id(self, workspace: Workspace) -> str:
        cfg = self._provider(workspace)
        account_id = cfg.get("account_id") or os.environ.get(
            str(cfg.get("account_id_env") or "CLOUDFLARE_ACCOUNT_ID")
        )
        if not account_id:
            raise ProtocolError(
                "Cloudflare account id is not bound; configure account_id or "
                "runtime CLOUDFLARE_ACCOUNT_ID"
            )
        return str(account_id)

    def verify_workspace(self, workspace: Workspace) -> dict[str, Any]:
        cfg = self._provider(workspace)
        account_id = self._account_id(workspace)
        r2_anchor = cfg.get("identity_anchor_r2_bucket")
        worker_script = cfg.get("worker_script")
        pages_project = cfg.get("project_name") or cfg.get("resource")

        anchor_receipt = None
        if r2_anchor:
            payload = self._unwrap(
                self.http.request(
                    "GET",
                    f"/accounts/{account_id}/r2/buckets",
                    params={"name": str(r2_anchor), "per_page": 100},
                )
            )
            # Current API shape is {"buckets": [...]}; tolerate a bare list.
            buckets = payload.get("buckets", []) if isinstance(payload, dict) else payload or []
            names = {str(item.get("name")) for item in buckets if isinstance(item, dict)}
            if str(r2_anchor) not in names:
                raise IdentityMismatch(
                    f"Cloudflare R2 identity anchor not found in account {account_id}: {r2_anchor}"
                )
            anchor_receipt = {
                "kind": "r2_bucket",
                "bucket": str(r2_anchor),
                "verified": True,
            }
        elif worker_script:
            scripts = self._unwrap(
                self.http.request("GET", f"/accounts/{account_id}/workers/scripts")
            )
            records = scripts if isinstance(scripts, list) else []
            match = next(
                (
                    item for item in records
                    if isinstance(item, dict) and str(item.get("id")) == str(worker_script)
                ),
                None,
            )
            if match is None:
                raise IdentityMismatch(
                    f"Cloudflare Worker identity anchor not found in account {account_id}: "
                    f"{worker_script}"
                )
            anchor_receipt = {
                "kind": "worker",
                "worker_script": str(worker_script),
                "verified": True,
            }
        elif pages_project:
            project = self._unwrap(
                self.http.request(
                    "GET",
                    f"/accounts/{account_id}/pages/projects/{pages_project}",
                )
            )
            actual_name = project.get("name") if isinstance(project, dict) else None
            if str(actual_name) != str(pages_project):
                raise IdentityMismatch(
                    f"Cloudflare Pages identity anchor mismatch: expected {pages_project}, "
                    f"got {actual_name}"
                )
            anchor_receipt = {
                "kind": "pages_project",
                "project_name": str(pages_project),
                "verified": True,
            }
        else:
            raise ProtocolError(
                "Cloudflare binding has no remotely verifiable identity anchor; "
                "configure identity_anchor_r2_bucket, worker_script or Pages project"
            )

        return {
            "account_id": account_id,
            "identity_anchor": anchor_receipt,
            "worker_script": worker_script,
            "pages_project": pages_project,
        }

    def _worker(self, workspace: Workspace, args: dict[str, Any]) -> tuple[str, str]:
        cfg = self._provider(workspace)
        account_id = self._account_id(workspace)
        script = args.get("script_name") or cfg.get("worker_script")
        if not script:
            raise ProtocolError("Cloudflare Worker tool requires script_name or workspace worker_script")
        return account_id, str(script)

    def _pages(self, workspace: Workspace) -> tuple[str, str]:
        cfg = self._provider(workspace)
        account_id = self._account_id(workspace)
        project = cfg.get("project_name") or cfg.get("resource")
        if not project:
            raise ProtocolError("workspace has no Cloudflare Pages project binding")
        return account_id, str(project)

    def read(self, workspace: Workspace, tool: str, args: dict[str, Any]) -> Any:
        identity = self.verify_workspace(workspace)

        if tool == "cloudflare.identity":
            return identity

        if tool == "cloudflare.r2_buckets":
            account_id = identity["account_id"]
            params = {}
            for key in ("name", "name_contains", "cursor", "direction"):
                if args.get(key) is not None:
                    params[key] = args[key]
            return self._unwrap(
                self.http.request(
                    "GET",
                    f"/accounts/{account_id}/r2/buckets",
                    params=params or None,
                )
            )

        if tool.startswith("cloudflare.worker"):
            account_id, script = self._worker(workspace, args)
            root = f"/accounts/{account_id}/workers/scripts/{script}"
            if tool == "cloudflare.worker":
                scripts = self._unwrap(
                    self.http.request("GET", f"/accounts/{account_id}/workers/scripts")
                )
                records = scripts if isinstance(scripts, list) else []
                match = next(
                    (item for item in records if isinstance(item, dict) and item.get("id") == script),
                    None,
                )
                if match is None:
                    raise IdentityMismatch(f"Cloudflare Worker not found: {script}")
                return {"identity": identity, "worker": match}
            if tool == "cloudflare.worker_versions":
                return self._unwrap(self.http.request("GET", root + "/versions"))
            if tool == "cloudflare.worker_deployments":
                return self._unwrap(self.http.request("GET", root + "/deployments"))
            if tool == "cloudflare.worker_deployment":
                deployment_id = args.get("deployment_id")
                if not deployment_id:
                    raise ProtocolError("cloudflare.worker_deployment requires deployment_id")
                return self._unwrap(
                    self.http.request("GET", root + f"/deployments/{deployment_id}")
                )

        if tool.startswith("cloudflare.pages"):
            account_id, project = self._pages(workspace)
            root = f"/accounts/{account_id}/pages/projects/{project}"
            if tool == "cloudflare.pages_project":
                return self._unwrap(self.http.request("GET", root))
            if tool == "cloudflare.pages_deployments":
                params = {}
                if args.get("env"):
                    params["env"] = args["env"]
                return self._unwrap(
                    self.http.request("GET", root + "/deployments", params=params or None)
                )
            if tool == "cloudflare.pages_deployment":
                deployment_id = args.get("deployment_id")
                if not deployment_id:
                    raise ProtocolError("cloudflare.pages_deployment requires deployment_id")
                return self._unwrap(
                    self.http.request("GET", root + f"/deployments/{deployment_id}")
                )

        raise ProtocolError(f"unsupported Cloudflare read tool: {tool}")

    def effect(self, workspace: Workspace, tool: str, args: dict[str, Any]) -> Any:
        identity = self.verify_workspace(workspace)

        if tool == "cloudflare.worker_deploy_version":
            account_id, script = self._worker(workspace, args)
            version_id = args.get("version_id")
            if not version_id:
                raise ProtocolError("cloudflare.worker_deploy_version requires version_id")
            root = f"/accounts/{account_id}/workers/scripts/{script}"
            created = self._unwrap(
                self.http.request(
                    "POST",
                    root + "/deployments",
                    json_body={
                        "strategy": "percentage",
                        "versions": [{"version_id": str(version_id), "percentage": 100}],
                        "annotations": {
                            "workers/message": str(
                                args.get("message") or "Deployed through Bob"
                            )
                        },
                    },
                )
            )
            deployment_id = created.get("id") if isinstance(created, dict) else None
            if not deployment_id:
                raise ProtocolError("Cloudflare deployment response contained no id")
            actual = self._unwrap(
                self.http.request("GET", root + f"/deployments/{deployment_id}")
            )
            versions = actual.get("versions", []) if isinstance(actual, dict) else []
            if not any(
                str(item.get("version_id")) == str(version_id)
                and float(item.get("percentage", 0)) == 100.0
                for item in versions
                if isinstance(item, dict)
            ):
                raise IdentityMismatch("Cloudflare deployment read-back mismatch")
            return {
                "identity": identity,
                "deployment": actual,
                "read_back_verified": True,
            }

        if tool in {"cloudflare.pages_retry", "cloudflare.pages_rollback"}:
            account_id, project = self._pages(workspace)
            deployment_id = args.get("deployment_id")
            if not deployment_id:
                raise ProtocolError(f"{tool} requires deployment_id")
            root = (
                f"/accounts/{account_id}/pages/projects/{project}/deployments/"
                f"{deployment_id}"
            )
            suffix = "/retry" if tool == "cloudflare.pages_retry" else "/rollback"
            result = self._unwrap(self.http.request("POST", root + suffix, json_body={}))
            return {"identity": identity, "result": result}

        raise ProtocolError(f"unsupported Cloudflare effect tool: {tool}")
