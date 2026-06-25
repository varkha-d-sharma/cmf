export const transformPipelineData = (rawData) => {
  const nodes = [];
  const links = [];

  const nodeMap = new Map();

  const addNode = (node) => {
    if (!nodeMap.has(node.id)) {
      nodeMap.set(node.id, node);
      nodes.push(node);
    }
  };

  const addLink = (source, target) => {
    links.push({
      source,
      target,
    });
  };

  const processExecution = (execution, parentId) => {
    const execId =
      execution.execution_id ||
      `${parentId}-${execution.execution_type}`;

    addNode({
      id: execId,
      name: execution.execution_type || execution.type,
      type: "Execution",
    });

    console.log("...execution.execution_type",execution.execution_type,"execution.children",execution.children);

    addLink(parentId, execId);

    // Process Artifacts
    if (Array.isArray(execution.events)) {
      execution.events.forEach((event) => {
        if (!event.artifact) return;

        const artifact = event.artifact;

        const artifactId = String(artifact.id);

        const cleanName =
          artifact.name
            ?.split("/")
            .pop()
            ?.split(":")[0] || artifact.name;

        addNode({
          id: artifactId,
          name: cleanName,
          type: artifact.type || "Artifact",
          owner: artifact.properties?.git_repo,
          uri: artifact.uri,
        });

        addLink(execId, artifactId);
      });
    }

    // Process Child Executions
    if (Array.isArray(execution.children)) {
      execution.children.forEach((childExecution) => {
        processExecution(childExecution, execId);
      });
    }
  };

  if (!rawData?.Pipeline) {
    return {
      nodes: [],
      links: [],
    };
  }

  rawData.Pipeline.forEach((pipeline, pIndex) => {
    const pipelineId = `pipeline-${pIndex}`;

    addNode({
      id: pipelineId,
      name: pipeline.name || "Pipeline",
      type: "Pipeline",
    });

    if (!Array.isArray(pipeline.stages)) return;

    pipeline.stages.forEach((stage, sIndex) => {
      const stageId =
        stage.stage_id ||
        `${pipelineId}-stage-${sIndex}`;

      addNode({
        id: stageId,
        name:
          stage.stage_name ||
          stage.name ||
          `Stage ${sIndex + 1}`,
        type: "Stage",
      });

      addLink(pipelineId, stageId);

      if (!Array.isArray(stage.executions)) return;

      stage.executions.forEach((execution) => {
        processExecution(execution, stageId);
      });
    });
  });

  return {
    nodes,
    links,
  };
};
