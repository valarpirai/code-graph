import { useEffect, useRef, useState, useCallback } from "react";
import cytoscape from "cytoscape";
// @ts-expect-error: no types for cose-bilkent
import coseBilkent from "cytoscape-cose-bilkent";
import { useGraph, useClusters } from "../../../hooks/useGraph";
import { baseStylesheet, CLUSTER_PALETTE } from "./cytoscapeConfig";
import NodeSidePanel from "./NodeSidePanel";
import MiniMap from "./MiniMap";
import FilterPanel, { defaultFilterState } from "../FilterPanel/index";
import type { FilterState } from "../FilterPanel/index";
import SearchBar from "../../shared/SearchBar";
import type { GraphNodeData, GraphResponse } from "../../../api/types";
import { getBlastRadius, getExecutionFlow } from "../../../api/client";

cytoscape.use(coseBilkent);

interface Props {
  projectId: string;
  linkedNodeId?: string | null;
  onNodeSelect?: (nodeId: string) => void;
}

export default function GraphView({ projectId, linkedNodeId, onNodeSelect }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<cytoscape.Core | null>(null);
  const [cy, setCy] = useState<cytoscape.Core | null>(null);
  const [selectedNode, setSelectedNode] = useState<GraphNodeData | null>(null);
  const [filters, setFilters] = useState<FilterState>(defaultFilterState());

  const { data: graphData, isLoading, isError } = useGraph(projectId);
  const { data: clusterData } = useClusters(projectId);

  useEffect(() => {
    if (!containerRef.current || !graphData) return;
    const instance = cytoscape({
      container: containerRef.current,
      elements: [...graphData.nodes, ...graphData.edges],
      style: baseStylesheet,
      layout: {
        name: "cose-bilkent",
        animate: false,
        randomize: true,
        idealEdgeLength: 120,
        nodeRepulsion: 12000,
        nodeDimensionsIncludeLabels: true,
        padding: 60,
        gravity: 0.15,
        numIter: 2500,
        tile: true,
      } as cytoscape.LayoutOptions,
      wheelSensitivity: 0.3,
    });
    instance.on("tap", "node", (evt) => {
      const data = evt.target.data() as GraphNodeData;
      setSelectedNode(data);
      onNodeSelect?.(data.id);
    });
    instance.on("tap", (evt) => { if (evt.target === instance) setSelectedNode(null); });
    cyRef.current = instance;
    setCy(instance);
    return () => { instance.destroy(); cyRef.current = null; setCy(null); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [graphData]);

  useEffect(() => {
    if (!cy || !clusterData || !filters.showClusters) {
      cy?.nodes().forEach((n) => n.removeStyle("background-color"));
      return;
    }
    const map = new Map(clusterData.clusters.map((c) => [c.node_uri, c.cluster_id]));
    cy.nodes().forEach((n) => {
      const clusterId = map.get(n.id());
      if (clusterId != null) {
        const idx = parseInt(clusterId, 10) % CLUSTER_PALETTE.length;
        n.style("background-color", CLUSTER_PALETTE[idx]);
      }
    });
  }, [cy, clusterData, filters.showClusters]);

  useEffect(() => {
    if (!cy) return;
    cy.nodes().forEach((n) => { const show = filters.visibleNodeTypes.has(n.data("node_type")); n.style("display", show ? "element" : "none"); });
    cy.edges().forEach((e) => { const show = filters.visibleEdgeRelations.has(e.data("relation")); e.style("display", show ? "element" : "none"); });
  }, [cy, filters]);

  useEffect(() => {
    if (!cy || !linkedNodeId) return;
    cy.nodes().unselect();
    const node = cy.getElementById(linkedNodeId);
    if (node.length) { node.select(); cy.animate({ center: { eles: node }, zoom: 1.5 }, { duration: 300 }); }
  }, [cy, linkedNodeId]);

  const handleBlastRadius = useCallback(async (nodeUri: string) => {
    if (!cy) return;
    cy.elements().removeClass("blast-radius blast-radius-edge faded");
    try {
      const result = await getBlastRadius(projectId, nodeUri);
      const affectedIds = new Set(result.nodes.map((n) => n.data.id));
      const affectedEdgeIds = new Set(result.edges.map((e) => e.data.id));
      cy.nodes().forEach((n) => { if (affectedIds.has(n.id())) n.addClass("blast-radius"); else n.addClass("faded"); });
      cy.edges().forEach((e) => { if (affectedEdgeIds.has(e.id())) e.addClass("blast-radius-edge"); else e.addClass("faded"); });
    } catch (err) { console.error("Blast radius failed", err); }
  }, [cy, projectId]);

  const handleExecutionFlow = useCallback(async (nodeUri: string) => {
    if (!cy) return;
    cy.elements().removeClass("execution-flow faded");
    try {
      const result = await getExecutionFlow(projectId, nodeUri);
      const flowIds = new Set(result.nodes.map((n) => n.data.id));
      cy.nodes().forEach((n) => { if (flowIds.has(n.id())) n.addClass("execution-flow"); else n.addClass("faded"); });
    } catch (err) { console.error("Execution flow failed", err); }
  }, [cy, projectId]);

  const handleSearch = useCallback((term: string) => {
    if (!cy) return;
    if (!term.trim()) { cy.elements().removeClass("faded"); return; }
    const lower = term.toLowerCase();
    cy.nodes().forEach((n) => {
      const match = (n.data("label") as string).toLowerCase().includes(lower);
      if (match) n.removeClass("faded"); else n.addClass("faded");
    });
  }, [cy]);

  if (isLoading) return <div className="flex-1 flex items-center justify-center text-gray-500 text-sm animate-pulse">Loading graph…</div>;
  if (isError) return <div className="flex-1 flex items-center justify-center text-accent-red text-sm">Failed to load graph.</div>;

  return (
    <div className="flex-1 flex overflow-hidden">
      {/* Always-visible filter sidebar */}
      <div className="w-52 shrink-0 border-r border-surface-border overflow-y-auto">
        <FilterPanel filters={filters} onChange={setFilters} />
      </div>

      {/* Graph canvas area */}
      <div className="flex-1 relative flex overflow-hidden">
        <div className="absolute top-3 left-3 z-10 flex gap-2">
          <button onClick={() => cy?.fit(undefined, 30)} className="btn-ghost text-xs px-3 py-1.5">Fit</button>
          <button onClick={() => cy?.elements().removeClass("blast-radius blast-radius-edge execution-flow faded")} className="btn-ghost text-xs px-3 py-1.5">Clear</button>
          <div className="w-48"><SearchBar onSearch={handleSearch} /></div>
        </div>
        <div ref={containerRef} className="flex-1 bg-surface" />
        <MiniMap cy={cy} />
        {selectedNode && (
          <NodeSidePanel node={selectedNode} graphData={graphData ?? { nodes: [], edges: [] }} onClose={() => setSelectedNode(null)} onBlastRadius={handleBlastRadius} onExecutionFlow={handleExecutionFlow} />
        )}
      </div>
    </div>
  );
}
