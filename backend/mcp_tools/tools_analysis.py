from fastmcp import FastMCP
from mcp_tools.client import get_client, handle_response


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    def get_blast_radius(project_id: str, node_uri: str) -> dict:
        """Find all direct and transitive callers of a node, with severity rating.
        node_uri is the full URI of a function or field (e.g. from get_graph_summary or run_sparql)."""
        with get_client() as c:
            return handle_response(c.get(
                f"/api/v1/projects/{project_id}/blast-radius",
                params={"node_uri": node_uri},
            ))
