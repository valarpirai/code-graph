import { useQuery } from "@tanstack/react-query";
import { getGraph, getClusters, getBlastRadius, getExecutionFlow } from "../api/client";

export const graphKeys = {
  graph: (id: string) => ["graph", id] as const,
  clusters: (id: string) => ["clusters", id] as const,
  blastRadius: (id: string, uri: string) => ["blast-radius", id, uri] as const,
  executionFlow: (id: string, uri: string) => ["execution-flow", id, uri] as const,
};

export function useGraph(projectId: string) {
  return useQuery({
    queryKey: graphKeys.graph(projectId),
    queryFn: () => getGraph(projectId),
    staleTime: 60_000,
  });
}

export function useClusters(projectId: string) {
  return useQuery({
    queryKey: graphKeys.clusters(projectId),
    queryFn: () => getClusters(projectId),
    staleTime: 60_000,
  });
}

export function useBlastRadius(projectId: string, nodeUri: string | null) {
  return useQuery({
    queryKey: graphKeys.blastRadius(projectId, nodeUri ?? ""),
    queryFn: () => getBlastRadius(projectId, nodeUri!),
    enabled: nodeUri != null,
  });
}

export function useExecutionFlow(projectId: string, nodeUri: string | null) {
  return useQuery({
    queryKey: graphKeys.executionFlow(projectId, nodeUri ?? ""),
    queryFn: () => getExecutionFlow(projectId, nodeUri!),
    enabled: nodeUri != null,
  });
}
