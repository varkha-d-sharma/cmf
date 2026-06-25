import React, { useMemo } from "react";
import ReactFlow, { Controls, Background, MiniMap, MarkerType, useNodes } from "reactflow";
import dagre from "dagre";
import LineageNode from "./LineageNode";

import "reactflow/dist/style.css";
import "./index.css";

const nodeTypes = { lineageNode: LineageNode };
const nodeWidth = 220; 
const nodeHeight = 80;

// Central color thematic scheme helper matching your MiniMap rules
const getNodeThemeColor = (type) => {
  switch (type) {
    case "Environment": return "#10b981"; // Green
    case "Stage": return "#f59e0b";   // Amber / Orange
    case "Model": return "#f59e0b";   // Alias fallback
    case "Node": return "#ef4444"; // Red
    case "Execution": return "#3b82f6"; // Blue
    default: return "#64748b";        // Gray
  }
};

// MiniMap Node Component 
const CustomMiniMapNode = ({ id, x, y, width, height }) => {
  const nodes = useNodes();
  const graphNode = nodes.find((n) => n.id === id);
  
  const nodeType = graphNode?.data?.type || "Node";
  const nodeName = graphNode?.data?.name || "";

  return (
    <g transform={`translate(${x},${y})`}>
      <rect
        width={width}
        height={height}
        rx={8}
        ry={8}
        fill={getNodeThemeColor(nodeType)}
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
        {nodeName.length > 18 ? `${nodeName.substring(0, 16)}...` : nodeName}
      </text>
    </g>
  );
};

// MODIFIED: Generates the exact clean layout tree seen in your example image
const transformLineageData = (rawJson) => {
  const nodesMap = new Map();
  const links = [];
  const flatItems = rawJson.flat();

  const determineType = (id) => {
    if (id.toLowerCase().includes("metrics")) return "Metrics";
    if (id.toLowerCase().includes("model")) return "Stage"; 
    if (id.toLowerCase().includes("train") || id.toLowerCase().includes("test") || id.toLowerCase().includes(".xml") || id.toLowerCase().includes("dataset") || id.toLowerCase().includes("input") || id.toLowerCase().includes("output")) return "Dataset";
    return "Execution";
  };

  // Step 1: Parse every element as an independent individual tree node (No Collapsing)
  flatItems.forEach((item) => {
    if (!item || !item.id) return;
    
    // Clean string name labels cleanly
    let cleanName = item.id.split("/").pop().split(":")[0];
    const type = determineType(item.id);

    if (!nodesMap.has(item.id)) {
      nodesMap.set(item.id, {
        id: item.id,
        name: cleanName,
        type: type,
        parents: item.parents || []
      });
    }
  });

  // Step 2: Directly map one-to-one edges to allow separate parallel branching
  const finalizedEdgesSet = new Set();
  nodesMap.forEach((node) => {
    node.parents.forEach((parentId) => {
      if (nodesMap.has(parentId) && parentId !== node.id) {
        const edgeKey = `${parentId}->${node.id}`;
        if (!finalizedEdgesSet.has(edgeKey)) {
          finalizedEdgesSet.add(edgeKey);
          links.push({ source: parentId, target: node.id });
        }
      }
    });
  });

  return { nodes: Array.from(nodesMap.values()), links };
};

// Layout reconfigured for a top-down vertical tree structure with side-by-side spacing
const getLayoutedElements = (nodes, edges) => {
  const g = new dagre.graphlib.Graph();
  
  // TB layout spreads child branches perfectly side-by-side horizontally
g.setGraph({
  rankdir: "TB",
  ranksep: 120,
  nodesep: 80,
  edgesep: 40,
  marginx: 50,
  marginy: 50
});
  g.setDefaultEdgeLabel(() => ({}));

  nodes.forEach((node) => g.setNode(node.id, { width: nodeWidth, height: nodeHeight }));
 edges.forEach((edge, index) =>
  g.setEdge(edge.source, edge.target, {
    weight: 10,
    minlen: 1,
  })
);

  dagre.layout(g);

  return nodes.map((node) => {
    const position = g.node(node.id);
    node.position = {
      x: position.x - nodeWidth / 2,
      y: position.y - nodeHeight / 2,
    };
    
    // Anchors connections to top/bottom edges matching your structure reference image
    node.targetPosition = 'top';
    node.sourcePosition = 'bottom';
    
    return node;
  });
};

const Hierarchical_LineageFlow = ({ data }) => {
  const proOptions = { hideAttribution: true };
  const { nodes, edges } = useMemo(() => {
    if (!data || data.length === 0) return { nodes: [], edges: [] };

    const formattedData = Array.isArray(data) && !data.nodes ? transformLineageData(data) : data;

    const rfNodes = formattedData.nodes.map((node) => ({
      id: node.id,
      type: "lineageNode",
      position: { x: 0, y: 0 },
      data: { 
        ...node,
        backgroundColor: getNodeThemeColor(node.type) // Injects colors directly to the node payload
      }, 
    }));

    const rfEdges = formattedData.links.map((link, index) => ({
      id: `edge-${index}`,
      source: link.source,
      target: link.target,
      type: "step", 
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
  }, [data]);

  return (
    <div style={{ width: "100%", height: "85vh", position: "relative" }}>
      <ReactFlow 
        nodes={nodes} 
        edges={edges} 
        nodeTypes={nodeTypes} 
        fitView                        
        fitViewOptions={{ padding: 0.15, includeHiddenNodes: true }} // Adjusted padding for cleaner fitting on vertical trees
        defaultViewport={{x: 0, y: 0, zoom:1}}
        minZoom={0.2}
        maxZoom={2}
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
            position: "fixed"
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

export default Hierarchical_LineageFlow;