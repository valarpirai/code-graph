import { useEffect, useRef, useState, useCallback } from "react";
import cytoscape from "cytoscape";
// @ts-expect-error: no types for cose-bilkent
import coseBilkent from "cytoscape-cose-bilkent";
// @ts-expect-error: no types for cytoscape-dagre
import dagre from "cytoscape-dagre";
import { useGraph, useClusters } from "../../../hooks/useGraph";
import { baseStylesheet, CLUSTER_PALETTE } from "./cytoscapeConfig";
import NodeSidePanel from "./NodeSidePanel";
import MiniMap from "./MiniMap";
import FilterPanel, { defaultFilterState } from "../FilterPanel/index";
import type { FilterState, LayoutName } from "../FilterPanel/index";
import SearchBar from "../../shared/SearchBar";
import type { GraphNodeData } from "../../../api/types";
import { getBlastRadius, getExecutionFlow } from "../../../api/client";

cytoscape.use(coseBilkent);
cytoscape.use(dagre);

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

function buildLayoutOptions(
  layoutName: LayoutName,
  nodeSpacing: number,
  nodeCount: number,
): cytoscape.LayoutOptions {
  switch (layoutName) {
    case "dagre":
      return {
        name: "dagre",
        animate: false,
        rankDir: "TB",
        nodeSep: Math.max(20, nodeSpacing / 500),
        rankSep: Math.max(40, nodeSpacing / 200),
        padding: 40,
      } as cytoscape.LayoutOptions;
    case "breadthfirst":
      return {
        name: "breadthfirst",
        animate: false,
        directed: true,
        spacingFactor: Math.max(0.5, nodeSpacing / 18000),
        padding: 40,
      } as cytoscape.LayoutOptions;
    case "circle":
      return {
        name: "circle",
        animate: false,
        spacingFactor: Math.max(0.5, nodeSpacing / 18000),
        padding: 40,
      } as cytoscape.LayoutOptions;
    case "grid":
      return {
        name: "grid",
        animate: false,
        avoidOverlap: true,
        spacingFactor: Math.max(0.5, nodeSpacing / 18000),
        padding: 40,
      } as cytoscape.LayoutOptions;
    case "cose-bilkent":
    default:
      return {
        name: "cose-bilkent",
        animate: false,
        randomize: true,
        idealEdgeLength: 120,
        nodeRepulsion: nodeSpacing,
        nodeDimensionsIncludeLabels: true,
        padding: 80,
        gravity: 0.2,
        numIter: adaptiveNumIter(nodeCount),
        tile: true,
      } as cytoscape.LayoutOptions;
  }
}

function applyGroupByFile(cy: cytoscape.Core, enabled: boolean): void {
  if (enabled) {
    const filePathToId = new Map<string, string>();
    cy.nodes().forEach((n) => {
      if (n.data("node_type") === "File") {
        const fp = n.data("file_path") as string | undefined;
        if (fp) filePathToId.set(fp, n.id());
      }
    });
    cy.startBatch();
    cy.nodes().forEach((n) => {
      if (n.data("node_type") === "File" || n.data("node_type") === "Module") return;
      const fp = n.data("file_path") as string | undefined;
      if (fp) {
        const fileId = filePathToId.get(fp);
        if (fileId) n.move({ parent: fileId });
      }
    });
    cy.endBatch();
  } else {
    cy.startBatch();
    cy.nodes().forEach((n) => { if (n.isChild()) n.move({ parent: null }); });
    cy.endBatch();
  }
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
  const [layouting, setLayouting] = useState(false);

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
    const addedEdgeIds = new Set<string>();

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
      const newEdgesInStage = graphData.edges.filter(
        e => loadedIds.has(e.data.source) && loadedIds.has(e.data.target) && !addedEdgeIds.has(e.data.id)
      );
      newEdgesInStage.forEach(e => addedEdgeIds.add(e.data.id));
      instance.add([...newNodes, ...newEdgesInStage]);
      setRenderProgress({ loaded: loadedIds.size, total: graphData.nodes.length });

      // Yield to browser so React commits the progress update before any
      // blocking computation starts.
      setTimeout(() => {
        const newEles = instance.nodes().filter(n => newNodeIds.has(n.id()));
        const totalNodes = instance.nodes().length;

        // Use fast manual grid for any stage with > 400 total nodes.
        // cose-bilkent is O(n²) and blocks the main thread for hundreds of
        // nodes; the post-render layout effect will apply the proper
        // force-directed pass once all stages complete.
        if (stageIndex >= 3 || totalNodes > 400) {
          const existing = instance.nodes().difference(newEles);
          const bb = existing.length
            ? existing.boundingBox()
            : { x1: 0, y1: 0, x2: 800, y2: 600 };
          const cols = Math.max(1, Math.ceil(Math.sqrt(newNodes.length)));
          let i = 0;
          instance.startBatch();
          newEles.forEach((n) => {
            n.position({ x: bb.x1 + (i % cols) * 140, y: bb.y2 + 100 + Math.floor(i / cols) * 70 });
            i++;
          });
          instance.endBatch();
          setTimeout(() => runStage(stageIndex + 1), 50);
          return;
        }

        // Small stages only (total ≤ 400): run cose-bilkent with conservative
        // params. Pre-scatter new nodes so they don't all start at (0,0).
        if (stageIndex > 0 && newNodes.length > 0) {
          const existing = instance.nodes().difference(newEles);
          const ebb = existing.length
            ? existing.boundingBox()
            : { x1: 0, y1: 0, x2: 600, y2: 400, w: 600, h: 400 };
          const cx = (ebb.x1 + ebb.x2) / 2;
          const ecy = (ebb.y1 + ebb.y2) / 2;
          const r = Math.max(ebb.w ?? 600, ebb.h ?? 400) * 0.6 + 150;
          const step = (2 * Math.PI) / newNodes.length;
          let si = 0;
          instance.startBatch();
          newEles.forEach((n) => {
            n.position({ x: cx + r * Math.cos(si * step), y: ecy + r * Math.sin(si * step) });
            si++;
          });
          instance.endBatch();
        }

        const layout = instance.layout({
          name: "cose-bilkent",
          animate: false,
          randomize: stageIndex === 0,
          idealEdgeLength: 100,
          nodeRepulsion: 12000,
          nodeDimensionsIncludeLabels: true,
          padding: 60,
          gravity: 0.25,
          numIter: adaptiveNumIter(totalNodes),
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
    cy.startBatch();
    cy.nodes().forEach((n) => {
      const nodeType = n.data("node_type") as string;
      const forceVisible = filters.groupByFile && nodeType === "File";
      const typeVisible = filters.visibleNodeTypes.has(n.data("node_type"));
      const testVisible = filters.showTestFiles || !n.data("is_test");
      const visibilityVisible = !callableTypes.has(nodeType) || (
        !filters.hiddenVisibilities.has(n.data("visibility") as string) &&
        !(n.data("is_abstract") && filters.hiddenVisibilities.has("abstract"))
      );
      const lang = n.data("language") as string | undefined;
      const langVisible = !lang || filters.hiddenLanguages.size === 0 || !filters.hiddenLanguages.has(lang);
      n.style("display", forceVisible || (typeVisible && testVisible && visibilityVisible && langVisible) ? "element" : "none");
    });
    cy.edges().forEach((e) => {
      e.style("display", filters.visibleEdgeRelations.has(e.data("relation")) ? "element" : "none");
    });
    cy.endBatch();
  }, [cy, filters, renderComplete]);

  // Shared layout runner: shows loading indicator, yields to browser so the
  // indicator renders before the synchronous layout computation blocks the thread.
  const runLayout = useCallback(() => {
    if (!cy) return;
    setLayouting(true);
    setTimeout(() => {
      applyGroupByFile(cy, filters.groupByFile);
      const visibleEles = cy.elements(":visible");
      const visNodeCount = visibleEles.nodes().length;
      // Auto-downgrade synchronous force-directed layouts that block the main
      // thread for large visible sets.
      let effectiveName: LayoutName = filters.layoutName;
      if (visNodeCount > 800 && effectiveName === "cose-bilkent") effectiveName = "dagre";
      if (visNodeCount > 2000) effectiveName = "grid";
      const l = visibleEles.layout(buildLayoutOptions(effectiveName, filters.nodeSpacing, visNodeCount));
      l.one("layoutstop", () => setLayouting(false));
      l.run();
    }, 50);
  }, [cy, filters.groupByFile, filters.layoutName, filters.nodeSpacing]);

  // Re-apply layout when algorithm, spacing, or grouping changes.
  // Deliberately excludes renderComplete from deps so it does NOT auto-run
  // on initial render completion — large graphs freeze the browser if layout
  // runs automatically. Users trigger layout via the "Layout" button or by
  // changing the algorithm picker.
  useEffect(() => {
    if (!cy || !renderComplete) return;
    const timer = setTimeout(runLayout, 300);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cy, filters.layoutName, filters.nodeSpacing, filters.groupByFile]);

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

  const handleReLayout = useCallback(() => runLayout(), [runLayout]);

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
          <button onClick={handleReLayout} disabled={!renderComplete} className="btn-ghost text-xs px-3 py-1.5 disabled:opacity-40">Layout</button>
          <div className="w-48"><SearchBar onSearch={handleSearch} /></div>
        </div>
        <div ref={containerRef} className="flex-1 bg-surface" />
        {(renderProgress || layouting) && (
          <div className="absolute bottom-6 left-1/2 -translate-x-1/2 z-10 pointer-events-none w-64">
            <div className="bg-surface-overlay border border-surface-border rounded-lg px-4 py-3 flex flex-col gap-2 shadow-lg">
              <div className="flex items-center justify-between text-xs">
                <span className="text-gray-300 font-medium">
                  {renderProgress ? "Building graph" : "Applying layout…"}
                </span>
                {renderProgress && (
                  <span className="text-gray-500 tabular-nums">
                    {renderProgress.loaded} / {renderProgress.total}
                  </span>
                )}
              </div>
              <div className="h-1.5 bg-surface-border rounded-full overflow-hidden">
                {renderProgress ? (
                  <div
                    className="h-full bg-accent-blue rounded-full transition-all duration-300 ease-out"
                    style={{ width: `${Math.round((renderProgress.loaded / renderProgress.total) * 100)}%` }}
                  />
                ) : (
                  <div className="h-full w-full bg-accent-blue rounded-full animate-pulse" />
                )}
              </div>
              {renderProgress && (
                <span className="text-[10px] text-gray-600 tabular-nums">
                  {Math.round((renderProgress.loaded / renderProgress.total) * 100)}%
                </span>
              )}
            </div>
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
