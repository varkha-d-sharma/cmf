#Change as necessary: https://jupyter-docker-stacks.readthedocs.io/en/latest/using/selecting.html
#FROM jupyter/datascience-notebook
FROM jupyter/tensorflow-notebook
#FROM jupyter/all-spark-notebook
#FROM jupyter/pyspark-notebook

#FROM nvcr.io/nvidia/tensorflow:21.02-tf1-py3
#FROM nvcr.io/nvidia/pytorch:21.02-py3
#FROM nvcr.io/nvidia/mxnet:21.02-py3
#FROM nvcr.io/nvidia/theano:18.08
#FROM nvcr.io/partners/paddlepaddle:0.11-alpha
#FROM nvcr.io/partners/chainer:4.0.0b1

#Following: https://jupyter-docker-stacks.readthedocs.io/en/latest/using/recipes.html#
ARG NB_USER 
ARG NB_UID
ARG NB_GID
ENV http_proxy http://web-proxy.labs.hpecorp.net:8080
ENV https_proxy http://web-proxy.labs.hpecorp.net:8080
RUN "${CONDA_DIR}/bin/python" -c 'import sys; assert (3, 9) <= sys.version_info[:2] < (3, 12), "CMF requires Python 3.9-3.11"'

USER ${NB_USER}

RUN mkdir -p "/home/${NB_USER}/cmflib"

COPY --chown=${NB_UID}:${NB_GID} pyproject.toml setup.py setup.cfg README.md /home/${NB_USER}/cmflib/
COPY --chown=${NB_UID}:${NB_GID} cmflib/ /home/${NB_USER}/cmflib/cmflib/
RUN "${CONDA_DIR}/bin/python" -m pip install --no-cache-dir /home/${NB_USER}/cmflib && \
    fix-permissions "${CONDA_DIR}" && \
    fix-permissions "/home/${NB_USER}"

COPY --chown=${NB_UID}:${NB_GID} examples/example-get-started /home/${NB_USER}/example-get-started

RUN "${CONDA_DIR}/bin/python" -m pip install --no-cache-dir 'notebook<7' 'jupyter-server<2' jupyter_contrib_nbextensions && \
    "${CONDA_DIR}/bin/jupyter" contrib nbextensions install --sys-prefix
COPY --chown=${NB_UID}:${NB_GID} jupyter-plugin/CMF_plugin /home/${NB_USER}/CMF_plugin
RUN "${CONDA_DIR}/bin/jupyter" nbextension install --sys-prefix --overwrite /home/${NB_USER}/CMF_plugin && \
    "${CONDA_DIR}/bin/jupyter" nbextension enable --sys-prefix CMF_plugin/main

COPY --chown=${NB_UID}:${NB_GID} jupyter-plugin/runJupyter.sh /home/${NB_USER}/runJupyter.sh
RUN chmod +x /home/${NB_USER}/runJupyter.sh
ENTRYPOINT ["bash","/home/jovyan/runJupyter.sh"]
