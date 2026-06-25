import React, { useMemo } from "react";
import ReactFlow, { Controls, Background, MiniMap, MarkerType, useNodes } from "reactflow";
import dagre from "dagre";
import LineageNode from "./LineageNode";

import "reactflow/dist/style.css";
import "./index.css";

const nodeTypes = { lineageNode: LineageNode };
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
      case "Dataset": return "#10b981"; // Green
      case "Model": return "#f59e0b";   // Amber
      case "Metrics": return "#ef4444"; // Red
      case "Execution": return "#3b82f6"; // Blue
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
        {nodeName.length > 18 ? `${nodeName.substring(0, 16)}...` : nodeName}
      </text>
    </g>
  );
};

// const transformLineageData = (rawJson) => {
//   const nodeMap = new Map();
//   const links = [];
//   const flatItems = rawJson.flat();

//   const determineType = (id) => {
//     if (id.includes("metrics")) return "Metrics";
//     if (id.includes("model")) return "Model";
//     if (id.includes("train") || id.includes("test") || id.includes(".xml")) return "Dataset";
//     return "Execution";
//   };

//   flatItems.forEach((item) => {
//     let cleanName = item.id.split("/").pop().split(":")[0];
    
//     if (!nodeMap.has(item.id)) {
//       nodeMap.set(item.id, {
//         id: item.id,
//         name: cleanName,
//         type: determineType(item.id),
//         uuid: item.id.includes("/") ? item.id.split("/")[0] : undefined
//       });
//     }

//     if (item.parents && item.parents.length > 0) {
//       item.parents.forEach((parentId) => {
//         links.push({ source: parentId, target: item.id });
//       });
//     }
//   });

//   return { nodes: Array.from(nodeMap.values()), links };
// };

const transformLineageData = (rawJson) => {
  const originalNodeMap = new Map();
  const links = [];
  const flatItems = rawJson.flat();

  const determineType = (id) => {
    if (id.includes("metrics")) return "Metrics";
    if (id.includes("model")) return "Model";
    if (id.includes("train") || id.includes("test") || id.includes(".xml")) return "Dataset";
    return "Execution";
  };

  // Step 1: Parse data and group identical dependencies to find parallel clusters
  flatItems.forEach((item) => {
    let cleanName = item.id.split("/").pop().split(":")[0];
    const parentKey = item.parents ? [...item.parents].sort().join(",") : "ROOT";
    const type = determineType(item.id);

    if (!originalNodeMap.has(item.id)) {
      originalNodeMap.set(item.id, {
        id: item.id,
        name: cleanName,
        type: type,
        parentKey: parentKey,
        parents: item.parents || []
      });
    }
  });

  // Step 2: Group parallel configurations into unified stage lines
  const finalNodesMap = new Map();
  const collapsedMapping = new Map(); // Maps old single IDs to the new grouped Stage IDs

  originalNodeMap.forEach((node) => {
    // We only collapse execution variants (like 1.1, 1.2, 1.3) sharing the same inputs
    if (node.type === "Execution") {
      const stageGroupId = `stage-execution-${node.parentKey}-${node.name}`;
      
      if (!finalNodesMap.has(stageGroupId)) {
        finalNodesMap.set(stageGroupId, {
          id: stageGroupId,
          name: `${node.name} (Parallel Runs)`, 
          type: "Execution",
          parents: node.parents
        });
      }
      collapsedMapping.set(node.id, stageGroupId);
    } else {
      // Keep primary Datasets, Models, and Metrics distinct
      finalNodesMap.set(node.id, node);
      collapsedMapping.set(node.id, node.id);
    }
  });

  // Step 3: Re-route links cleanly to the newly grouped linear stages
  const finalizedEdgesSet = new Set();

  originalNodeMap.forEach((node) => {
    const targetStageId = collapsedMapping.get(node.id);
    
    node.parents.forEach((parentId) => {
      const sourceStageId = collapsedMapping.get(parentId);
      
      // Prevent self-looping and remove duplicate stacked lines
      if (sourceStageId && targetStageId && sourceStageId !== targetStageId) {
        const edgeKey = `${sourceStageId}->${targetStageId}`;
        if (!finalizedEdgesSet.has(edgeKey)) {
          finalizedEdgesSet.add(edgeKey);
          links.push({ source: sourceStageId, target: targetStageId });
        }
      }
    });
  });

  return { nodes: Array.from(finalNodesMap.values()), links };
};


// FIXED: Layout configured for vertical flow with top/bottom anchors
const getLayoutedElements = (nodes, edges) => {
  const g = new dagre.graphlib.Graph();
  
  // 1. CHANGED: rankdir modified from "LR" to "TB" (Top to Bottom)
  g.setGraph({ rankdir: "TB", ranksep: 80, nodesep: 60 });
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
    
    // 2. CHANGED: Explicitly force handles to line up at the Top and Bottom sides
    node.targetPosition = 'top';
    node.sourcePosition = 'bottom';
    
    return node;
  });
};

const HierarchicalLineageFlow = ({ data }) => {
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
      type: "step", 
      markerEnd: { 
      type: MarkerType.Arrow, 
      color: "#b1b1b7"},
      style: {
        stroke: "#b1b1b7",
        strokeWidth: 1.5,}
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
        fitViewOptions={{ padding: 0.15 }} // Adjusted padding for cleaner fitting on vertical trees
        minZoom={0.2} // Decreased minZoom to allow complex layouts to fit on screens perfectly
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

export default HierarchicalLineageFlow;

