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
import ReactFlow, { Controls, Background, MiniMap, MarkerType, useNodes } from "reactflow";
import dagre from "dagre";

import "reactflow/dist/style.css";
import "./index.css";
import LineageNode1 from "./lineagenode";

const nodeTypes = { lineageNode: LineageNode1 };
const nodeWidth = 220;
const nodeHeight = 90;

// MiniMap Node Component with text value lookup using useNodes()
const CustomMiniMapNode = ({ id, x, y, width, height }) => {
  const nodes = useNodes();
  const graphNode = nodes.find((n) => n.id === id);

  const nodeType = graphNode?.data?.type || "Node";
  const nodeName = graphNode?.data?.name || "";

  const getBackgroundColor = (type) => {
    switch (type) {
      case "Dataset": return "#10b981";
      case "Model": return "#f59e0b";
      case "Metrics": return "#ef4444";
      case "Execution": return "#3b82f6";
      default: return "#64748b";
    }
  };

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

  originalNodeMap.forEach((node) => {
    node.parents.forEach((parentId) => {
      if (parentId !== node.id) {
        const edgeKey = `${parentId}->${node.id}`;
        if (!edgeSet.has(edgeKey)) {
          edgeSet.add(edgeKey);
          rawLinks.push({ source: parentId, target: node.id });
        }
      }
    });
  });

  const adjacency = new Map();
  rawLinks.forEach(({ source, target }) => {
    if (!adjacency.has(source)) adjacency.set(source, new Set());
    adjacency.get(source).add(target);
  });

  const reachabilityCache = new Map();
  const isReachableWithoutEdge = (source, target, skipDirectEdge) => {
    const cacheKey = `${source}->${target}:${skipDirectEdge}`;
    if (reachabilityCache.has(cacheKey)) {
      return reachabilityCache.get(cacheKey);
    }

    const visited = new Set();
    const stack = [...(adjacency.get(source) || [])].filter(
      (next) => !(skipDirectEdge && next === target)
    );

    let reachable = false;
    while (stack.length) {
      const current = stack.pop();
      if (current === target) {
        reachable = true;
        break;
      }
      if (visited.has(current)) continue;
      visited.add(current);
      (adjacency.get(current) || []).forEach((next) => {
        if (!visited.has(next)) {
          stack.push(next);
        }
      });
    }

    reachabilityCache.set(cacheKey, reachable);
    return reachable;
  };

  const links = rawLinks.filter(({ source, target }) => {
    return !isReachableWithoutEdge(source, target, true);
  });

  return { nodes: Array.from(originalNodeMap.values()), links };
}; // closes transformLineageData

// FIXED: Layout configured for vertical flow with top/bottom anchors
const getLayoutedElements = (nodes, edges) => {
  const g = new dagre.graphlib.Graph();
  g.setGraph({ rankdir: "TB", ranksep: 140, nodesep: 60 }); // ranksep raised from 100 to 140
  g.setDefaultEdgeLabel(() => ({}));

  nodes.forEach((node) => g.setNode(node.id, { width: nodeWidth, height: nodeHeight }));
  edges.forEach((edge) => g.setEdge(edge.source, edge.target));

  dagre.layout(g);

  const positioned = nodes.map((node) => {
    const position = g.node(node.id);
    return { ...node, rawX: position.x, rawY: position.y };
  });

  const rowMap = new Map();
  positioned.forEach((node) => {
    const rowKey = Math.round(node.rawY / 10) * 10;
    if (!rowMap.has(rowKey)) rowMap.set(rowKey, []);
    rowMap.get(rowKey).push(node);
  });

  const FIXED_GAP = nodeWidth + 60;

  rowMap.forEach((rowNodes) => {
    rowNodes.sort((a, b) => a.rawX - b.rawX);
    const totalWidth = (rowNodes.length - 1) * FIXED_GAP;
    const startX = -totalWidth / 2;

    rowNodes.forEach((node, index) => {
      node.evenX = startX + index * FIXED_GAP;
    });
  });

  return positioned.map((node) => {
    node.position = {
      x: node.evenX - nodeWidth / 2,
      y: node.rawY - nodeHeight / 2,
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

    //Linking of node logic rendered here.
    const rfEdges = (formattedData?.links ?? formattedData?.edges ??[]).map((link, index) => ({
      id: `edge-${index}`,
      source: link.source,
      target: link.target,
      type: isArtifactExecutionLineage ? "simplebezier" : "step",
      markerEnd: {
        type: MarkerType.Arrow,
        color: "#b1b1b7"
      },
      style: {
        stroke: "#b1b1b7",
        strokeWidth: 1.5,
      }
    }));
    return {
      nodes: getLayoutedElements(rfNodes, rfEdges),
      edges: rfEdges,
    };
  }, [data, lineageType]);

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
      >
        <MiniMap
          position="bottom-right"
          nodeComponent={CustomMiniMapNode}
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