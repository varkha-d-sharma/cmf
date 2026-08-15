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

import React, { useState } from "react";
import { Handle, Position } from "reactflow";

const getColor = (type) => {
  switch (type) {
    case "Dataset":
      return "#10b981";

    case "Execution":
      return "#3b82f6";

    case "Node":
    case "Metrics":
      return "#ef4444";

    case "Model":
    case "Stage":
      return "#f59e0b";

    case "Environment":
      return "#14b8a6";

    default:
      return "#64748b";
  }
};

const getBadgeLabel = (type) => {
  if (type === "Environment") return "PIPELINE";
  return type ? type.toUpperCase() : "NODE";
};

const HANDLE_HIDDEN_STYLE = {
  opacity: 0,
  width: 1,
  height: 1,
  minWidth: 0,
  minHeight: 0,
  border: "none",
  background: "transparent",
};

const LineageNode = ({ data }) => {
  const [showTooltip, setShowTooltip] = useState(false);
  const { backgroundColor, fullUuid, id, ...rest } = data;
  const tooltipData = { ...rest, uuid: fullUuid || data.uuid };

  const isExecution = data.type === "Execution";
  const targetHandleStyle = isExecution ? HANDLE_HIDDEN_STYLE : undefined;
  const sourceHandleStyle = isExecution ? HANDLE_HIDDEN_STYLE : undefined;

  return (
    <div
      className="lineage-card"
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => setShowTooltip(false)}
      style={{ position: "relative" }}
    >
      <Handle type="target" position={Position.Top} style={targetHandleStyle} />

      <div className="lineage-badge" style={{ backgroundColor: getColor(data.type) }}>
        {getBadgeLabel(data.type)}
      </div>

      <div className="lineage-title" title={data.name}>{data.name}</div>

      {data.uuid && <div className="lineage-subtitle">{data.uuid}</div>}

      {showTooltip && (
        <pre
          className="lineage-tooltip"
          style={{
            maxHeight: "160px",
            maxWidth: "280px",
            overflowY: "auto",
            overflowX: "hidden",
            whiteSpace: "pre-wrap",
            wordBreak: "break-word",
            margin: 0,
          }}
        >
          {JSON.stringify(tooltipData, null, 2)}
        </pre>
      )}

      <Handle type="source" position={Position.Bottom} style={sourceHandleStyle} />
    </div>
  );
};

export default React.memo(LineageNode);