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
 * Renders an interactive hierarchical lineage graph using React Flow.
 * Transforms raw lineage data into nodes and edges, computes a fast
 * top-down rank/barycenter layout, and displays the lineage with custom
 * nodes, edge routing, MiniMap, zoom/pan controls, and fit-to-view support.
 *
 * Shared MiniMap/canvas/node-edge-mapping code lives in ./LineageFlowCommon.
 */

import React, { useMemo } from "react";
import "./index.css";
import lineagenode from "../HierarchicalLineageFlow/lineagenode";
import { LineageCanvas, nodeWidth, buildReactFlowNodes, buildReactFlowEdges} from "../../pages/lineage/LineageFlowCommon";

// React Flow Configuration Constants
const nodeTypes = { lineageNode: lineagenode };
const nodeHeight = 90;
const RANK_GAP = nodeHeight + 140; // Vertical spacing between graph levels
const FIXED_GAP = nodeWidth + 60;  // Horizontal spacing between adjacent nodes

// Visual mapping for lineage node categories
const TYPE_COLORS = {
  Dataset: "#10b981",
  Model: "#f59e0b",
  Metrics: "#ef4444",
  Execution: "#3b82f6",
};

/**
 * Matches a node ID against naming keywords to resolve its type.
 */
const getBackgroundColor = (type) => TYPE_COLORS[type] || "#64748b";

/**
 * Parses and builds nodes and parent-child edges from a flat execution list.
 * Applies a Transitive Reduction algorithm to strip redundant transitive links.
 * 
 * @param {Array} rawJson - Flat structure of pipeline lineage entries.
 * @returns {Object} Extracted unique nodes and reduced list of direct links.
 */
const transformLineageData = (rawJson) => {
  const flatItems = rawJson.flat();
  const originalNodeMap = new Map();

  // Helper to categorize nodes based on ID keyword patterns
  const determineType = (id) => {
    if (id.includes("metrics")) return "Metrics";
    if (id.includes("model")) return "Model";
    if (id.includes("train") || id.includes("test") || id.includes(".xml")) return "Dataset";
    return "Execution";
  };

  // Populate unique node map and ensure virtual parent placeholders are registered
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

  // Construct raw links and populate adjacent neighbor maps
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

  // Depth-first traversal mapping to track downstream node paths
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

  // Transitive Reduction: Drop indirect paths if a direct edge exists
  const links = rawLinks.filter(({ source, target }) => {
    const neighbours = adjacency.get(source);
    if (!neighbours || neighbours.size <= 1) return true;
    for (const w of neighbours) {
      if (w === target) continue;
      if (computeReachable(w).has(target)) {
        return false; // Skip edge since an alternate multi-step route exists
      }
    }
    return true;
  });

  return { nodes: Array.from(originalNodeMap.values()), links };
};

/**
 * Custom fast Dagre-like layout engine.
 * Computes node coordinates using network in-degrees and Barycenter ordering.
 * 
 * @param {Array} nodes - React Flow structured node components.
 * @param {Array} edges - React Flow connection configurations.
 * @returns {Array} Processed node items complete with relative coordinates.
 */
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

  // Calculate dependency depths (In-degrees)
  const inDegree = new Map();
  nodeIds.forEach((id) => inDegree.set(id, 0));
  edges.forEach(({ target }) => inDegree.set(target, (inDegree.get(target) || 0) + 1));

  // Determine root tracking starting points
  const rank = new Map();
  const queue = [];
  nodeIds.forEach((id) => {
    if ((inDegree.get(id) || 0) === 0) {
      rank.set(id, 0);
      queue.push(id);
    }
  });

  // Breadth-First-Search step calculation to establish hierarchical layers
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

  // Assemble horizontal row tracks for the graph
  const rowMap = new Map();
  nodeIds.forEach((id) => {
    const r = rank.get(id);
    if (!rowMap.has(r)) rowMap.set(r, []);
    rowMap.get(r).push(id);
  });
  const sortedRanks = Array.from(rowMap.keys()).sort((a, b) => a - b);

  // Apply Barycenter method sorting to cut down edge crossovers
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
    // Distribute centers symmetric to the central axis
    const totalWidth = (rowIds.length - 1) * FIXED_GAP;
    const startX = -totalWidth / 2;
    rowIds.forEach((id, index) => xPosition.set(id, startX + index * FIXED_GAP));
  });

  // Format node dimensions and handle connection constraints
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

/**
 * Shared wrapper managing lineage tree state conversions and canvas routing.
 */
const CommonLineageComponent = ({ data, lineageType }) => {
  const isArtifactExecutionLineage = lineageType === "Artifact_Execution_Tree";

  // Cache elements array calculations to prevent unnecessary layout computations
  const { nodes, edges } = useMemo(() => {
    if (!data || data.length === 0) return { nodes: [], edges: [] };
    
    // Normalize either raw array inputs or pre-transformed structures
    const formattedData = Array.isArray(data) && !data.nodes ? transformLineageData(data) : data;

    // Convert datasets into React Flow compliant schema elements
    const rfNodes = buildReactFlowNodes(formattedData.nodes);
    const rfEdges = buildReactFlowEdges(formattedData?.links ?? formattedData?.edges ?? [], {
      edgeType: isArtifactExecutionLineage ? "simplebezier" : "step",
    });

    // Run structural positioning calculations
    const laidOutNodes = getLayoutedElements(rfNodes, rfEdges);

    return { nodes: laidOutNodes, edges: rfEdges };
  }, [data, lineageType]);

  return (
    <LineageCanvas
      nodes={nodes}
      edges={edges}
      nodeTypes={nodeTypes}
      colorFn={getBackgroundColor}
      onlyRenderVisibleElements
      nodesDraggable={false}
      nodesConnectable={false}
      elementsSelectable={false}
    />
  );
};

export default CommonLineageComponent;