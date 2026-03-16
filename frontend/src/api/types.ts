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
  source: string;
  languages: string[];
  last_indexed?: string;
  node_count?: number;
  edge_count?: number;
  error_message?: string;
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
  | "containsFile"
  | "containsClass"
  | "defines"
  | "uses"
  | "hasMethod"
  | "hasField";

export interface GraphNodeData {
  id: string;
  label: string;
  node_type: NodeType;
  file_path?: string;
  line?: number;
  language?: string;
  qualified_name?: string;
  visibility?: string;
  is_exported?: boolean;
  entry_point_score?: number;
  framework_role?: string;
  value?: string;
  class_kind?: string;
  is_test?: boolean;
  is_abstract?: boolean;
  var_kind?: string;
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
