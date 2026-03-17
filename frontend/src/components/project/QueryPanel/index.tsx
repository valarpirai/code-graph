import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { runSparql, runNLSparql } from "../../../api/client";
import type { SparqlResult } from "../../../api/types";

const NS = "http://codegraph.dev/ontology#";

const EXAMPLE_QUERIES = [
  {
    label: "All functions",
    query: `PREFIX cg: <${NS}>
SELECT ?name ?visibility ?line WHERE {
  ?fn a cg:Function ;
      cg:name ?name ;
      cg:visibility ?visibility ;
      cg:line ?line .
} ORDER BY ?name LIMIT 50`,
  },
  {
    label: "Call graph",
    query: `PREFIX cg: <${NS}>
SELECT ?callerName ?calleeName WHERE {
  ?caller cg:calls ?callee ;
          cg:name ?callerName .
  ?callee cg:name ?calleeName .
} LIMIT 50`,
  },
  {
    label: "Classes per package",
    query: `PREFIX cg: <${NS}>
SELECT ?package ?className WHERE {
  ?pkg a cg:Module ;
       cg:name ?package ;
       cg:containsClass ?cls .
  ?cls cg:name ?className .
} ORDER BY ?package LIMIT 50`,
  },
];

interface Props {
  projectId: string;
}

function ResultsTable({ variables, rows }: { variables: string[]; rows: SparqlResult[] }) {
  if (rows.length === 0) return null;
  return (
    <div className="card flex-1 overflow-auto">
      <table className="w-full text-xs text-left">
        <thead className="border-b border-surface-border sticky top-0 bg-surface-elevated">
          <tr>
            {variables.map((v) => (
              <th key={v} className="px-4 py-2 text-gray-400 font-semibold uppercase tracking-widest">
                {v}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className="border-b border-surface-border/40 hover:bg-surface-elevated transition-colors">
              {variables.map((v) => (
                <td key={v} className="px-4 py-2 text-gray-300 font-mono break-all">
                  {row[v]?.value ?? ""}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function QueryPanel({ projectId }: Props) {
  const [query, setQuery] = useState(EXAMPLE_QUERIES[0].query);
  const [nlQuestion, setNlQuestion] = useState("");

  const sparqlMutation = useMutation({
    mutationFn: () => runSparql(projectId, query),
  });

  const nlMutation = useMutation({
    mutationFn: () => runNLSparql(projectId, nlQuestion),
    onSuccess: (data) => {
      // Populate the SPARQL editor with the generated query so user can inspect/edit
      if (data.query) setQuery(data.query);
    },
  });

  const sparqlVariables = sparqlMutation.data?.variables ?? [];
  const sparqlRows = sparqlMutation.data?.results.bindings ?? [];

  const nlVariables = nlMutation.data?.variables ?? [];
  const nlRows = nlMutation.data?.results.bindings ?? [];

  return (
    <div className="flex-1 flex flex-col overflow-hidden p-4 gap-4">
      {/* Natural Language input */}
      <div className="card p-4 flex flex-col gap-2">
        <span className="text-xs text-gray-500 uppercase tracking-widest">
          Ask in Natural Language
        </span>
        <div className="flex gap-2">
          <input
            type="text"
            value={nlQuestion}
            onChange={(e) => setNlQuestion(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && nlQuestion.trim() && nlMutation.mutate()}
            placeholder="e.g. Which functions call the render method?"
            className="flex-1 bg-surface border border-surface-border rounded px-3 py-2
                       text-sm text-gray-200 focus:outline-none focus:border-accent-blue transition-colors"
          />
          <button
            onClick={() => nlMutation.mutate()}
            disabled={nlMutation.isPending || !nlQuestion.trim()}
            className="btn-primary"
          >
            {nlMutation.isPending ? "Thinking…" : "Ask"}
          </button>
        </div>
        {nlMutation.isError && (
          <p className="text-accent-red text-xs">{(nlMutation.error as Error).message}</p>
        )}
        {nlMutation.data?.error && (
          <p className="text-accent-red text-xs">SPARQL error: {nlMutation.data.error}</p>
        )}
        {nlMutation.data && (
          <p className="text-xs text-gray-500">
            Generated SPARQL loaded into editor below.
          </p>
        )}
      </div>

      {/* SPARQL editor */}
      <div className="card flex flex-col gap-2 p-4">
        <div className="flex items-center justify-between">
          <span className="text-xs text-gray-500 uppercase tracking-widest">
            SPARQL Query
          </span>
          <div className="flex gap-2">
            {EXAMPLE_QUERIES.map((eq) => (
              <button
                key={eq.label}
                onClick={() => setQuery(eq.query)}
                className="text-xs text-gray-500 hover:text-accent-blue transition-colors"
              >
                {eq.label}
              </button>
            ))}
          </div>
        </div>
        <textarea
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          rows={8}
          spellCheck={false}
          className="w-full bg-surface border border-surface-border rounded p-3
                     text-sm text-gray-200 font-mono resize-none
                     focus:outline-none focus:border-accent-blue transition-colors"
        />
        <div className="flex justify-end">
          <button
            onClick={() => sparqlMutation.mutate()}
            disabled={sparqlMutation.isPending || !query.trim()}
            className="btn-primary"
          >
            {sparqlMutation.isPending ? "Running…" : "Run Query"}
          </button>
        </div>
        {sparqlMutation.isError && (
          <p className="text-accent-red text-xs">{(sparqlMutation.error as Error).message}</p>
        )}
      </div>

      {/* NL results */}
      {nlMutation.isSuccess && nlRows.length > 0 && (
        <>
          <p className="text-xs text-gray-500 -mb-2">Natural language results:</p>
          <ResultsTable variables={nlVariables} rows={nlRows} />
        </>
      )}

      {/* SPARQL results */}
      <ResultsTable variables={sparqlVariables} rows={sparqlRows} />

      {sparqlMutation.isSuccess && sparqlRows.length === 0 && (
        <p className="text-gray-600 text-sm text-center py-8">
          Query returned no results.
        </p>
      )}
    </div>
  );
}
