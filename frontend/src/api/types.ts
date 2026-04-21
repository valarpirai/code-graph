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
  branch?: string;
  is_stale?: boolean;
  languages: string[];
  last_indexed?: string;
  node_count?: number;
  edge_count?: number;
  error_message?: string;
}

// ── Graph ─────────────────────────────────────────────────────────────────────

export type NodeType =
  // Infrastructure
  | "File"
  | "Module"
  | "ExternalSymbol"
  // TypeDefinition hierarchy
  | "Class"
  | "AbstractClass"
  | "DataClass"
  | "Interface"
  | "Trait"
  | "Enum"
  | "Struct"
  | "Mixin"
  // Callable hierarchy
  | "Function"
  | "Method"
  | "Constructor"
  // StorageNode hierarchy
  | "Field"
  | "Parameter"
  | "LocalVariable"
  | "Constant";

export type EdgeRelation =
  | "calls"
  | "imports"
  | "inherits"
  | "implements"
  | "mixes"
  | "contains"
  | "containsFile"
  | "containsClass"
  | "defines"
  | "uses"
  | "hasMethod"
  | "hasField"
  | "hasParameter";

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
  data_type?: string;
  is_test?: boolean;
  is_abstract?: boolean;
  line_count?: number;
  file_size?: number;
  cluster_id?: string;
  caller_count?: number;
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

// ── Wiki Search ───────────────────────────────────────────────────────────────

export interface WikiSearchResponse {
  answer: string;
  sources: string[];
}

// ── NL SPARQL ─────────────────────────────────────────────────────────────────

export interface NLSparqlResponse {
  query: string;
  variables: string[];
  results: {
    bindings: SparqlResult[];
  };
  error?: string;
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
