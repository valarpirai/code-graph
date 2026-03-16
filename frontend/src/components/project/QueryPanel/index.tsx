import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { runSparql } from "../../../api/client";
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

export default function QueryPanel({ projectId }: Props) {
  const [query, setQuery] = useState(EXAMPLE_QUERIES[0].query);

  const mutation = useMutation({
    mutationFn: () => runSparql(projectId, query),
  });

  const variables = mutation.data?.variables ?? [];
  const rows = mutation.data?.results.bindings ?? [];

  return (
    <div className="flex-1 flex flex-col overflow-hidden p-4 gap-4">
      {/* Query input */}
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
            onClick={() => mutation.mutate()}
            disabled={mutation.isPending || !query.trim()}
            className="btn-primary"
          >
            {mutation.isPending ? "Running…" : "Run Query"}
          </button>
        </div>
        {mutation.isError && (
          <p className="text-accent-red text-xs">
            {(mutation.error as Error).message}
          </p>
        )}
      </div>

      {/* Results table */}
      {rows.length > 0 && (
        <div className="card flex-1 overflow-auto">
          <table className="w-full text-xs text-left">
            <thead className="border-b border-surface-border sticky top-0 bg-surface-elevated">
              <tr>
                {variables.map((v) => (
                  <th
                    key={v}
                    className="px-4 py-2 text-gray-400 font-semibold uppercase tracking-widest"
                  >
                    {v}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row: SparqlResult, i: number) => (
                <tr
                  key={i}
                  className="border-b border-surface-border/40 hover:bg-surface-elevated transition-colors"
                >
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
      )}

      {mutation.isSuccess && rows.length === 0 && (
        <p className="text-gray-600 text-sm text-center py-8">
          Query returned no results.
        </p>
      )}
    </div>
  );
}
