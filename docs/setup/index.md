# CMF Installation & Setup Guide

This guide provides step-by-step instructions for installing, configuring, and using CMF (Common Metadata Framework) for ML pipeline metadata tracking.

## Overview

The installation process consists of the following components:

1. **[cmflib with CMF Client Installation](#install-cmf-library-ie-cmflib)**: A Python library that captures and tracks metadata throughout your ML pipeline, including datasets, models, and metrics.
2. **[CMF Server with GUI Installation](#install-cmf-server-with-gui)**: A centralized server that aggregates metadata from multiple clients and provides a web-based graphical interface for visualizing pipeline executions, artifacts, and lineage relationships.

> **Note:** Every CMF setup requires a CMF Server instance. In collaborative environments, multiple users working on the same project can share a single CMF Server to centralize metadata and facilitate team coordination.

---

# CMF Installation

This hub connects you to the deployment procedures for the Common Metadata Framework (CMF). CMF separates metadata collection from visualization, requiring two distinct installation tracks depending on your user role.

## Component Overview

* **[CMF Client (cmflib)](./client_side_installation.md)**: A lightweight Python library integrated into ML scripts to capture pipeline, dataset, and model metadata.
* **[CMF Server & GUI](./server_side_installation.md)**: A centralized backend infrastructure that aggregates metadata from clients and hosts the web dashboard.

!!! info "Deployment Topology"
    Every operational CMF environment requires exactly one active CMF Server instance. In collaborative environments, multiple data scientists share a single centralized server to collaborate on pipeline lineages.

---

## Shared Baseline Prerequisites

Ensure your target deployment nodes meet these foundational system constraints before selecting an installation track:

* **Operating System**: Linux (Ubuntu/Debian distributions strictly validated).
* **Python Engine**: Runtime versions 3.9 to 3.11 are supported.
* **Recommended Runtime**: Python 3.10 is optimized to prevent environment edge cases.

---

## Choose Deployment Track

Select the guide below that corresponds to your environment configuration goals:

### Track 1: Pipeline Nodes (Data Scientists / Developers)
* **Goal**: Enable ML scripts to track and push metadata.
* **Artifacts**: Installs `cmflib` and sets up tracking storage backends.
* **Link**: Proceed to the **[CMF Client Installation Guide](./client_side_installation.md)**.

### Track 2: Infrastructure Host (DevOps / System Administrators)
* **Goal**: Launch the central tracking database, API layer, and frontend UI.
* **Artifacts**: Deploys containerized PostgreSQL, Nginx, TensorBoard, and CMF API.
* **Link**: Proceed to the **[CMF Server Installation Guide](./server_side_installation.md)**.

# CLI Execution Reference
Before initiating the environment setup, review the foundational commands required to deploy the client.

!!! warning "Important Note"
    * The following initial steps are basic and mandatory prerequisites for both server-side and client-side installations. You must execute these core commands sequentially to prepare your environment.
<br />

**Note:** First, at the root directory, execute the ls command to check the existing workspace folder structure.<br />

**Step 1: List Directory Contents**<br/><br/>
**Description:** ls command to check the existing workspace folder structure<br/>
```bash
 $ ls
```
**Output:** Demo,  cmf_env,  cmf_workspace 
<br>

---

**Step 2: Check Installed Python Version**<br/><br/>
**Description**: Next, check the Python version at the root directory to confirm the environment meets CMF runtime constraints.<br/>

```bash
$ python --version
```
**Output:** Python 3.10.20 <br/>
If you have python version greater then 3.10 use below commands:
    <br>
    ```bash
    sudo apt update
    sudo apt install -y python3.10 python3.10-venv python3-pip
    ```

- **Python:** Version 3.9 to 3.11 (3.10 recommended)

    > **Note:** If you encounter issues with Python 3.9 on Ubuntu, refer to the [Troubleshooting](#troubleshooting) section at the end of this guide.

---

**Step 3: Create a Virtual Environment**<br/><br/>
**Description:** Create an isolated, self-contained Python virtual environment named cmf_env dedicated exclusively to CMF dependencies to prevent dependency pollution.<br/>

```bash
$  python3.10 -m venv cmf_env
```
**Output:** The command will run silently and output absolutely nothing to the terminal. It simply creates the cmf_env folder.

---

**Step 4: Activate the Virtual Environment**<br/><br/>
**Description:** Activate the virtual environment to configure your path variables so all subsequent python and pip binaries resolve strictly inside this sandbox.<br/>

```bash
$  source cmf_env/bin/activate
```
**Output:** (cmf_env)$
<br>
Activate the virtual environment

---

**Step 5: Install the CMF Library**<br/><br/>
**Description:** Install the core cmflib client package to expose the framework APIs required to track ML workflows and push metadata streams.<br/>

```bash
$  pip install cmflib
```
**Output:**
    new release of pip is available: 23.0.1<br />
    26.1.1 To update, run: pip install --upgrade pip
---
