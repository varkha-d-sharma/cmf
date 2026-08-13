/***
 * Copyright (2023) Hewlett Packard Enterprise Development LP
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * You may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 ***/

/**
 * Renders an interactive hierarchical lineage graph using React Flow and Dagre.
 * Transforms raw lineage data into nodes and edges, computes an automatic
 * top-down layout, and displays the lineage with custom nodes, edge routing,
 * MiniMap, zoom/pan controls, and fit-to-view support.
 */

import React, { useMemo } from "react";
import ReactFlow, { Controls, Background, MiniMap, MarkerType } from "reactflow";

import "reactflow/dist/style.css";
import "./index.css";
import LineageNode1 from "./lineagenode";

const nodeTypes = { lineageNode: LineageNode1 };
const nodeWidth = 220;
const nodeHeight = 90;
const RANK_GAP = nodeHeight + 140;
const FIXED_GAP = nodeWidth + 60;

const EDGE_MARKER_END = { type: MarkerType.Arrow, color: "#b1b1b7" };
const EDGE_STYLE = { stroke: "#b1b1b7", strokeWidth: 1.5 };

const TYPE_COLORS = {
  Dataset: "#10b981",
  Model: "#f59e0b",
  Metrics: "#ef4444",
  Execution: "#3b82f6",
};
const getBackgroundColor = (type) => TYPE_COLORS[type] || "#64748b";

const CustomMiniMapNode = ({ id, x, y, width, height, nodeDataMap }) => {
  const graphNode = nodeDataMap.get(id);
  const nodeType = graphNode?.type || "Node";
  const nodeName = graphNode?.name || "";

  return (
    <g transform={`translate(${x},${y})`}>
      <rect
        width={width}
        height={height}
        rx={8}
        ry={8}
        fill={getBackgroundColor(nodeType)}
        stroke="#ffffff"
        strokeWidth={2}
      />
      <text
        x={width / 2}
        y={height / 3 + 4}
        textAnchor="middle"
        fill="#ffffff"
        style={{
          fontSize: "20px",
          fontWeight: "bold",
          fontFamily: "Inter, sans-serif",
          pointerEvents: "none",
        }}
      >
        {nodeType.toUpperCase()}
      </text>
      <text
        x={width / 2}
        y={(2 * height) / 3 + 8}
        textAnchor="middle"
        fill="rgba(255, 255, 255, 0.9)"
        style={{
          fontSize: "16px",
          fontFamily: "Inter, sans-serif",
          pointerEvents: "none",
        }}
      >
        {nodeName.length > 18 ?` ${nodeName.substring(0, 16)}...` : nodeName}
      </text>
    </g>
  );
};

const transformLineageData = (rawJson) => {
  const flatItems = rawJson.flat();
  const originalNodeMap = new Map();

  const determineType = (id) => {
    if (id.includes("metrics")) return "Metrics";
    if (id.includes("model")) return "Model";
    if (id.includes("train") || id.includes("test") || id.includes(".xml")) return "Dataset";
    return "Execution";
  };

  flatItems.forEach((item) => {
    const sortedParents = item.parents ? Array.from(new Set(item.parents)).sort() : [];
    const type = determineType(item.id);

    if (!originalNodeMap.has(item.id)) {
      originalNodeMap.set(item.id, {
        id: item.id,
        name: item.id,
        type,
        parents: sortedParents,
      });
    }

    sortedParents.forEach((parentId) => {
      if (!originalNodeMap.has(parentId)) {
        originalNodeMap.set(parentId, {
          id: parentId,
          name: parentId,
          type: determineType(parentId),
          parents: [],
        });
      }
    });
  });

  const rawLinks = [];
  const edgeSet = new Set();
  const adjacency = new Map();

  originalNodeMap.forEach((node) => {
    node.parents.forEach((parentId) => {
      if (parentId !== node.id) {
        const edgeKey = `${parentId}->${node.id}`;
        if (!edgeSet.has(edgeKey)) {
          edgeSet.add(edgeKey);
          rawLinks.push({ source: parentId, target: node.id });
          if (!adjacency.has(parentId)) adjacency.set(parentId, new Set());
          adjacency.get(parentId).add(node.id);
        }
      }
    });
  });

  const reachabilityFrom = new Map();
  const computeReachable = (start) => {
    if (reachabilityFrom.has(start)) return reachabilityFrom.get(start);
    const visited = new Set();
    const stack = [...(adjacency.get(start) || [])];
    while (stack.length) {
      const current = stack.pop();
      if (visited.has(current)) continue;
      visited.add(current);
      (adjacency.get(current) || []).forEach((next) => {
        if (!visited.has(next)) stack.push(next);
      });
    }
    reachabilityFrom.set(start, visited);
    return visited;
  };

  const links = rawLinks.filter(({ source, target }) => {
    const neighbours = adjacency.get(source);
    if (!neighbours || neighbours.size <= 1) return true;
    for (const w of neighbours) {
      if (w === target) continue;
      if (computeReachable(w).has(target)) {
        return false;
      }
    }
    return true;
  });

  return { nodes: Array.from(originalNodeMap.values()), links };
}; // closes transformLineageData

// ---- Fast custom layout (replaces dagre.layout) ----
const getLayoutedElements = (nodes, edges) => {
  const nodeIds = nodes.map((n) => n.id);
  const adjacency = new Map();
  const parentsOf = new Map();
  nodeIds.forEach((id) => {
    adjacency.set(id, new Set());
    parentsOf.set(id, []);
  });
  edges.forEach(({ source, target }) => {
    if (!adjacency.has(source)) adjacency.set(source, new Set());
    adjacency.get(source).add(target);
    if (!parentsOf.has(target)) parentsOf.set(target, []);
    parentsOf.get(target).push(source);
  });

  const inDegree = new Map();
  nodeIds.forEach((id) => inDegree.set(id, 0));
  edges.forEach(({ target }) => inDegree.set(target, (inDegree.get(target) || 0) + 1));

  const rank = new Map();
  const queue = [];
  nodeIds.forEach((id) => {
    if ((inDegree.get(id) || 0) === 0) {
      rank.set(id, 0);
      queue.push(id);
    }
  });

  const remaining = new Map(inDegree);
  let qi = 0;
  while (qi < queue.length) {
    const u = queue[qi++];
    const uRank = rank.get(u) || 0;
    (adjacency.get(u) || new Set()).forEach((v) => {
      if (!rank.has(v) || rank.get(v) < uRank + 1) rank.set(v, uRank + 1);
      remaining.set(v, remaining.get(v) - 1);
      if (remaining.get(v) === 0) queue.push(v);
    });
  }
  nodeIds.forEach((id) => {
    if (!rank.has(id)) rank.set(id, 0);
  });

  const rowMap = new Map();
  nodeIds.forEach((id) => {
    const r = rank.get(id);
    if (!rowMap.has(r)) rowMap.set(r, []);
    rowMap.get(r).push(id);
  });
  const sortedRanks = Array.from(rowMap.keys()).sort((a, b) => a - b);

  const xPosition = new Map();
  sortedRanks.forEach((r) => {
    const rowIds = rowMap.get(r);
    if (r !== 0) {
      rowIds.sort((a, b) => {
        const aParents = parentsOf.get(a) || [];
        const bParents = parentsOf.get(b) || [];
        const aBary = aParents.length
          ? aParents.reduce((sum, p) => sum + (xPosition.get(p) ?? 0), 0) / aParents.length
          : 0;
        const bBary = bParents.length
          ? bParents.reduce((sum, p) => sum + (xPosition.get(p) ?? 0), 0) / bParents.length
          : 0;
        return aBary - bBary;
      });
    }
    const totalWidth = (rowIds.length - 1) * FIXED_GAP;
    const startX = -totalWidth / 2;
    rowIds.forEach((id, index) => xPosition.set(id, startX + index * FIXED_GAP));
  });

  return nodes.map((node) => {
    node.position = {
      x: (xPosition.get(node.id) ?? 0) - nodeWidth / 2,
      y: rank.get(node.id) * RANK_GAP - nodeHeight / 2,
    };
    node.targetPosition = "top";
    node.sourcePosition = "bottom";
    return node;
  });
};

const HierarchicalLineageFlow = ({ data, lineageType }) => {
  const proOptions = { hideAttribution: true };
  const isArtifactExecutionLineage = lineageType === "Artifact_Execution_Tree";

  const { nodes, edges } = useMemo(() => {
    if (!data || data.length === 0) return { nodes: [], edges: [] };
    const formattedData = Array.isArray(data) && !data.nodes ? transformLineageData(data) : data;
    const rfNodes = formattedData.nodes.map((node) => ({
      id: node.id,
      type: "lineageNode",
      position: { x: 0, y: 0 },
      data: { ...node },
    }));

    const rfEdges = (formattedData?.links ?? formattedData?.edges ?? []).map((link, index) => ({
      id: `edge-${index}`,
      source: link.source,
      target: link.target,
      type: isArtifactExecutionLineage ? "simplebezier" : "step",
      markerEnd: EDGE_MARKER_END,
      style: EDGE_STYLE,
    }));

    const laidOutNodes = getLayoutedElements(rfNodes, rfEdges);

    return { nodes: laidOutNodes, edges: rfEdges };
  }, [data, lineageType]);

  const nodeDataMap = useMemo(() => {
    const map = new Map();
    nodes.forEach((n) => map.set(n.id, n.data));
    return map;
  }, [nodes]);

  const minimapNodeComponent = useMemo(
    () => (props) => <CustomMiniMapNode {...props} nodeDataMap={nodeDataMap} />,
    [nodeDataMap]
  );

  return (
    <div style={{ width: "100%", height: "85vh", position: "relative" }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.15 }}
        minZoom={0.2}
        proOptions={proOptions}
        onlyRenderVisibleElements
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable={false}
      >
        <MiniMap
          position="bottom-right"
          nodeComponent={minimapNodeComponent}
          maskColor="rgba(241, 245, 249, 0.4)"
          style={{
            backgroundColor: "#f8fafc",
            border: "1px solid #cbd5e1",
            borderRadius: "8px",
            width: 300,
            height: 160,
            position: "fixed",
          }}
          zoomable
          pannable
        />
        <Controls />
        <Background />
      </ReactFlow>
    </div>
  );
};

export default HierarchicalLineageFlow;