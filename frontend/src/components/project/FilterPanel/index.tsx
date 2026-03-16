import { useMemo } from "react";
import type { NodeType, EdgeRelation, GraphResponse } from "../../../api/types";
import { NODE_COLORS, EDGE_COLORS } from "../GraphView/cytoscapeConfig";

// Grouped node types for display order
const TYPE_DEF_NODES: NodeType[] = ["Class", "AbstractClass", "DataClass", "Interface", "Trait", "Enum", "Struct", "Mixin"];
const CALLABLE_NODES: NodeType[] = ["Function", "Method", "Constructor"];
const STORAGE_NODES: NodeType[] = ["Field", "Parameter", "LocalVariable", "Constant"];
const OTHER_NODES: NodeType[] = ["File", "Module", "ExternalSymbol"];

const ALL_EDGE_RELATIONS: EdgeRelation[] = [
  "calls", "imports", "inherits", "implements", "mixes",
  "contains", "containsFile", "containsClass",
  "defines", "uses", "hasMethod", "hasField", "hasParameter",
];

export const ALL_VISIBILITIES = ["public", "protected", "private", "abstract"] as const;

export interface FilterState {
  visibleNodeTypes: Set<NodeType>;
  visibleEdgeRelations: Set<EdgeRelation>;
  showClusters: boolean;
  showTestFiles: boolean;
  hiddenVisibilities: Set<string>;
}

export function defaultFilterState(): FilterState {
  return {
    visibleNodeTypes: new Set<NodeType>([
      "File", "Module",
      "Class", "AbstractClass", "DataClass", "Interface", "Trait", "Enum", "Struct", "Mixin",
      "Function", "Method", "Constructor",
      "Field", "Constant",
      "ExternalSymbol",
    ]),
    visibleEdgeRelations: new Set(ALL_EDGE_RELATIONS.filter((r) => r !== "calls")),
    showClusters: false,
    showTestFiles: true,
    hiddenVisibilities: new Set(),
  };
}

function clearFilterState(): FilterState {
  return {
    visibleNodeTypes: new Set<NodeType>([
      ...TYPE_DEF_NODES, ...CALLABLE_NODES, ...STORAGE_NODES, ...OTHER_NODES,
    ] as NodeType[]),
    visibleEdgeRelations: new Set(ALL_EDGE_RELATIONS),
    showClusters: false,
    showTestFiles: true,
    hiddenVisibilities: new Set(),
  };
}

interface Props {
  filters: FilterState;
  onChange: (f: FilterState) => void;
  graphData?: GraphResponse;
}

export default function FilterPanel({ filters, onChange, graphData }: Props) {
  // Count nodes per type from full graph data
  const nodeTypeCounts = useMemo(() => {
    const counts = new Map<NodeType, number>();
    if (!graphData) return counts;
    for (const { data } of graphData.nodes) {
      const t = data.node_type;
      counts.set(t, (counts.get(t) ?? 0) + 1);
    }
    return counts;
  }, [graphData]);

  // IDs of nodes that pass the current node-type filter (for dynamic edge counts)
  const visibleNodeIds = useMemo(() => {
    if (!graphData) return new Set<string>();
    const ids = new Set<string>();
    for (const { data } of graphData.nodes) {
      if (filters.visibleNodeTypes.has(data.node_type)) ids.add(data.id);
    }
    return ids;
  }, [graphData, filters.visibleNodeTypes]);

  // Count edges per relation where both endpoints are in visibleNodeIds
  const edgeRelationCounts = useMemo(() => {
    const counts = new Map<EdgeRelation, number>();
    if (!graphData) return counts;
    for (const { data } of graphData.edges) {
      if (visibleNodeIds.has(data.source) && visibleNodeIds.has(data.target)) {
        counts.set(data.relation, (counts.get(data.relation) ?? 0) + 1);
      }
    }
    return counts;
  }, [graphData, visibleNodeIds]);

  const toggleNodeType = (t: NodeType) => {
    const next = new Set(filters.visibleNodeTypes);
    next.has(t) ? next.delete(t) : next.add(t);
    onChange({ ...filters, visibleNodeTypes: next });
  };
  const toggleEdge = (r: EdgeRelation) => {
    const next = new Set(filters.visibleEdgeRelations);
    next.has(r) ? next.delete(r) : next.add(r);
    onChange({ ...filters, visibleEdgeRelations: next });
  };
  const toggleVisibility = (v: string) => {
    const next = new Set(filters.hiddenVisibilities);
    next.has(v) ? next.delete(v) : next.add(v);
    onChange({ ...filters, hiddenVisibilities: next });
  };

  const isDefault = useMemo(() => {
    const def = defaultFilterState();
    if (filters.showClusters !== def.showClusters) return false;
    if (filters.showTestFiles !== def.showTestFiles) return false;
    if (filters.visibleNodeTypes.size !== def.visibleNodeTypes.size) return false;
    if (filters.visibleEdgeRelations.size !== def.visibleEdgeRelations.size) return false;
    if (filters.hiddenVisibilities.size !== def.hiddenVisibilities.size) return false;
    for (const t of def.visibleNodeTypes) if (!filters.visibleNodeTypes.has(t)) return false;
    for (const r of def.visibleEdgeRelations) if (!filters.visibleEdgeRelations.has(r)) return false;
    return true;
  }, [filters]);

  return (
    <div className="card p-4 flex flex-col gap-4 text-xs">
      {/* Action buttons */}
      <div className="flex gap-2">
        <button
          onClick={() => onChange(clearFilterState())}
          className="flex-1 btn-ghost text-xs py-1 px-2"
        >
          Show All
        </button>
        <button
          onClick={() => onChange(defaultFilterState())}
          disabled={isDefault}
          className="flex-1 btn-ghost text-xs py-1 px-2 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          Reset
        </button>
      </div>

      <NodeTypeSection
        label="Type Definitions"
        types={TYPE_DEF_NODES}
        counts={nodeTypeCounts}
        visible={filters.visibleNodeTypes}
        onToggle={toggleNodeType}
      />
      <NodeTypeSection
        label="Callables"
        types={CALLABLE_NODES}
        counts={nodeTypeCounts}
        visible={filters.visibleNodeTypes}
        onToggle={toggleNodeType}
      />
      <NodeTypeSection
        label="Storage"
        types={STORAGE_NODES}
        counts={nodeTypeCounts}
        visible={filters.visibleNodeTypes}
        onToggle={toggleNodeType}
      />
      <NodeTypeSection
        label="Other"
        types={OTHER_NODES}
        counts={nodeTypeCounts}
        visible={filters.visibleNodeTypes}
        onToggle={toggleNodeType}
      />

      <Section label="Edge Relations">
        {ALL_EDGE_RELATIONS.filter((r) => !graphData || edgeRelationCounts.has(r)).map((r) => (
          <CheckRow
            key={r}
            label={r}
            color={EDGE_COLORS[r]}
            count={edgeRelationCounts.get(r)}
            checked={filters.visibleEdgeRelations.has(r)}
            onChange={() => toggleEdge(r)}
          />
        ))}
      </Section>

      <Section label="Method Visibility">
        {ALL_VISIBILITIES.map((v) => (
          <CheckRow key={v} label={v} checked={!filters.hiddenVisibilities.has(v)} onChange={() => toggleVisibility(v)} />
        ))}
      </Section>

      <label className="flex items-center gap-2 cursor-pointer">
        <input type="checkbox" checked={filters.showClusters} onChange={() => onChange({ ...filters, showClusters: !filters.showClusters })} className="accent-accent-blue" />
        <span className="text-gray-300">Cluster colour overlay</span>
      </label>
      <label className="flex items-center gap-2 cursor-pointer">
        <input type="checkbox" checked={filters.showTestFiles} onChange={() => onChange({ ...filters, showTestFiles: !filters.showTestFiles })} className="accent-accent-blue" />
        <span className="text-gray-300">Show test files</span>
      </label>
    </div>
  );
}

interface NodeTypeSectionProps {
  label: string;
  types: NodeType[];
  counts: Map<NodeType, number>;
  visible: Set<NodeType>;
  onToggle: (t: NodeType) => void;
}

function NodeTypeSection({ label, types, counts, visible, onToggle }: NodeTypeSectionProps) {
  // Only show types that exist in the graph (when data is loaded)
  const available = counts.size > 0 ? types.filter((t) => counts.has(t)) : types;
  if (available.length === 0) return null;
  return (
    <Section label={label}>
      {available.map((t) => (
        <CheckRow
          key={t}
          label={t}
          color={NODE_COLORS[t]}
          count={counts.get(t)}
          checked={visible.has(t)}
          onChange={() => onToggle(t)}
        />
      ))}
    </Section>
  );
}

function Section({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1.5">
      <span className="text-gray-500 uppercase tracking-widest text-[10px]">{label}</span>
      {children}
    </div>
  );
}

function CheckRow({
  label, color, count, checked, onChange,
}: {
  label: string; color?: string; count?: number; checked: boolean; onChange: () => void;
}) {
  return (
    <label className="flex items-center gap-2 cursor-pointer">
      <input type="checkbox" checked={checked} onChange={onChange} className="accent-accent-blue shrink-0" />
      {color && <span className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: color }} />}
      <span className="text-gray-300 truncate flex-1">{label}</span>
      {count !== undefined && (
        <span className="text-gray-600 tabular-nums ml-auto shrink-0">{count}</span>
      )}
    </label>
  );
}
