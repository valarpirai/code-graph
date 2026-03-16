import type { Stylesheet } from "cytoscape";
import type { NodeType, EdgeRelation } from "../../../api/types";

export const NODE_COLORS: Record<NodeType, string> = {
  File: "#58a6ff",
  Class: "#3fb950",
  Function: "#d29922",
  Variable: "#8b949e",
  ExternalSymbol: "#f85149",
  Module: "#bc8cff",
};

export const EDGE_COLORS: Record<EdgeRelation, string> = {
  calls: "#e6edf3",
  imports: "#58a6ff",
  inherits: "#3fb950",
  contains: "#484f58",
  defines: "#bc8cff",
  uses: "#8b949e",
};

export const CLUSTER_PALETTE = [
  "#58a6ff", "#3fb950", "#d29922", "#bc8cff",
  "#f85149", "#79c0ff", "#56d364", "#e3b341",
];

export const baseStylesheet: Stylesheet[] = [
  {
    selector: "node",
    style: {
      label: "data(label)",
      "font-family": "JetBrains Mono, monospace",
      "font-size": "10px",
      color: "#e6edf3",
      "text-valign": "bottom",
      "text-margin-y": 4,
      "background-color": (ele) =>
        NODE_COLORS[ele.data("node_type") as NodeType] ?? "#484f58",
      "border-width": (ele) =>
        ele.data("node_type") === "ExternalSymbol" ? 2 : 0,
      "border-color": "#f85149",
      width: 18,
      height: 18,
    },
  },
  {
    selector: "edge",
    style: {
      width: 1.5,
      "line-color": (ele) =>
        EDGE_COLORS[ele.data("relation") as EdgeRelation] ?? "#484f58",
      "target-arrow-color": (ele) =>
        EDGE_COLORS[ele.data("relation") as EdgeRelation] ?? "#484f58",
      "target-arrow-shape": "triangle",
      "curve-style": "bezier",
      opacity: 0.7,
    },
  },
  {
    selector: "node:selected",
    style: {
      "border-width": 2,
      "border-color": "#58a6ff",
      "background-color": "#58a6ff",
    },
  },
  {
    selector: ".blast-radius",
    style: {
      "background-color": "#f85149",
      "border-color": "#f85149",
      "border-width": 2,
    },
  },
  {
    selector: ".blast-radius-edge",
    style: {
      "line-color": "#f85149",
      "target-arrow-color": "#f85149",
      width: 2.5,
      opacity: 1,
    },
  },
  {
    selector: ".execution-flow",
    style: {
      "background-color": "#bc8cff",
      "border-color": "#bc8cff",
      "border-width": 2,
    },
  },
  {
    selector: ".faded",
    style: { opacity: 0.1 },
  },
];
