#!/bin/bash
set -euo pipefail
export PATH="/opt/conda/bin:$PATH"
mkdir -p /home/jovyan/workspace
cd /home/jovyan/workspace
if [ ! -e .git ]; then
    bash /home/jovyan/example-get-started/initialize.sh
fi
exec /opt/conda/bin/jupyter notebook --ip 0.0.0.0 --port 8899 --no-browser --allow-root