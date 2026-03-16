// ── Project ──────────────────────────────────────────────────────────────────

export type ProjectStatus =
  | "pending"
  | "cloning"
  | "indexing"
  | "ready"
  | "error";

export interface Project {
  id: string;
  name: string;
  status: ProjectStatus;
  source_url?: string;
  languages: string[];
  created_at: string;
  updated_at: string;
  node_count?: number;
  edge_count?: number;
  error_message?: string;
}

export interface ProjectList {
  projects: Project[];
}

// ── Graph ─────────────────────────────────────────────────────────────────────

export type NodeType =
  | "File"
  | "Class"
  | "Function"
  | "Variable"
  | "ExternalSymbol"
  | "Module";

export type EdgeRelation =
  | "calls"
  | "imports"
  | "inherits"
  | "contains"
  | "defines"
  | "uses";

export interface GraphNodeData {
  id: string;
  label: string;
  node_type: NodeType;
  file_path?: string;
  line?: number;
  col?: number;
  language?: string;
  cluster_id?: string;
  [key: string]: unknown;
}

export interface GraphEdgeData {
  id: string;
  source: string;
  target: string;
  relation: EdgeRelation;
}

export interface GraphResponse {
  nodes: Array<{ data: GraphNodeData }>;
  edges: Array<{ data: GraphEdgeData }>;
}

// ── Clusters ──────────────────────────────────────────────────────────────────

export interface ClusterAssignment {
  node_uri: string;
  cluster_id: string;
  cluster_label?: string;
}

export interface ClustersResponse {
  clusters: ClusterAssignment[];
}

// ── Blast Radius / Execution Flow ─────────────────────────────────────────────

export interface SubgraphResponse {
  nodes: Array<{ data: GraphNodeData }>;
  edges: Array<{ data: GraphEdgeData }>;
}

// ── SPARQL ────────────────────────────────────────────────────────────────────

export interface SparqlResult {
  [variable: string]: { type: string; value: string };
}

export interface SparqlResponse {
  results: {
    bindings: SparqlResult[];
  };
  variables: string[];
}

// ── Wiki ──────────────────────────────────────────────────────────────────────

export interface WikiFile {
  name: string;
  path: string;
}

export interface WikiListResponse {
  files: WikiFile[];
}

export interface WikiContentResponse {
  content: string;
  name: string;
}

// ── WebSocket events ──────────────────────────────────────────────────────────

export type WsEventType =
  | "progress"
  | "status_change"
  | "complete"
  | "error";

export interface WsEvent {
  type: WsEventType;
  message: string;
  progress?: number; // 0–100
  status?: ProjectStatus;
}

// ── Create project ────────────────────────────────────────────────────────────

export interface CreateProjectRequest {
  github_url: string;
}
