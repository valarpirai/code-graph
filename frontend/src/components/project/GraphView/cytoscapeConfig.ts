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
  containsFile: "#6e7681",
  containsClass: "#79c0ff",
  defines: "#bc8cff",
  uses: "#8b949e",
  hasMethod: "#d29922",
  hasField: "#8b949e",
};

export const CLUSTER_PALETTE = [
  "#58a6ff", "#3fb950", "#d29922", "#bc8cff",
  "#f85149", "#79c0ff", "#56d364", "#e3b341",
];

export const baseStylesheet: Stylesheet[] = [
  {
    selector: "node",
    style: {
      label: (ele) => {
        const raw: string = ele.data("label") ?? "";
        return raw.length > 24 ? raw.slice(0, 22) + "…" : raw;
      },
      "font-family": "JetBrains Mono, monospace",
      "font-size": "9px",
      color: "#c9d1d9",
      "text-valign": "bottom",
      "text-margin-y": 5,
      "text-background-color": "#0d1117",
      "text-background-opacity": 0.7,
      "text-background-padding": "2px",
      "background-color": (ele) =>
        NODE_COLORS[ele.data("node_type") as NodeType] ?? "#484f58",
      "border-width": (ele) => {
        if (ele.data("node_type") === "ExternalSymbol") return 2;
        if (ele.data("class_kind") && ele.data("class_kind") !== "class") return 2;
        return 0;
      },
      "border-color": (ele) => {
        switch (ele.data("class_kind")) {
          case "interface":      return "#58a6ff";   // blue
          case "abstract_class": return "#bc8cff";   // purple
          case "final_class":    return "#d29922";   // amber
          default: return "#f85149";
        }
      },
      "border-style": (ele) => {
        if (ele.data("class_kind") === "interface") return "dashed";
        return "solid";
      },
      width: 22,
      height: 22,
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
  {
    selector: "node[?is_test]",
    style: {
      "border-width": 2,
      "border-color": "#f0883e",
      "border-style": "dashed",
    },
  },
  // Variable kind overrides — all use the Variable base color but with different borders
  { selector: "node[var_kind = 'instance']",  style: { "border-width": 1, "border-color": "#8b949e", "border-style": "solid" } },
  { selector: "node[var_kind = 'static']",    style: { "border-width": 2, "border-color": "#bc8cff", "border-style": "solid" } },
  { selector: "node[var_kind = 'constant']",  style: { "border-width": 2, "border-color": "#d29922", "border-style": "solid" } },
  { selector: "node[var_kind = 'final']",     style: { "border-width": 2, "border-color": "#58a6ff", "border-style": "solid" } },
  { selector: "node[var_kind = 'local']",     style: { "border-width": 1, "border-color": "#484f58", "border-style": "dotted" } },
];
