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

//ExecutionTable.jsx
import React, { useState, useEffect } from "react";
import "./index.module.css";

const ExecutionPsTable = ({ executions, onSort, onFilter }) => {
  // Default sorting order
  const [sortOrder, setSortOrder] = useState(onSort);
  const [sortedData, setSortedData] = useState([]);
  // Local filter value state
  const [filterValue, setFilterValue] = useState("");
  const [expandedRow, setExpandedRow] = useState(null);

  const consistentColumns = [];

  useEffect(() => {
    // Set initial sorting order when component mounts
    setSortedData([...executions]);
  }, [executions]);

  const handleSort = () => {
    const newSortOrder =
      sortOrder === "desc" ? "asc" : sortOrder === "asc" ? "desc" : "asc";
    setSortOrder(newSortOrder);
    const sorted = [...executions].sort((a, b) => {
      if (newSortOrder === "asc") {
        return a.Context_Type.localeCompare(b.Context_Type);
      } else {
        return b.Context_Type.localeCompare(a.Context_Type);
      }
    });
    setSortedData(sorted); // Notify parent component about sorting change
  };

  const handleFilterChange = (event) => {
    const value = event.target.value;
    setFilterValue(value);
    onFilter(value); // Notify parent component about filter change
  };

  const toggleRow = (rowId) => {
    if (expandedRow === rowId) {
      setExpandedRow(null);
    } else {
      setExpandedRow(rowId);
    }
  };

  const getPropertyValue = (properties, propertyName) => {
    if (typeof properties === "string") {
        try {
            properties = JSON.parse(properties);  // Parse the string to an array
        } catch (e) {
            console.error("Failed to parse properties:", e);
            return "N/A";  // Return "N/A" if parsing fails
        }
    }

    // Ensure properties is now an array
    if (!Array.isArray(properties)) {
        console.warn("Expected an array for properties, got:", properties);
        return "N/A";
    }

    // Filter the properties by name and extract string_value
    const values = properties
      .filter(prop => prop.name === propertyName)  // Filter properties by name
      .map(prop => prop.value);  // Extract string_value

    // // Return the values as a comma-separated string or "N/A" if no values are found
    return values.length > 0 ? values.join(", ") : "N/A";
  };

  const renderArrow = () => {
    if (sortOrder === "desc") {
      return (
        <span
          className="text-2xl cursor-pointer"
          style={{ marginLeft: "4px", display: "inline-flex" }}
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="16"
            height="16"
            fill="currentColor"
            class="bi bi-arrow-down"
            viewBox="0 0 16 16"
          >
            <path
              fill-rule="evenodd"
              d="M8 1a.5.5 0 0 1 .5.5v11.793l3.146-3.147a.5.5 0 0 1 .708.708l-4 4a.5.5 0 0 1-.708 0l-4-4a.5.5 0 0 1 .708-.708L7.5 13.293V1.5A.5.5 0 0 1 8 1"
            />
          </svg>
        </span>
      ); //data is in desc order ---> ↓
    } else if (sortOrder === "asc") {
      return (
        <span
          className="text-2xl cursor-pointer"
          style={{ marginLeft: "4px", display: "inline-flex" }}
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="16"
            height="16"
            fill="currentColor"
            class="bi bi-arrow-up"
            viewBox="0 0 16 16"
          >
            <path
              fill-rule="evenodd"
              d="M8 15a.5.5 0 0 0 .5-.5V2.707l3.146 3.147a.5.5 0 0 0 .708-.708l-4-4a.5.5 0 0 0-.708 0l-4 4a.5.5 0 1 0 .708.708L7.5 2.707V14.5a.5.5 0 0 0 .5.5"
            />
          </svg>
        </span>
      ); //data is in asc order ----> ↑
    } else {
      return (
        <span
          className="text-2xl cursor-pointer"
          style={{ marginLeft: "4px", display: "inline-flex" }}
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="16"
            height="16"
            fill="currentColor"
            class="bi bi-arrow-down-up"
            viewBox="0 0 16 16"
          >
            <path
              fill-rule="evenodd"
              d="M11.5 15a.5.5 0 0 0 .5-.5V2.707l3.146 3.147a.5.5 0 0 0 .708-.708l-4-4a.5.5 0 0 0-.708 0l-4 4a.5.5 0 1 0 .708.708L11 2.707V14.5a.5.5 0 0 0 .5.5m-7-14a.5.5 0 0 1 .5.5v11.793l3.146-3.147a.5.5 0 0 1 .708.708l-4 4a.5.5 0 0 1-.708 0l-4-4a.5.5 0 0 1 .708-.708L4 13.293V1.5a.5.5 0 0 1 .5-.5"
            />
          </svg>
        </span>
      ); //data is in initial order -----------> ↓↑
    }
  };

  return (
    <div className="flex flex-col">
      <div
        style={{
          display: "flex",
          justifyContent: "flex-end",
          marginBottom: "0.5rem",
          marginTop: "0.5rem",
        }}
      >
        <input
          type="text"
          value={filterValue}
          onChange={handleFilterChange}
          placeholder="Filter by Context Type/Properties"
          style={{
            marginRight: "1rem",
            padding: "0.5rem",
            border: "1px solid #ccc",
          }}
        />
      </div>
      <div className="overflow-x-auto">
        <div className="p-1.5 w-full inline-block align-middle">
          <table className="min-w-full divide-y divide-gray-200" id="mytable">
            <thead>
              <tr className="text-xs font-bold text-left text-black uppercase">
                <th scope="col" className="px-6 py-3"></th>
                <th
                  scope="col"
                  onClick={handleSort}
                  className="px-6 py-3 Context_Type"
                >
                  <span style={{ display: 'inline-flex', alignItems: 'center' }}>
                    Context Type {renderArrow()}
                  </span>
                </th>
                <th scope="col" className="px-6 py-3 Execution">
                  Execution
                </th>
                <th scope="col" className="px-6 py-3 Git_Repo">
                  Git Repo
                </th>
                <th scope="col" className="px-6 py-3 Git_Start_Commit">
                  Git Start Commit
                </th>
                <th scope="col" className="px-6 py-3 Pipeline_Type">
                  Pipeline Type
                </th>
              </tr>
            </thead>
            <tbody className="body divide-y divide-gray-200">
              {sortedData.map((data, index) => (
                <React.Fragment key={index}>
                  <tr
                    key={index}
                    onClick={() => toggleRow(index)}
                    className="text-sm font-medium text-gray-800"
                  >
                    <td className="px-6 py-4 cursor-pointer">
                      {expandedRow === index ? "-" : "+"}
                    </td>
                    <td className="px-6 py-4">{getPropertyValue(data.execution_properties, "Context_Type")}</td>
                    <td className="px-6 py-4">{getPropertyValue(data.execution_properties, "Execution")}</td>
                    <td className="px-6 py-4">{getPropertyValue(data.execution_properties, "Git_Repo")}</td>
                    <td className="px-6 py-4">{getPropertyValue(data.execution_properties, "Git_Start_Commit")}</td>
                    <td className="px-6 py-4">{getPropertyValue(data.execution_properties, "Pipeline_Type")}</td>
                  </tr>
                  {expandedRow === index && (
                    <tr>
                      <td colSpan="4">
                        <table className="expanded-table">
                        <tbody>
                        {JSON.parse(data.execution_properties).map((property, idx) => (
                          <tr key={idx}>
                            <td>{property.name}</td>
                            <td>{property.value}</td>
                          </tr>
                        ))}
                        </tbody>
                        </table>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default ExecutionPsTable;