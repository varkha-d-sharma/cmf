define([
	'base/js/namespace',
	'base/js/events'
], function (Jupyter, events) {

	// ==================================================================
	// 1. CMF CLASS CREATION
	// Injects the cmflib import and the Cmf() class instantiation at
	// the top of the notebook (skips if it already exists).
	// ==================================================================
	var cmf_create_class = function () {
		var cells = Jupyter.notebook.get_cells();
		for (var i in cells) {
			if (cells[i].get_text().match("from cmflib import cmf.*")) {
				alert("CMF class creation code already exists in this notebook");
				return;
			}
		}
		var nb_name = Jupyter.notebook.notebook_name.substr(0, Jupyter.notebook.notebook_name.length - 6);
		var cmf_code = '# CMF class creation - update filepath / pipeline_name if needed' + `\n`;
		cmf_code += 'from cmflib import cmf' + `\n`;
		cmf_code += 'metawriter = cmf.Cmf(filepath="' + nb_name + '.mlmd", pipeline_name="' + nb_name + '", custom_properties={}, graph=False, is_server=False)' + `\n`;
		Jupyter.notebook.insert_cell_at_index("code", 0).set_text(cmf_code);
	};

	// ==================================================================
	// 2. CONTEXT & EXECUTION CREATION
	// Prepends create_context / create_execution to the selected cell.
	// Prompts for the pipeline stage and execution type.
	// ==================================================================
	var cmf_inject_exec_data = function () {
		var stageName = prompt("Please provide the pipeline stage", "Evaluate");
		if (stageName == null) {
			return;
		}
		var execType = prompt("Please provide an execution type", "Evaluate-execution");
		if (execType == null) {
			return;
		}
		currText = Jupyter.notebook.get_selected_cell().get_text();
		cmf_code = '# Please update the PIPELINE STAGE & EXECUTION TYPE to match your use case' + `\n`;
		cmf_code += 'context = metawriter.create_context(pipeline_stage="' + stageName + '", custom_properties={})' + `\n`;
		cmf_code += 'execution = metawriter.create_execution(execution_type="' + execType + '", custom_properties={})' + `\n`;
		cmf_code += currText + `\n`;
		Jupyter.notebook.get_selected_cell().set_text(cmf_code);
	};

	// ==================================================================
	// 3. LOG DATASET WITH LABEL
	// Appends a metawriter.log_dataset(...) template (with label and
	// label_properties) to the selected cell.
	// ==================================================================
	var cmf_log_dataset_with_label = function () {
		currText = Jupyter.notebook.get_selected_cell().get_text();
		cmf_code = currText + "# Please update the PATH, EVENT (input/output) and the LABEL details" + `\n`;
		cmf_code += '_ = metawriter.log_dataset(url="PATH_TO_FILE", event="input/output", custom_properties={}, label="LABEL_NAME", label_properties={}, external=False)' + `\n`;
		Jupyter.notebook.get_selected_cell().set_text(cmf_code);
	};

	// ==================================================================
	// 4. LOG METRICS (fine-grained, per step / per epoch)
	// Injects a metawriter.log_metric(...) template meant to be called
	// inside a training loop. Use "Commit metrics" (5) when done.
	// ==================================================================
	var cmf_log_metric = function () {
		cmf_code = '# Fine-grained (per step / per epoch) metric logging. Call this inside your training loop.' + `\n`;
		cmf_code += '# Please update METRICS_NAME and the metric key/values as required' + `\n`;
		cmf_code += 'metawriter.log_metric(metrics_name="METRICS_NAME", custom_properties={"METRIC_KEY": "METRIC_VALUE"})' + `\n`;
		Jupyter.notebook.insert_cell_below('code').set_text(cmf_code);
		Jupyter.notebook.select_next();
	};

	// ==================================================================
	// 5. COMMIT METRICS
	// Injects metawriter.commit_metrics(...) which writes the in-memory
	// metrics (logged via log_metric) to a parquet file and commits it.
	// ==================================================================
	var cmf_commit_metrics = function () {
		cmf_code = '# Commits the metrics logged with log_metric to DVC/Git and stores the artifact in MLMD' + `\n`;
		cmf_code += '# METRICS_NAME must match the name used in log_metric' + `\n`;
		cmf_code += '_ = metawriter.commit_metrics("METRICS_NAME")' + `\n`;
		Jupyter.notebook.insert_cell_below('code').set_text(cmf_code);
		Jupyter.notebook.select_next();
	};

	// ==================================================================
	// 6. LOG MODEL
	// Appends a metawriter.log_model(...) template to the selected cell.
	// ==================================================================
	var cmf_log_model = function () {
		currText = Jupyter.notebook.get_selected_cell().get_text();
		cmf_code = currText + "# Please update the PATH, EVENT, FRAMEWORK, MODEL TYPE & NAME" + `\n`;
		cmf_code += '_ = metawriter.log_model(path="MODEL.pkl", event="input/output", model_framework="FRAMEWORK", model_type="TYPE", model_name="NAME", custom_properties={})' + `\n`;
		Jupyter.notebook.get_selected_cell().set_text(cmf_code);
	};

	// ==================================================================
	// 7. LOG EXECUTION METRICS (coarse-grained, per execution)
	// Injects a sklearn-metrics template ending with
	// metawriter.log_execution_metrics(...).
	// ==================================================================
	var cmf_log_execution_metrics = function () {
		metrics_import = 'import sklearn.metrics as metrics' + `\n`;
		Jupyter.notebook.insert_cell_at_index("code", 0).set_text(metrics_import);
		cmf_code = '# Coarse-grained execution metrics. Please update and edit the below code as required. This is only a template' + `\n`;
		cmf_code += 'avg_prec = metrics.average_precision_score(labels, predictions)' + `\n`;
		cmf_code += 'roc_auc = metrics.roc_auc_score(labels, predictions)' + `\n`;
		cmf_code += 'exec_metrics = dict(avg_prec=avg_prec, roc_auc=roc_auc)' + `\n`;
		cmf_code += '_ = metawriter.log_execution_metrics(metrics_name="metrics", custom_properties=exec_metrics)' + `\n`;
		Jupyter.notebook.insert_cell_below('code').set_text(cmf_code);
	};

	// ==================================================================
	// 8. CMF INIT
	// Injects a cmf.cmf_init(...) template that configures the artifact
	// repository, git remote and CMF server for this workspace.
	// ==================================================================
	var cmf_init = function () {
		var cmf_code = '# CMF init - configures the artifact repo, git remote and CMF server.' + `\n`;
		cmf_code += '# Please update TYPE ("local", "minioS3", "amazonS3", "sshremote", "osdfremote"),' + `\n`;
		cmf_code += '# the paths/URLs below, and add type-specific arguments if needed.' + `\n`;
		cmf_code += 'from cmflib import cmf' + `\n`;
		cmf_code += 'cmf.cmf_init(type="local",' + `\n`;
		cmf_code += '             path="/home/jovyan/dvc_remote",' + `\n`;
		cmf_code += '             git_remote_url="GIT_REMOTE_URL",' + `\n`;
		cmf_code += '             cmf_server_url="http://CMF_SERVER_IP:80")' + `\n`;
		Jupyter.notebook.insert_cell_below('code').set_text(cmf_code);
		Jupyter.notebook.select_next();
	};

	// ==================================================================
	// 9. METADATA PUSH
	// Injects a cmf.metadata_push(...) template that pushes the local
	// mlmd file to the CMF server configured via cmf init.
	// ==================================================================
	var cmf_metadata_push = function () {
		var nb_name = Jupyter.notebook.notebook_name.substr(0, Jupyter.notebook.notebook_name.length - 6);
		var cmf_code = '# Pushes the local metadata (mlmd) file to the CMF server configured with cmf init.' + `\n`;
		cmf_code += '# Please update the pipeline name / file name if they differ.' + `\n`;
		cmf_code += 'from cmflib import cmf' + `\n`;
		cmf_code += 'cmf.metadata_push(pipeline_name="' + nb_name + '", file_name="' + nb_name + '.mlmd")' + `\n`;
		Jupyter.notebook.insert_cell_below('code').set_text(cmf_code);
		Jupyter.notebook.select_next();
	};

	// ==================================================================
	// 10. METADATA PULL
	// Injects a cmf.metadata_pull(...) template that pulls a pipeline's
	// metadata from the CMF server into a local mlmd file.
	// ==================================================================
	var cmf_metadata_pull = function () {
		var nb_name = Jupyter.notebook.notebook_name.substr(0, Jupyter.notebook.notebook_name.length - 6);
		var cmf_code = '# Pulls the pipeline metadata from the CMF server into a local mlmd file.' + `\n`;
		cmf_code += '# Please update the pipeline name / output file name if they differ.' + `\n`;
		cmf_code += 'from cmflib import cmf' + `\n`;
		cmf_code += 'cmf.metadata_pull(pipeline_name="' + nb_name + '", file_name="' + nb_name + '.mlmd")' + `\n`;
		Jupyter.notebook.insert_cell_below('code').set_text(cmf_code);
		Jupyter.notebook.select_next();
	};

	// Run on start
	function load_ipython_extension() {
		console.log("Initiating CMF Extension");
		// Hide cells with tag hide-cell
		cells = Jupyter.notebook.get_cells()
		for (let c in cells) {
			if (cells[c]._metadata.hasOwnProperty("tags") && cells[c]._metadata["tags"].includes("hide-cell")) {
				cells[c].element.find("div.input").hide();
			}
		}

		console.log("Adding CMF toolbar buttons");

		// 1. CMF class creation
		$(Jupyter.toolbar.add_buttons_group([
			Jupyter.keyboard_manager.actions.register({
				help: 'Create CMF class (cmf.Cmf)',
				icon: 'fa-plus-square',
				handler: cmf_create_class
			}, 'Create-CMF-Class', 'Create_CMF_Class')
		])).find('.btn').attr('id', 'Create_CMF_Class');

		// 2. Context & Execution creation
		$(Jupyter.toolbar.add_buttons_group([
			Jupyter.keyboard_manager.actions.register({
				help: 'Create CMF Context & Execution',
				icon: 'fa-code',
				handler: cmf_inject_exec_data
			}, 'Inject-CMF-Code', 'Inject_CMF_Code')
		])).find('.btn').attr('id', 'Inject_CMF_Code');

		// 3. Log dataset with label
		$(Jupyter.toolbar.add_buttons_group([
			Jupyter.keyboard_manager.actions.register({
				help: 'Log dataset with label (log_dataset)',
				icon: 'fa-table',
				handler: cmf_log_dataset_with_label
			}, 'Log-CMF-Dataset-With-Label', 'Log_CMF_Dataset_With_Label')
		])).find('.btn').attr('id', 'Log_CMF_Dataset_With_Label');

		// 4. Log metrics (fine-grained)
		$(Jupyter.toolbar.add_buttons_group([
			Jupyter.keyboard_manager.actions.register({
				help: 'Log per-step metrics (log_metric)',
				icon: 'fa-line-chart',
				handler: cmf_log_metric
			}, 'Log-CMF-Metric', 'Log_CMF_Metric')
		])).find('.btn').attr('id', 'Log_CMF_Metric');

		// 5. Commit metrics
		$(Jupyter.toolbar.add_buttons_group([
			Jupyter.keyboard_manager.actions.register({
				help: 'Commit logged metrics (commit_metrics)',
				icon: 'fa-check-square',
				handler: cmf_commit_metrics
			}, 'Commit-CMF-Metrics', 'Commit_CMF_Metrics')
		])).find('.btn').attr('id', 'Commit_CMF_Metrics');

		// 6. Log model
		$(Jupyter.toolbar.add_buttons_group([
			Jupyter.keyboard_manager.actions.register({
				help: 'Log model (log_model)',
				icon: 'fa-cube',
				handler: cmf_log_model
			}, 'Inject-CMF-model-template', 'Inject_CMF_model_template')
		])).find('.btn').attr('id', 'Inject_CMF_model_template');

		// 7. Log execution metrics (coarse-grained)
		$(Jupyter.toolbar.add_buttons_group([
			Jupyter.keyboard_manager.actions.register({
				help: 'Log execution metrics (log_execution_metrics)',
				icon: 'fa-bar-chart',
				handler: cmf_log_execution_metrics
			}, 'Log-CMF-Execution-Metrics', 'Log_CMF_Execution_Metrics')
		])).find('.btn').attr('id', 'Log_CMF_Execution_Metrics');

		// 8. CMF init
		$(Jupyter.toolbar.add_buttons_group([
			Jupyter.keyboard_manager.actions.register({
				help: 'Initialize CMF (cmf init: artifact repo, git remote & CMF server)',
				icon: 'fa-wrench',
				handler: cmf_init
			}, 'CMF-Init', 'CMF_Init')
		])).find('.btn').attr('id', 'CMF_Init');

		// 9. Metadata push
		$(Jupyter.toolbar.add_buttons_group([
			Jupyter.keyboard_manager.actions.register({
				help: 'Push metadata to CMF server (metadata_push)',
				icon: 'fa-cloud-upload',
				handler: cmf_metadata_push
			}, 'CMF-Metadata-Push', 'CMF_Metadata_Push')
		])).find('.btn').attr('id', 'CMF_Metadata_Push');

		// 10. Metadata pull
		$(Jupyter.toolbar.add_buttons_group([
			Jupyter.keyboard_manager.actions.register({
				help: 'Pull metadata from CMF server (metadata_pull)',
				icon: 'fa-cloud-download',
				handler: cmf_metadata_pull
			}, 'CMF-Metadata-Pull', 'CMF_Metadata_Pull')
		])).find('.btn').attr('id', 'CMF_Metadata_Pull');

	}

	return {
		load_ipython_extension: load_ipython_extension
	};
});
