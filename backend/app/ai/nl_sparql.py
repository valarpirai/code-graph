"""Natural language → SPARQL query generation using Claude."""
from rdflib import Graph, URIRef, Literal

import anthropic

_MODEL = "claude-sonnet-4-6"

_SYSTEM_PROMPT = """\
You are a SPARQL query generator for a code knowledge graph.
Convert the user's natural language question into a valid SPARQL 1.1 SELECT query.

RDF prefix:
  PREFIX cg: <http://codegraph.dev/ontology#>
  PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

Node types:
  Infrastructure : cg:File, cg:Module, cg:Import, cg:ExternalSymbol
  Type defs      : cg:Class, cg:AbstractClass, cg:DataClass, cg:Interface,
                   cg:Trait, cg:Enum, cg:Struct, cg:Mixin
  Callables      : cg:Function, cg:Method, cg:Constructor
  Storage        : cg:Field, cg:Parameter, cg:LocalVariable, cg:Constant

Object properties:
  cg:calls, cg:imports, cg:inherits, cg:implements, cg:mixes,
  cg:hasField, cg:hasMethod, cg:hasParameter, cg:defines,
  cg:containsFile, cg:containsClass

Datatype properties:
  cg:name, cg:qualifiedName, cg:filePath, cg:language, cg:line,
  cg:visibility, cg:isExported, cg:frameworkRole, cg:entryPointScore,
  cg:dataType, cg:returnType, cg:classKind, cg:value,
  cg:isTest, cg:isAbstract, cg:lineCount, cg:fileSize

Rules:
- rdflib SPARQL has NO subclass inference; always enumerate concrete types with VALUES.
- Return ONLY the SPARQL query — no prose, no markdown fences.
- Add LIMIT 50 unless the user asks for all results.
"""


def _execute(graph: Graph, sparql: str) -> dict:
    result = graph.query(sparql)
    variables = [str(v) for v in result.vars]
    bindings = []
    for row in result:
        binding: dict = {}
        for var in result.vars:
            val = row[var]
            if val is None:
                continue
            if isinstance(val, URIRef):
                binding[str(var)] = {"type": "uri", "value": str(val)}
            else:
                binding[str(var)] = {"type": "literal", "value": str(val)}
        bindings.append(binding)
    return {"variables": variables, "results": {"bindings": bindings}}


def nl_to_sparql(graph: Graph, question: str, api_key: str) -> dict:
    """Convert a natural language question to SPARQL, execute it, return both."""
    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model=_MODEL,
        max_tokens=512,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": question}],
    )

    sparql = message.content[0].text.strip()
    # Strip accidental markdown fences
    if sparql.startswith("```"):
        lines = sparql.splitlines()
        sparql = "\n".join(
            line for line in lines if not line.startswith("```")
        ).strip()

    try:
        query_result = _execute(graph, sparql)
        return {"query": sparql, **query_result}
    except Exception as exc:
        return {
            "query": sparql,
            "error": str(exc),
            "variables": [],
            "results": {"bindings": []},
        }
