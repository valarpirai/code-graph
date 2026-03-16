import type {
  Project,
  ProjectList,
  GraphResponse,
  ClustersResponse,
  SubgraphResponse,
  SparqlResponse,
  WikiListResponse,
  WikiContentResponse,
  CreateProjectRequest,
} from "./types";

const BASE_URL =
  (import.meta as { env?: { VITE_API_BASE_URL?: string } }).env?.VITE_API_BASE_URL ?? "http://localhost:8000";

async function apiFetch<T>(
  path: string,
  init?: RequestInit
): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`API ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

// ── Projects ──────────────────────────────────────────────────────────────────

export const listProjects = () =>
  apiFetch<ProjectList>("/api/v1/projects");

export const getProject = (id: string) =>
  apiFetch<Project>(`/api/v1/projects/${id}`);

export const createProjectFromGitHub = (body: CreateProjectRequest) =>
  apiFetch<Project>("/api/v1/projects", {
    method: "POST",
    body: JSON.stringify(body),
  });

export const uploadProjectZip = (file: File) => {
  const form = new FormData();
  form.append("file", file);
  return fetch(`${BASE_URL}/api/v1/projects/upload`, {
    method: "POST",
    body: form,
  }).then((res) => {
    if (!res.ok) throw new Error(`Upload failed: ${res.statusText}`);
    return res.json() as Promise<Project>;
  });
};

export const deleteProject = (id: string) =>
  apiFetch<void>(`/api/v1/projects/${id}`, { method: "DELETE" });

export const reindexProject = (id: string) =>
  apiFetch<Project>(`/api/v1/projects/${id}/reindex`, { method: "POST" });

// ── Graph ─────────────────────────────────────────────────────────────────────

export const getGraph = (id: string) =>
  apiFetch<GraphResponse>(`/api/v1/projects/${id}/graph`);

export const getClusters = (id: string) =>
  apiFetch<ClustersResponse>(`/api/v1/projects/${id}/clusters`);

export const getBlastRadius = (id: string, nodeUri: string) =>
  apiFetch<SubgraphResponse>(
    `/api/v1/projects/${id}/blast-radius?node_uri=${encodeURIComponent(nodeUri)}`
  );

export const getExecutionFlow = (id: string, nodeUri: string) =>
  apiFetch<SubgraphResponse>(
    `/api/v1/projects/${id}/execution-flow?node_uri=${encodeURIComponent(nodeUri)}`
  );

// ── SPARQL ────────────────────────────────────────────────────────────────────

export const runSparql = (id: string, query: string) =>
  apiFetch<SparqlResponse>(`/api/v1/projects/${id}/sparql`, {
    method: "POST",
    body: JSON.stringify({ query }),
  });

// ── Wiki ──────────────────────────────────────────────────────────────────────

export const listWikiFiles = (id: string) =>
  apiFetch<WikiListResponse>(`/api/v1/projects/${id}/wiki`);

export const getWikiContent = (id: string, fileName: string) =>
  apiFetch<WikiContentResponse>(
    `/api/v1/projects/${id}/wiki/${encodeURIComponent(fileName)}`
  );

export const generateWiki = (id: string) =>
  apiFetch<void>(`/api/v1/projects/${id}/wiki/generate`, { method: "POST" });

// ── WebSocket factory ─────────────────────────────────────────────────────────

export const wsUrl = (projectId: string) => {
  const wsBase = BASE_URL.replace(/^http/, "ws");
  return `${wsBase}/ws/projects/${projectId}/status`;
};
