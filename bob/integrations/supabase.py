from __future__ import annotations

from typing import Any

from bob.errors import IdentityMismatch, ProtocolError
from bob.workspaces import Workspace
from .http import JsonHttp


class SupabaseAdapter:
    """Thin wrapper around the Supabase Management API."""

    def __init__(self, access_token: str):
        self.http = JsonHttp(
            "https://api.supabase.com",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
        )

    def capabilities(self) -> list[str]:
        return [
            "supabase.project",
            "supabase.functions",
            "supabase.logs",
            "supabase.read_only_query",
            "supabase.query",
        ]

    def _ref(self, workspace: Workspace) -> str:
        cfg = workspace.providers.get("supabase") or {}
        ref = cfg.get("project_id")
        if not ref:
            raise ProtocolError("workspace has no Supabase project_id")
        return str(ref)

    def verify_workspace(self, workspace: Workspace) -> dict[str, Any]:
        ref = self._ref(workspace)
        cfg = workspace.providers.get("supabase") or {}
        expected_org = cfg.get("organization_id")

        project = self.http.request("GET", f"/v1/projects/{ref}")
        actual = str(project.get("id") or project.get("ref") or ref)
        if actual != ref:
            raise IdentityMismatch(f"Supabase project mismatch: expected {ref}, got {actual}")

        organization_id = project.get("organization_id")
        if expected_org and organization_id is None:
            # The single-project response is not guaranteed to expose org identity
            # in every Management API shape. Resolve from the canonical project list.
            projects = self.http.request("GET", "/v1/projects")
            match = next(
                (
                    item for item in projects
                    if isinstance(item, dict)
                    and str(item.get("ref") or item.get("id")) == ref
                ),
                None,
            )
            if match is None:
                raise IdentityMismatch(f"Supabase project not present in accessible project list: {ref}")
            organization_id = match.get("organization_id")

        if expected_org and str(organization_id) != str(expected_org):
            raise IdentityMismatch(
                f"Supabase organization mismatch: expected {expected_org}, got {organization_id}"
            )

        return {
            "project_id": ref,
            "organization_id": organization_id,
            "name": project.get("name"),
            "region": project.get("region"),
            "status": project.get("status"),
        }

    def read(self, workspace: Workspace, tool: str, args: dict[str, Any]) -> Any:
        ref = self._ref(workspace)
        self.verify_workspace(workspace)
        if tool == "supabase.project":
            return self.verify_workspace(workspace)
        if tool == "supabase.functions":
            return self.http.request("GET", f"/v1/projects/{ref}/functions")
        if tool == "supabase.logs":
            params = {}
            for key in ("sql", "iso_timestamp_start", "iso_timestamp_end"):
                if args.get(key) is not None:
                    params[key] = args[key]
            return self.http.request(
                "GET",
                f"/v1/projects/{ref}/analytics/endpoints/logs",
                params=params or None,
            )
        if tool == "supabase.read_only_query":
            query = args.get("query")
            if not isinstance(query, str) or not query.strip():
                raise ProtocolError("supabase.read_only_query requires query")
            return self.http.request(
                "POST",
                f"/v1/projects/{ref}/database/query/read-only",
                json_body={"query": query, "parameters": args.get("parameters") or []},
            )
        raise ProtocolError(f"unsupported Supabase read tool: {tool}")

    def effect(self, workspace: Workspace, tool: str, args: dict[str, Any]) -> Any:
        ref = self._ref(workspace)
        self.verify_workspace(workspace)
        if tool == "supabase.query":
            query = args.get("query")
            if not isinstance(query, str) or not query.strip():
                raise ProtocolError("supabase.query requires query")
            return self.http.request(
                "POST",
                f"/v1/projects/{ref}/database/query",
                json_body={
                    "query": query,
                    "parameters": args.get("parameters") or [],
                    "read_only": bool(args.get("read_only", False)),
                },
            )
        raise ProtocolError(f"unsupported Supabase effect tool: {tool}")
