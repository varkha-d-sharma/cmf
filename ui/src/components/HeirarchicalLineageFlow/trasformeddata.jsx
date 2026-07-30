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

// need to add comments and why this file is here and what is the use expain in comments

// The transformer used for hierarchical lineage data.
// Supports both nested stage payloads and flat lineage item payloads.

const determineType = (id) => {
  if (!id) return "Execution";
  const normalized = id.toLowerCase();
  if (normalized.includes("metrics")) return "Metrics";
  if (normalized.includes("model")) return "Stage";
  if (
    normalized.includes("train") ||
    normalized.includes("test") ||
    normalized.includes(".xml") ||
    normalized.includes("dataset") ||
    normalized.includes("input") ||
    normalized.includes("output")
  ) {
    return "Dataset";
  }
  return "Execution";
};

const transformFlatLineageData = (rawJson) => {
  const nodesMap = new Map();
  const links = [];
  const flatItems = rawJson.flat();

  flatItems.forEach((item) => {
    if (!item || !item.id) return;

    const cleanName = item.id.split("/").pop().split(":")[0];
    const type = determineType(item.id);

    if (!nodesMap.has(item.id)) {
      nodesMap.set(item.id, {
        id: item.id,
        name: cleanName,
        type,
        parents: item.parents || [],
      });
    }
  });

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

const transformNestedStageData = (rawJson) => {
  const nodes = [];
  const links = [];

  if (!rawJson?.stages) {
    return { nodes, links };
  }

  const envId = `${rawJson.environment || "env"}`;
  nodes.push({ id: envId, name: rawJson.environment || "Environment", type: "Environment" });

  const addExecutionChildren = (execution, executionId) => {
    if (!Array.isArray(execution.children)) return;

    execution.children.forEach((child) => {
      const childId = child.node_id || child.execution_id || `${executionId}-${child.node_name}`;

      nodes.push({ id: childId, name: child.node_name || child.execution_type || "Node", type: "Node" });
      links.push({ source: executionId, target: childId });

      if (Array.isArray(child.children)) {
        addExecutionChildren(child, childId);
      }
    });
  };

  rawJson.stages.forEach((stage) => {
    const stageId = `stage-${stage.stage_id}`;

    nodes.push({ id: stageId, name: stage.stage_name, type: "Stage" });
    links.push({ source: envId, target: stageId });

    if (Array.isArray(stage.executions)) {
      stage.executions.forEach((exec) => {
        const execId = `exec-${exec.execution_id}`;
        const [execName, execUuidLine] = (exec.execution_type || "Execution").split("\n");

        nodes.push({
          id: execId,
          name: execName || "Execution",
          type: "Execution",
          uuid: "",
          fullUuid: exec.full_uuid || execUuidLine || "",
        });
        links.push({ source: stageId, target: execId });
        addExecutionChildren(exec, execId);
      });
    }
  });

  return { nodes, links };
};

export const transformLineageData = (rawJson) => {
  if (!rawJson) return { nodes: [], links: [] };
  if (rawJson?.nodes && rawJson?.links) return rawJson;
  if (Array.isArray(rawJson)) return transformFlatLineageData(rawJson);
  return transformNestedStageData(rawJson);
};