import React, { useMemo } from "react";
import ReactFlow, { Controls, Background, MiniMap, MarkerType, useNodes } from "reactflow";
import dagre from "dagre";
import LineageNode from "./LineageNode";

import "reactflow/dist/style.css";
import "./index.css";

const nodeTypes = { lineageNode: LineageNode };
const nodeWidth = 220;
const nodeHeight = 90;

// FIXED: MiniMap Node Component with text value lookup using useNodes()
const CustomMiniMapNode = ({ id, x, y, width, height }) => {
  const nodes = useNodes();
  const graphNode = nodes.find((n) => n.id === id);
  
  // Extract values from the true active node data structure
  const nodeType = graphNode?.data?.type || "Node";
  const nodeName = graphNode?.data?.name || "";

  const getBackgroundColor = (type) => {
    switch (type) {
      case "Dataset": return "#10b981"; // Green
      case "Model": return "#f59e0b";   // Amber
      case "Metrics": return "#ef4444"; // Red
      case "Execution": return "#3b82f6"; // Blue
      default: return "#64748b";
    }
  };

  return (
    <g transform={`translate(${x},${y})`}>
      {/* Mini Card Base */}
      <rect
        width={width}
        height={height}
        rx={8}
        ry={8}
        fill={getBackgroundColor(nodeType)}
        stroke="#ffffff"
        strokeWidth={2}
      />
      
      {/* Node Type Label */}
      <text
        x={width / 2}
        y={height / 3 + 4}
        textAnchor="middle"
        fill="#ffffff"
        style={{
          fontSize: "20px", // Scaled to read cleanly inside 220x90 dimensions
          fontWeight: "bold",
          fontFamily: "Inter, sans-serif",
          pointerEvents: "none",
        }}
      >
        {nodeType.toUpperCase()}
      </text>

      {/* Node Name/Filename Label */}
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
        {nodeName.length > 18 ? `${nodeName.substring(0, 16)}...` : nodeName}
      </text>
    </g>
  );
};

const transformLineageData = (rawJson) => {
  const nodeMap = new Map();
  const links = [];
  const flatItems = rawJson.flat();

  const determineType = (id) => {
    if (id.includes("metrics")) return "Metrics";
    if (id.includes("model")) return "Model";
    if (id.includes("train") || id.includes("test") || id.includes(".xml")) return "Dataset";
    return "Execution";
  };

  flatItems.forEach((item) => {
    let cleanName = item.id.split("/").pop().split(":")[0];
    
    if (!nodeMap.has(item.id)) {
      nodeMap.set(item.id, {
        id: item.id,
        name: cleanName,
        type: determineType(item.id),
        uuid: item.id.includes("/") ? item.id.split("/")[0] : undefined
      });
    }

    if (item.parents && item.parents.length > 0) {
      item.parents.forEach((parentId) => {
        links.push({ source: parentId, target: item.id });
      });
    }
  });

  return { nodes: Array.from(nodeMap.values()), links };
};

const getLayoutedElements = (nodes, edges) => {
  const g = new dagre.graphlib.Graph();
  g.setGraph({ rankdir: "LR", ranksep: 120, nodesep: 80 });
  g.setDefaultEdgeLabel(() => ({}));

  nodes.forEach((node) => g.setNode(node.id, { width: nodeWidth, height: nodeHeight }));
  edges.forEach((edge) => g.setEdge(edge.source, edge.target));

  dagre.layout(g);

  return nodes.map((node) => {
    const position = g.node(node.id);
    node.position = {
      x: position.x - nodeWidth / 2,
      y: position.y - nodeHeight / 2,
    };
    return node;
  });
};

const HierarchicalLineageFlow2 = ({ data }) => {
    const proOptions = { hideAttribution: true };
  const { nodes, edges } = useMemo(() => {
    if (!data || data.length === 0) return { nodes: [], edges: [] };

    const formattedData = Array.isArray(data) && !data.nodes ? transformLineageData(data) : data;

    const rfNodes = formattedData.nodes.map((node) => ({
      id: node.id,
      type: "lineageNode",
      position: { x: 0, y: 0 },
      data: { ...node },
    }));

    const rfEdges = formattedData.links.map((link, index) => ({
      id: `edge-${index}`,
      source: link.source,
      target: link.target,
      type: "smoothstep",
      markerEnd: { type: MarkerType.ArrowClosed },
    }));

    return {
      nodes: getLayoutedElements(rfNodes, rfEdges),
      edges: rfEdges,
    };
  }, [data]);

  return (
    <div style={{ width: "100%", height: "85vh", position: "relative" }}>
      <ReactFlow 
        nodes={nodes} 
        edges={edges} 
        nodeTypes={nodeTypes} 
        fitView                        
        fitViewOptions={{ padding: 0.3 }} 
        minZoom={0.4}
        proOptions={proOptions}
      >
        <MiniMap 
          position="bottom-right" 
          nodeComponent={CustomMiniMapNode} // Wire up fixed custom text component
          maskColor="rgba(241, 245, 249, 0.4)"
          style={{
            backgroundColor: "#f8fafc",
            border: "1px solid #cbd5e1",
            borderRadius: "8px",
            width: 300, // Slightly expanded to make small texts cleanly legible
            height: 160,
            position:"fixed"
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

export default HierarchicalLineageFlow2;