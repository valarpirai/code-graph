from fastmcp import FastMCP
from mcp_tools.client import get_client, handle_response


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    def get_graph_summary(project_id: str) -> dict:
        """Return node and edge counts grouped by type for a project's graph."""
        with get_client() as c:
            return handle_response(c.get(f"/api/v1/projects/{project_id}/graph/summary"))

    @mcp.tool()
    def run_sparql(project_id: str, query: str) -> dict:
        """Execute a SPARQL SELECT query against the project graph.
        Use the cg: prefix for ontology terms (e.g. cg:calls, cg:Function).
        Results are capped at 500 rows."""
        with get_client() as c:
            return handle_response(c.post(f"/api/v1/projects/{project_id}/sparql", json={"query": query}))

    @mcp.tool()
    def natural_language_query(project_id: str, question: str) -> dict:
        """Convert a plain-English question into SPARQL and execute it.
        Returns both the generated query and the results.
        Requires ANTHROPIC_API_KEY configured on the backend."""
        with get_client() as c:
            return handle_response(c.post(
                f"/api/v1/projects/{project_id}/sparql/natural",
                json={"question": question},
            ))
