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


import React, { useEffect, useState } from "react";
import FastAPIClient from "../../client";
import config from "../../config";
import DashboardHeader from "../../components/DashboardHeader";
import Footer from "../../components/Footer";
import LineageSidebar from "../../components/LineageSidebar";
import LineageTypeSidebar from "./LineageTypeSidebar";
import LineageArtifacts from "../../components/LineageArtifacts";
import ExecutionDropdown from "../../components/ExecutionDropdown";
const client = new FastAPIClient(config);

const Lineage = () => {
  const [pipelines, setPipelines] = useState([]);
  const [selectedPipeline, setSelectedPipeline] = useState(null);
  const LineageTypes=['Artifacts','Execution'];
  const [selectedLineageType, setSelectedLineageType] = useState('Artifacts');
  const [selectedExecutionType, setSelectedExecutionType] = useState(null);
  const [lineageData, setLineageData]=useState(null);
  const [executionData, setExecutionData]=useState(null);
  const [lineageArtifactsKey, setLineageArtifactsKey] = useState(0);
  const [execDropdownData,setExecDropdownData] = useState([]);

  // fetching list of pipelines
  useEffect(() => {
    fetchPipelines();
  }, []);

  const fetchPipelines = () => {
    client.getPipelines("").then((data) => {
      setPipelines(data);
      setSelectedPipeline(data[0]);
      // when pipeline is updated we need to update the lineage selection too
      // in my opinion this is also not needed as we have selectedLineage has
      // default value
      if (data[0]) {
        setSelectedLineageType(LineageTypes[0]);
        // call artifact lineage as it is default
        fetchArtifactLineage(data[0]);
      }
    });
  };
  const handlePipelineClick = (pipeline) => {
    setLineageData(null);
    setExecutionData(null); 
    setSelectedPipeline(pipeline);
    // when pipeline is updated we need to update the lineage selection too
    // this is also not needed as selectedLineage has default value
    // setSelectedLineageType(LineageTypes[0]);
     if (selectedPipeline) {
       if (selectedLineageType === "Artifacts") {
          //call artifact lineage as it is default
          fetchArtifactLineage(pipeline);
       }
       else {
          fetchExecutionTypes(pipeline);
       }}
  };

  const handleLineageTypeClick = (lineageType) => {
    setLineageData(null);
    setExecutionData(null);
    setSelectedLineageType(lineageType);
    if (lineageType === "Artifacts") {
      fetchArtifactLineage(selectedPipeline);
    }
    else {
      fetchExecutionTypes(selectedPipeline);
    }
  };  


  const fetchArtifactLineage = (pipelineName) => {
    client.getArtifactLineage(pipelineName).then((data) => {    
        if (data === null) { 
        setLineageData(null);
        }
        setLineageData(data);
    });
    setLineageArtifactsKey((prevKey) => prevKey + 1);
  };

  const fetchExecutionTypes = (pipelineName) => {
    client.getExecutionTypes(pipelineName).then((data) => {    
        if (data === null ) {
           setExecDropdownData(null);
        }
        else {
        setExecDropdownData(data);
        setSelectedExecutionType(data[0]);
        const typeParts = data[0].split('/');
        const exec_type = typeParts[1].split('_')[0];
        const uuid= typeParts[1].split('_').slice(-1)[0];
        fetchExecutionLineage(pipelineName, exec_type,uuid);
        }

    });
    setLineageArtifactsKey((prevKey) => prevKey + 1);
  };

  // used for execution drop down
  const handleExecutionClick = (executionType) => {
    setExecutionData(null);
    setSelectedExecutionType(executionType);
    const typeParts = executionType.split('/');
    const type = typeParts[1].split('_')[0];
    const uuid= typeParts[1].split('_').slice(-1)[0];
    fetchExecutionLineage(selectedPipeline, type,uuid);
  };  

  const fetchExecutionLineage = (pipelineName, type,uuid) => {
    client.getExecutionLineage(pipelineName,type,uuid).then((data) => {    
      if (data === null) {
          setExecutionData(null);
      }
      setExecutionData(data);
    });
  };

  return (
    <>
      <section
        className="flex flex-col bg-white"
        style={{ minHeight: "100vh" }}
      >
        <DashboardHeader />

        <div className="container">
          <div className="flex flex-row">
            <LineageSidebar
              pipelines={pipelines}
              handlePipelineClick={handlePipelineClick}
            />
          <div className="container justify-center items-center mx-auto px-4">
            <div className="flex flex-col">
             {selectedPipeline !== null && (
                <LineageTypeSidebar
                  LineageTypes={LineageTypes}
                  handleLineageTypeClick= {handleLineageTypeClick}
                />
             )}
            </div>
            <div className="container">
                {selectedPipeline !== null && selectedLineageType === "Artifacts" && lineageData !== null && (
                <LineageArtifacts key={lineageArtifactsKey}  data={lineageData}/>
              )}
                {selectedPipeline !== null && selectedLineageType === "Execution" && execDropdownData !== null  && executionData !== null &&(
                <div>
                <ExecutionDropdown data={execDropdownData} exec_type={selectedExecutionType} handleExecutionClick= {handleExecutionClick}/>        
                </div>
                )}
                {selectedPipeline !== null && selectedLineageType === "Execution" && execDropdownData !== null  && executionData !== null &&(
                <div>
                <LineageArtifacts key={lineageArtifactsKey} data={executionData} />
                </div>
                )}
            </div>
          </div>
        </div>
       </div>
        <Footer />
      </section>
    </>
  );
};

export default Lineage;
