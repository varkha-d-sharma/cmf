# CMF Jupyter Extension

Adds toolbar buttons to the classic Jupyter Notebook that insert
Common Metadata Framework (CMF) code templates into notebook cells.
The buttons insert editable templates only; review and complete the
code before running it.

## Toolbar buttons

| Button | Inserts |
|---|---|
| Create CMF class | `from cmflib import cmf` and a `cmf.Cmf(...)` instance at the top of the notebook |
| Create Context & Execution | `create_context` / `create_execution` calls (prompts for stage and execution type) |
| Log dataset with label | A `log_dataset(...)` template appended to the selected cell |
| Log metrics | A per-step `log_metric(...)` template for training loops |
| Commit metrics | A `commit_metrics(...)` call that stores logged metrics |
| Log model | A `log_model(...)` template appended to the selected cell |
| Log execution metrics | A sklearn metrics + `log_execution_metrics(...)` template |
| CMF init | A `cmf.cmf_init(...)` template to configure the artifact repo and CMF server |
| Metadata push | A `cmf.metadata_push(...)` template to send the local mlmd file to the CMF server |
| Metadata pull | A `cmf.metadata_pull(...)` template to fetch pipeline metadata from the CMF server |

See the full setup guide in `jupyter-plugin/readme.md` of the CMF
repository.
