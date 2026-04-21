from fastmcp import FastMCP
from mcp_tools.client import get_client, handle_response

_SPARQL_PREFIXES = "PREFIX cg: <http://codegraph.dev/ontology#>\nPREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>\n"


def _sparql(c, project_id: str, query: str) -> dict:
    return handle_response(c.post(f"/api/v1/projects/{project_id}/sparql", json={"query": query}))


def _bindings(result: dict) -> list[dict]:
    return result.get("results", {}).get("bindings", [])


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

    @mcp.tool()
    def get_callers(project_id: str, node_uri: str) -> list[dict]:
        """Return direct callers of a function or method.
        Each result has: caller_uri, caller_name, caller_type, qualified_name.
        Use get_blast_radius for the full transitive call chain."""
        query = _SPARQL_PREFIXES + f"""
SELECT ?caller ?name ?type ?qname WHERE {{
  ?caller cg:calls <{node_uri}> .
  ?caller cg:name ?name .
  ?caller rdf:type ?type .
  OPTIONAL {{ ?caller cg:qualifiedName ?qname }}
}} LIMIT 200
"""
        with get_client() as c:
            rows = _bindings(_sparql(c, project_id, query))
        return [
            {
                "caller_uri": r["caller"]["value"],
                "caller_name": r["name"]["value"],
                "caller_type": r["type"]["value"].split("#")[-1],
                "qualified_name": r.get("qname", {}).get("value", ""),
            }
            for r in rows
        ]

    @mcp.tool()
    def get_callees(project_id: str, node_uri: str) -> list[dict]:
        """Return all functions/methods that a given function directly calls.
        Each result has: callee_uri, callee_name, callee_type, qualified_name."""
        query = _SPARQL_PREFIXES + f"""
SELECT ?callee ?name ?type ?qname WHERE {{
  <{node_uri}> cg:calls ?callee .
  ?callee cg:name ?name .
  ?callee rdf:type ?type .
  OPTIONAL {{ ?callee cg:qualifiedName ?qname }}
}} LIMIT 200
"""
        with get_client() as c:
            rows = _bindings(_sparql(c, project_id, query))
        return [
            {
                "callee_uri": r["callee"]["value"],
                "callee_name": r["name"]["value"],
                "callee_type": r["type"]["value"].split("#")[-1],
                "qualified_name": r.get("qname", {}).get("value", ""),
            }
            for r in rows
        ]

    @mcp.tool()
    def get_class_hierarchy(project_id: str, class_uri: str) -> dict:
        """Return the inheritance ancestry and descendants of a class.
        ancestors: classes this class inherits from (transitively via SPARQL* if supported, else 1-hop).
        descendants: classes that inherit from this class.
        implements: interfaces this class implements."""
        with get_client() as c:
            parents_q = _SPARQL_PREFIXES + f"""
SELECT ?parent ?name WHERE {{
  <{class_uri}> cg:inherits ?parent .
  ?parent cg:name ?name .
}}
"""
            children_q = _SPARQL_PREFIXES + f"""
SELECT ?child ?name WHERE {{
  ?child cg:inherits <{class_uri}> .
  ?child cg:name ?name .
}}
"""
            ifaces_q = _SPARQL_PREFIXES + f"""
SELECT ?iface ?name WHERE {{
  <{class_uri}> cg:implements ?iface .
  ?iface cg:name ?name .
}}
"""
            parents = _bindings(_sparql(c, project_id, parents_q))
            children = _bindings(_sparql(c, project_id, children_q))
            ifaces = _bindings(_sparql(c, project_id, ifaces_q))

        return {
            "class_uri": class_uri,
            "parents": [{"uri": r["parent"]["value"], "name": r["name"]["value"]} for r in parents],
            "children": [{"uri": r["child"]["value"], "name": r["name"]["value"]} for r in children],
            "implements": [{"uri": r["iface"]["value"], "name": r["name"]["value"]} for r in ifaces],
        }

    @mcp.tool()
    def find_nodes(
        project_id: str,
        name_contains: str = "",
        node_type: str = "",
        language: str = "",
        limit: int = 50,
    ) -> list[dict]:
        """Search for nodes by name substring, type, or language.
        node_type: one of Function, Method, Constructor, Class, Interface, Field, File, Module, ExternalSymbol, etc.
        language: e.g. java, python, typescript.
        Returns uri, name, type, qualified_name, language."""
        filters = []
        if name_contains:
            filters.append(f'FILTER(contains(lcase(str(?name)), "{name_contains.lower()}"))')
        if node_type:
            filters.append(f"?node rdf:type cg:{node_type} .")
        else:
            filters.append("?node rdf:type ?type .")
        if language:
            filters.append(f'?node cg:language "{language}" .')

        type_sel = f"cg:{node_type}" if node_type else "?type"
        query = _SPARQL_PREFIXES + f"""
SELECT ?node ?name {"?type" if not node_type else ""} ?qname ?lang WHERE {{
  {chr(10).join(filters)}
  ?node cg:name ?name .
  OPTIONAL {{ ?node cg:qualifiedName ?qname }}
  OPTIONAL {{ ?node cg:language ?lang }}
}} LIMIT {limit}
"""
        with get_client() as c:
            rows = _bindings(_sparql(c, project_id, query))
        return [
            {
                "uri": r["node"]["value"],
                "name": r["name"]["value"],
                "type": (r.get("type", {}).get("value", type_sel)).split("#")[-1],
                "qualified_name": r.get("qname", {}).get("value", ""),
                "language": r.get("lang", {}).get("value", ""),
            }
            for r in rows
        ]
