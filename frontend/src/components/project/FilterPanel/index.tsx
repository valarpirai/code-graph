import type { NodeType, EdgeRelation } from "../../../api/types";
import { NODE_COLORS, EDGE_COLORS } from "../GraphView/cytoscapeConfig";

// Grouped node types for display
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

interface Props { filters: FilterState; onChange: (f: FilterState) => void; }

export default function FilterPanel({ filters, onChange }: Props) {
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

  return (
    <div className="card p-4 flex flex-col gap-4 text-xs">
      <Section label="Type Definitions">
        {TYPE_DEF_NODES.map((t) => (
          <CheckRow key={t} label={t} color={NODE_COLORS[t]} checked={filters.visibleNodeTypes.has(t)} onChange={() => toggleNodeType(t)} />
        ))}
      </Section>
      <Section label="Callables">
        {CALLABLE_NODES.map((t) => (
          <CheckRow key={t} label={t} color={NODE_COLORS[t]} checked={filters.visibleNodeTypes.has(t)} onChange={() => toggleNodeType(t)} />
        ))}
      </Section>
      <Section label="Storage">
        {STORAGE_NODES.map((t) => (
          <CheckRow key={t} label={t} color={NODE_COLORS[t]} checked={filters.visibleNodeTypes.has(t)} onChange={() => toggleNodeType(t)} />
        ))}
      </Section>
      <Section label="Other">
        {OTHER_NODES.map((t) => (
          <CheckRow key={t} label={t} color={NODE_COLORS[t]} checked={filters.visibleNodeTypes.has(t)} onChange={() => toggleNodeType(t)} />
        ))}
      </Section>
      <Section label="Edge Relations">
        {ALL_EDGE_RELATIONS.map((r) => (
          <CheckRow key={r} label={r} color={EDGE_COLORS[r]} checked={filters.visibleEdgeRelations.has(r)} onChange={() => toggleEdge(r)} />
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

function Section({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1.5">
      <span className="text-gray-500 uppercase tracking-widest">{label}</span>
      {children}
    </div>
  );
}

function CheckRow({ label, color, checked, onChange }: { label: string; color?: string; checked: boolean; onChange: () => void }) {
  return (
    <label className="flex items-center gap-2 cursor-pointer">
      <input type="checkbox" checked={checked} onChange={onChange} className="accent-accent-blue" />
      {color && <span className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: color }} />}
      <span className="text-gray-300">{label}</span>
    </label>
  );
}
