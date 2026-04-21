import time
from fastmcp import FastMCP
from mcp_tools.client import get_client, handle_response


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    def list_projects() -> list[dict]:
        """List all projects: id, name, status, languages, source."""
        with get_client() as c:
            return handle_response(c.get("/api/v1/projects"))

    @mcp.tool()
    def get_project(project_id: str) -> dict:
        """Get full metadata for a project by ID."""
        with get_client() as c:
            return handle_response(c.get(f"/api/v1/projects/{project_id}"))

    @mcp.tool()
    def index_github_repo(github_url: str) -> dict:
        """Start indexing a public GitHub repo. Returns immediately with project_id and status.
        Call wait_for_indexing(project_id) to block until done."""
        with get_client() as c:
            return handle_response(c.post("/api/v1/projects", json={"github_url": github_url}))

    @mcp.tool()
    def wait_for_indexing(project_id: str, timeout_seconds: int = 300) -> dict:
        """Poll until indexing completes or fails. Returns final project state plus a progress log."""
        start = time.time()
        progress_log: list[dict] = []
        data: dict = {}

        while time.time() - start < timeout_seconds:
            with get_client() as c:
                data = handle_response(c.get(f"/api/v1/projects/{project_id}"))
            elapsed = round(time.time() - start, 1)
            status = data.get("status")
            progress_log.append({"elapsed_s": elapsed, "status": status})
            if status in ("ready", "error"):
                return {**data, "progress_log": progress_log}
            time.sleep(3)

        return {**data, "timed_out": True, "progress_log": progress_log}

    @mcp.tool()
    def reindex_project(project_id: str) -> dict:
        """Trigger re-indexing of an existing project. Returns immediately; use wait_for_indexing to track."""
        with get_client() as c:
            return handle_response(c.post(f"/api/v1/projects/{project_id}/reindex"))

    @mcp.tool()
    def delete_project(project_id: str) -> dict:
        """Delete a project and all its data (graph, wiki, source)."""
        with get_client() as c:
            resp = c.delete(f"/api/v1/projects/{project_id}")
            if resp.status_code == 204:
                return {"deleted": True, "project_id": project_id}
            return handle_response(resp)
