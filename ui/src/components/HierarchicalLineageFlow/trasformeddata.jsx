export const transformNestedStageData = (rawJson) => {
  const nodes = [];
  const links = [];

  if (!rawJson?.stages) {
    return { nodes, links };
  }

  const envId = `env-${rawJson.environment || "env"}`;

  nodes.push({
    id: envId,
    name: rawJson.environment || "Environment",
    type: "Environment",
  });

  const addExecutionChildren = (execution, executionId) => {
    if (!Array.isArray(execution.children)) return;

    execution.children.forEach((child) => {
      const childId =
        child.node_id ||
        child.execution_id ||
        `${executionId}-${child.node_name}`;

      nodes.push({
        id: childId,
        name:
          child.node_name ||
          child.execution_type ||
          "Node",
        type: "Node",
      });

      links.push({
        source: executionId,
        target: childId,
      });

      // Recursive support
      if (Array.isArray(child.children)) {
        addExecutionChildren(child, childId);
      }
    });
  };

  rawJson.stages.forEach((stage) => {
    const stageId = `stage-${stage.stage_id}`;

    nodes.push({
      id: stageId,
      name: stage.stage_name,
      type: "Stage",
    });

    links.push({
      source: envId,
      target: stageId,
    });

    if (Array.isArray(stage.executions)) {
      stage.executions.forEach((exec) => {
        const execId = `exec-${exec.execution_id}`;

        nodes.push({
          id: execId,
          name: exec.execution_type,
          type: "Execution",
        });

        links.push({
          source: stageId,
          target: execId,
        });

        // ADD CHILD NODES HERE
        addExecutionChildren(exec, execId);
      });
    }
  });

  console.log("Nodes:", nodes.length);
  console.log("Links:", links.length);

  return { nodes, links };
};


export const transformLegacyLineageData = (rawJson) => {
  const originalNodeMap = new Map();
  const links = [];
  
  // CRITICAL: Safe fallback array conversion so .flat() or .forEach() never crashes
  const flatItems = Array.isArray(rawJson) ? rawJson.flat().filter(Boolean) : [];

  const determineType = (id) => {
    if (!id) return "Execution";
    if (id.includes("metrics")) return "Metrics";
    if (id.includes("model")) return "Model";
    if (id.includes("train") || id.includes("test") || id.includes(".xml")) return "Dataset";
    return "Execution";
  };

  flatItems.forEach((item) => {
    if (!item || !item.id) return;
    let cleanName = item.id.split("/").pop().split(":");
    const parents = Array.isArray(item.parents) ? item.parents : [];
    const parentKey = [...parents].sort().join(",") || "ROOT";
    const type = determineType(item.id);

    if (!originalNodeMap.has(item.id)) {
      originalNodeMap.set(item.id, { id: item.id, name: cleanName, type, parentKey, parents });
    }
  });

  const finalNodesMap = new Map();
  const collapsedMapping = new Map();

  originalNodeMap.forEach((node) => {
    if (node.type === "Execution") {
      const stageGroupId = `stage-execution-${node.parentKey}-${node.name}`;
      if (!finalNodesMap.has(stageGroupId)) {
        finalNodesMap.set(stageGroupId, { id: stageGroupId, name: `${node.name} (Parallel Runs)`, type: "Execution", parents: node.parents });
      }
      collapsedMapping.set(node.id, stageGroupId);
    } else {
      finalNodesMap.set(node.id, node);
      collapsedMapping.set(node.id, node.id);
    }
  });

  originalNodeMap.forEach((node) => {
    const targetStageId = collapsedMapping.get(node.id);
    const safeParents = Array.isArray(node.parents) ? node.parents : [];
    safeParents.forEach((parentId) => {
      const sourceStageId = collapsedMapping.get(parentId);
      if (sourceStageId && targetStageId && sourceStageId !== targetStageId) {
        links.push({ source: sourceStageId, target: targetStageId });
      }
    });
  });

  return { nodes: Array.from(finalNodesMap.values()), links };
};

