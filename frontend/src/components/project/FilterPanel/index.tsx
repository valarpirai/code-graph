import type { NodeType, EdgeRelation } from "../../../api/types";
import { NODE_COLORS, EDGE_COLORS } from "../GraphView/cytoscapeConfig";

const ALL_NODE_TYPES: NodeType[] = ["File", "Class", "Function", "Variable", "ExternalSymbol", "Module"];
const ALL_EDGE_RELATIONS: EdgeRelation[] = ["calls", "imports", "inherits", "contains", "containsFile", "containsClass", "defines", "uses", "hasMethod"];

export interface FilterState {
  visibleNodeTypes: Set<NodeType>;
  visibleEdgeRelations: Set<EdgeRelation>;
  showClusters: boolean;
  showTestFiles: boolean;
}

export function defaultFilterState(): FilterState {
  return {
    // ExternalSymbol nodes are very numerous and noisy — hidden by default
    visibleNodeTypes: new Set<NodeType>(["File", "Class", "Function", "Variable", "Module"]),
    visibleEdgeRelations: new Set(ALL_EDGE_RELATIONS),
    showClusters: false,
    showTestFiles: true,
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
  return (
    <div className="card p-4 flex flex-col gap-4 text-xs">
      <Section label="Node Types">
        {ALL_NODE_TYPES.map((t) => (
          <CheckRow key={t} label={t} color={NODE_COLORS[t]} checked={filters.visibleNodeTypes.has(t)} onChange={() => toggleNodeType(t)} />
        ))}
      </Section>
      <Section label="Edge Relations">
        {ALL_EDGE_RELATIONS.map((r) => (
          <CheckRow key={r} label={r} color={EDGE_COLORS[r]} checked={filters.visibleEdgeRelations.has(r)} onChange={() => toggleEdge(r)} />
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

function CheckRow({ label, color, checked, onChange }: { label: string; color: string; checked: boolean; onChange: () => void }) {
  return (
    <label className="flex items-center gap-2 cursor-pointer">
      <input type="checkbox" checked={checked} onChange={onChange} className="accent-accent-blue" />
      <span className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: color }} />
      <span className="text-gray-300">{label}</span>
    </label>
  );
}
