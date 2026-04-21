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

const RENDER_STAGES: readonly string[][] = [
  ["File", "Module"],
  ["Class", "AbstractClass", "DataClass", "Interface", "Trait", "Enum", "Struct", "Mixin"],
  ["Function", "Method", "Constructor"],
  ["Field", "Parameter", "LocalVariable", "Constant", "Import", "ExternalSymbol"],
];

function adaptiveNumIter(nodeCount: number): number {
  if (nodeCount < 100) return 1500;
  if (nodeCount < 300) return 800;
  if (nodeCount < 600) return 350;
  return 150;
}

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
  const [renderProgress, setRenderProgress] = useState<{ loaded: number; total: number } | null>(null);
  const [renderComplete, setRenderComplete] = useState(false);

  const { data: graphData, isLoading, isError } = useGraph(projectId);
  const { data: clusterData } = useClusters(projectId);

  useEffect(() => {
    if (!containerRef.current || !graphData) return;

    setRenderComplete(false);
    setRenderProgress({ loaded: 0, total: graphData.nodes.length });

    const instance = cytoscape({
      container: containerRef.current,
      elements: [],
      style: baseStylesheet,
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

    const loadedIds = new Set<string>();

    const runStage = (stageIndex: number) => {
      if (stageIndex >= RENDER_STAGES.length) {
        setRenderProgress(null);
        setRenderComplete(true);
        return;
      }

      const stageTypes = new Set(RENDER_STAGES[stageIndex]);
      const newNodes = graphData.nodes.filter(n => stageTypes.has(n.data.node_type));

      if (newNodes.length === 0) {
        setTimeout(() => runStage(stageIndex + 1), 0);
        return;
      }

      const newNodeIds = new Set(newNodes.map(n => n.data.id));
      newNodes.forEach(n => loadedIds.add(n.data.id));
      const newEdges = graphData.edges.filter(
        e => loadedIds.has(e.data.source) && loadedIds.has(e.data.target)
      );
      instance.add([...newNodes, ...newEdges]);
      setRenderProgress({ loaded: loadedIds.size, total: graphData.nodes.length });

      // Yield to the browser so React commits the progress update before the
      // blocking layout computation starts (prevents UI appearing frozen).
      setTimeout(() => {
        const newEles = instance.nodes().filter(n => newNodeIds.has(n.id()));

        if (stageIndex >= 3) {
          // Storage nodes (stage 3) can number in the hundreds. Position them in a
          // simple grid manually — avoids cose-bilkent's O(n²) cost AND skips the
          // layout event system (collection.layout layoutstop is unreliable for subsets).
          // startBatch/endBatch batches all position writes into a single canvas redraw.
          const bb = instance.nodes().difference(newEles).boundingBox();
          const cols = Math.max(1, Math.ceil(Math.sqrt(newEles.length())));
          let i = 0;
          instance.startBatch();
          newEles.forEach((n) => {
            n.position({ x: bb.x1 + (i % cols) * 55, y: bb.y2 + 80 + Math.floor(i / cols) * 45 });
            i++;
          });
          instance.endBatch();
          setTimeout(() => runStage(stageIndex + 1), 50);
          return;
        }

        const layout = instance.layout({
          name: "cose-bilkent",
          animate: false,
          randomize: stageIndex === 0,
          idealEdgeLength: 120,
          nodeRepulsion: 12000,
          nodeDimensionsIncludeLabels: true,
          padding: 60,
          gravity: 0.15,
          numIter: adaptiveNumIter(instance.nodes().length),
          tile: true,
        } as cytoscape.LayoutOptions);

        layout.on("layoutstop", () => setTimeout(() => runStage(stageIndex + 1), 50));
        layout.run();
      }, 50);
    };

    runStage(0);

    return () => {
      instance.destroy();
      cyRef.current = null;
      setCy(null);
      setRenderProgress(null);
      setRenderComplete(false);
    };
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
    const callableTypes = new Set(["Function", "Method", "Constructor"]);
    cy.nodes().forEach((n) => {
      const typeVisible = filters.visibleNodeTypes.has(n.data("node_type"));
      const testVisible = filters.showTestFiles || !n.data("is_test");
      const visibilityVisible = !callableTypes.has(n.data("node_type")) || (
        !filters.hiddenVisibilities.has(n.data("visibility") as string) &&
        !(n.data("is_abstract") && filters.hiddenVisibilities.has("abstract"))
      );
      const lang = n.data("language") as string | undefined;
      const langVisible = !lang || filters.hiddenLanguages.size === 0 || !filters.hiddenLanguages.has(lang);
      n.style("display", typeVisible && testVisible && visibilityVisible && langVisible ? "element" : "none");
    });
    cy.edges().forEach((e) => { const show = filters.visibleEdgeRelations.has(e.data("relation")); e.style("display", show ? "element" : "none"); });
  }, [cy, filters, renderComplete]);

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

  const handleSelectNode = useCallback((nodeId: string) => {
    if (!cy || !graphData) return;
    cy.nodes().unselect();
    const ele = cy.getElementById(nodeId);
    if (ele.length) {
      ele.select();
      cy.animate({ center: { eles: ele }, zoom: 1.5 }, { duration: 300 });
      setSelectedNode(ele.data() as GraphNodeData);
    }
  }, [cy, graphData]);

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
      <div className="w-52 shrink-0 border-r border-surface-border overflow-y-auto h-full">
        <FilterPanel filters={filters} onChange={setFilters} graphData={graphData} />
      </div>

      {/* Graph canvas area */}
      <div className="flex-1 relative flex overflow-hidden">
        <div className="absolute top-3 left-3 z-10 flex gap-2">
          <button onClick={() => cy?.fit(undefined, 30)} className="btn-ghost text-xs px-3 py-1.5">Fit</button>
          <button onClick={() => cy?.elements().removeClass("blast-radius blast-radius-edge execution-flow faded")} className="btn-ghost text-xs px-3 py-1.5">Clear</button>
          <div className="w-48"><SearchBar onSearch={handleSearch} /></div>
        </div>
        <div ref={containerRef} className="flex-1 bg-surface" />
        {renderProgress && (
          <div className="absolute bottom-4 left-1/2 -translate-x-1/2 z-10 flex items-center gap-2 bg-surface-overlay border border-surface-border text-gray-400 text-xs px-3 py-1.5 rounded-full pointer-events-none">
            <span className="animate-pulse">●</span>
            Rendering {renderProgress.loaded} / {renderProgress.total} nodes…
          </div>
        )}
        <MiniMap cy={cy} />
        {selectedNode && (
          <NodeSidePanel node={selectedNode} graphData={graphData ?? { nodes: [], edges: [] }} onClose={() => setSelectedNode(null)} onBlastRadius={handleBlastRadius} onExecutionFlow={handleExecutionFlow} onSelectNode={handleSelectNode} />
        )}
      </div>
    </div>
  );
}
