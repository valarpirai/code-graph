"""
Code Graph MCP server.

Usage:
  uv run python mcp_server.py                              # stdio (default)
  uv run python mcp_server.py --transport http             # Streamable HTTP on :8001
  uv run python mcp_server.py --transport http --port 9000
"""
import argparse
from fastmcp import FastMCP
from mcp_tools import tools_projects, tools_graph, tools_analysis

mcp = FastMCP("Code Graph")

tools_projects.register(mcp)
tools_graph.register(mcp)
tools_analysis.register(mcp)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Code Graph MCP server")
    parser.add_argument("--transport", choices=["stdio", "http"], default="stdio")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8001)
    args = parser.parse_args()

    if args.transport == "http":
        mcp.run(transport="streamable-http", host=args.host, port=args.port)
    else:
        mcp.run()
