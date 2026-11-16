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
	// The selected cell must carry a tag denoting the pipeline stage.
	// ==================================================================
	var cmf_inject_exec_data = function () {
		tags = Jupyter.notebook.get_selected_cell()._metadata.tags;
		try {
			if (tags.length >= 1) {
				currText = Jupyter.notebook.get_selected_cell().get_text();
				cmf_code = '# Please update the PIPELINE STAGE & EXECUTION TYPE to match your use case' + `\n`;
				cmf_code += 'context = metawriter.create_context(pipeline_stage="' + tags[0] + '", custom_properties={})' + `\n`;
				var execType = prompt("Please provide an execution type", "Evaluate-execution");
				cmf_code += 'execution = metawriter.create_execution(execution_type="' + execType + '", custom_properties={})' + `\n`;
				cmf_code += currText + `\n`;
				Jupyter.notebook.get_selected_cell().set_text(cmf_code);
			}
			else {
				console.log("Cell needs a tag");
				alert("Cell needs a tag");
			}
		}
		catch (err) {
			alert("Cell needs a tag");
			console.log(err)
		}
	};

	// ==================================================================
	// 3. LOAD DATASET FROM A DATA STORE
	// Fetches the available data sources from the remote API server and
	// renders a dropdown; selecting one injects its connection code.
	// ==================================================================
	var get_data_sources = function () {
		console.log("Getting Data sources")
		console.log(api_base_url)
		if (api_base_url == '') {
			alert("Please provide the Base URL for Data source API calls")
		}
		else {
			fetch(api_base_url + '/get_all_datasources').then(response => response.json()).then(response => {
				let res = response["list"];
				let optionList = "";
				for (let x of res) {
					optionList += "<option>" + x + "</option>";
				}
				let htmlCode = '';
				htmlCode += '%%HTML\n';
				htmlCode += '\
						<form id="frm">\
							<label for="dataSet">Select DataSet:</label>\
							<select class="dataSet form-select" aria-label="Default select example">\
								<option selected>Select DataSet</option>\
								'+ optionList + '\
							</select>\
							<input type="submit" value="Submit">\
						</form>\
						<br><br>\
						<script>\
					\
						$("#frm").submit(function(event) {\
						event.preventDefault();\
						});\
						$(".dataSet").change(function() {\
							console.log($(this).val());\
							fetch("'+ api_base_url + '/get_datasource_connection/"+$(this).val()).then(response2 => response2.text()).then(response2 => {\
								console.log("----------------");\
								response2 = JSON.parse(response2);\
								console.log(response2);\
								let optionlist2 = "";\
								for (let x of response2["connection_string"]) {\
									optionlist2 += x +`\n`\
								}\
								Jupyter.notebook.insert_cell_below("code").set_text(optionlist2);\
								idx = Jupyter.notebook.get_selected_index();\
								Jupyter.notebook.select(idx + 1);\
								console.log("----------------");\
							 });\
						  });\
						</script>';
				Jupyter.notebook.insert_cell_below('code').set_text(htmlCode);
				cell_index = Jupyter.notebook.get_selected_index();
				Jupyter.notebook.select(cell_index + 1);
				next_cell = Jupyter.notebook.get_cell(cell_index + 1);
				next_cell.execute();
				if (next_cell._metadata.hasOwnProperty("tags")) {
					existing_tags = [...next_cell._metadata["tags"]];
					existing_tags.push("hide-cell");
				}
				else {
					next_cell._metadata["tags"] = ["hide-cell"]
				}
				next_cell.element.find("div.input").hide();
			});
		}
	};

	// ==================================================================
	// 4. LOG DATASET WITH LABEL
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
	// 5. LOG METRICS (fine-grained, per step / per epoch)
	// Injects a metawriter.log_metric(...) template meant to be called
	// inside a training loop. Use "Commit metrics" (6) when done.
	// ==================================================================
	var cmf_log_metric = function () {
		cmf_code = '# Fine-grained (per step / per epoch) metric logging. Call this inside your training loop.' + `\n`;
		cmf_code += '# Please update METRICS_NAME and the metric key/values as required' + `\n`;
		cmf_code += 'metawriter.log_metric(metrics_name="METRICS_NAME", custom_properties={"METRIC_KEY": "METRIC_VALUE"})' + `\n`;
		Jupyter.notebook.insert_cell_below('code').set_text(cmf_code);
		Jupyter.notebook.select_next();
	};

	// ==================================================================
	// 6. COMMIT METRICS
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
	// 7. LOG MODEL
	// Appends a metawriter.log_model(...) template to the selected cell.
	// ==================================================================
	var cmf_log_model = function () {
		currText = Jupyter.notebook.get_selected_cell().get_text();
		cmf_code = currText + "# Please update the PATH, EVENT, FRAMEWORK, MODEL TYPE & NAME" + `\n`;
		cmf_code += '_ = metawriter.log_model(path="MODEL.pkl", event="input/output", model_framework="FRAMEWORK", model_type="TYPE", model_name="NAME", custom_properties={})' + `\n`;
		Jupyter.notebook.get_selected_cell().set_text(cmf_code);
	};

	// ==================================================================
	// 8. LOG EXECUTION METRICS (coarse-grained, per execution)
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
	// UNUSED CODE (kept for reference, commented out)
	// ==================================================================

	// UNUSED: HTML-form based variant of context & execution creation
	// var cmf_inject_exec_data_html = function () {
	// 	htmlCode = "%%HTML\n";
	// 	htmlCode += '\
	// 	  <script>\
	// 		function cmf_inject_exec_data() {;\n\
	// 			Jupyter.notebook.insert_cell_below("code").set_text("");\n\
	// 			cell_index = Jupyter.notebook.get_selected_index();\n\
	// 			Jupyter.notebook.select(cell_index + 1);\n\
	// 			next_cell = Jupyter.notebook.get_cell(cell_index + 1);\n\
	// 			currText = ""\n\
	// 			cmf_code = "# Please update the PIPELINE STAGE & EXECUTION TYPE to match your use case if needed\\n";\n\
	// 			var stageName = document.getElementById("html_id_stage").value;\n\
	// 			cmf_code += `context = metawriter.create_context(pipeline_stage="` + stageName +`")\\n`;\n\
	// 			var execType = document.getElementById("html_id_exec_type").value;\n\
	// 			cmf_code += `execution = metawriter.create_execution(execution_type="` + execType +`")\\n`;\n\
	// 			cmf_code += currText;\n\
	// 			cmf_code += "#Please choose the button/option to insert the CMF Cell Set";\n\
	// 			next_cell.set_text(cmf_code);\n\
	// 			next_cell._metadata["tags"] = ["STAGE-DEF-CELL", stageName];\
	// 		};\n\
	// 	  </script>\n\
	// 	  <label>Stage:</label>\n\
	// 	  <input type="text" id="html_id_stage">\n\
	// 	  <label>Execution Type:</label>\n\
	// 	  <input type="text" id="html_id_exec_type">\n\
	// 	  <input type="button" value="Submit" onclick="cmf_inject_exec_data()">\
	// 	  '
	// 	Jupyter.notebook.insert_cell_below('code').set_text(htmlCode);
	// 	cell_index = Jupyter.notebook.get_selected_index();
	// 	Jupyter.notebook.select(cell_index + 1);
	// 	next_cell = Jupyter.notebook.get_cell(cell_index + 1);
	// 	next_cell.execute();
	// 	next_cell._metadata["tags"] = ["hide-cell"]
	// 	next_cell.element.find("div.input").hide();
	// };

	// UNUSED: creates a set of stage/input/processing/output cells
	// var cmf_stage_inject = function () {
	// 	console.log("Stage inject")
	// 	//Insert stage cell
	// 	cmf_inject_exec_data();
	// 	Jupyter.notebook.select_next();
	// 	curr_code = Jupyter.notebook.get_selected_cell().get_text() + `\n`;
	// 	curr_code += "Please save and reload the notebook to enable tag visibility"
	// 	c1_tags = Jupyter.notebook.get_selected_cell()._metadata["tags"];
	//
	// 	//Insert Inputs cell
	// 	Jupyter.notebook.insert_cell_below('code');
	// 	Jupyter.notebook.select_next();
	// 	c2_tags = [...c1_tags];
	// 	c2_tags.push("input");
	// 	Jupyter.notebook.get_selected_cell()._metadata["tags"] = c2_tags;
	// 	cmf_code = "# Designated Input Cell. Please add your input statements here and then choose the log data set option" + `\n\n`;
	// 	Jupyter.notebook.get_selected_cell().set_text(cmf_code)
	//
	// 	console.log("Stage inject mid");
	//
	// 	//Insert Processing cell
	// 	Jupyter.notebook.insert_cell_below('code');
	// 	Jupyter.notebook.select_next();
	// 	c3_tags = [...c1_tags];
	// 	c3_tags.push("processing");
	// 	Jupyter.notebook.get_selected_cell()._metadata["tags"] = c3_tags;
	// 	cmf_code = "# Designated Processing/Transformation cell. Please use this space to write your transformation logic" + `\n\n`;
	// 	Jupyter.notebook.get_selected_cell().set_text(cmf_code)
	//
	// 	//Insert Output cell
	// 	Jupyter.notebook.insert_cell_below('code');
	// 	Jupyter.notebook.select_next();
	// 	c4_tags = [...c1_tags];
	// 	c4_tags.push("output");
	// 	Jupyter.notebook.get_selected_cell()._metadata["tags"] = c4_tags;
	// 	cmf_code = "# Designated output cell. Please use this space to output to file or model and choose the log dataset or model option" + `\n\n`;
	// 	Jupyter.notebook.get_selected_cell().set_text(cmf_code)
	// };

	// UNUSED: auto-detects dataset file reads/writes in the selected cell
	// var cmf_inject_dataset = function () {
	// 	code = Jupyter.notebook.get_selected_cell().get_text().split('\n')
	// 	ext_list = ["csv", "json", "xml", "orc", "parquet", "gpkg"]
	// 	code_new = []
	// 	for (i in code) {
	// 		for (j in ext_list) {
	// 			if (code[i].match(ext_list[j])) {
	// 				regex_val = '".*' + ext_list[j] + '"'
	// 				setType = "output";
	// 				if (code[i].match("read")) {
	// 					setType = "input";
	// 				}
	// 				code_new.push('metawriter.log_dataset(' + code[i].match(regex_val)[0] + ', "' + setType + '")')
	// 			}
	// 		}
	// 	}
	// 	finalCode = code.concat(code_new)
	// 	console.log(finalCode)
	// 	fin = ""
	// 	for (let x of finalCode) {
	// 		fin += x + `\n`
	// 	}
	// 	console.log(fin)
	// 	Jupyter.notebook.get_selected_cell().set_text(fin)
	// };

	// UNUSED: sends the mlmd file over a kafka pipeline to CMF
	// var inject_shadow_pipeline = function () {
	// 	cells = Jupyter.notebook.get_cells();
	// 	mlmd_path = "";
	// 	json_path = "";
	// 	reg = /(?:filepath|filename)=\"(.*mlmd)\".*/;
	// 	for (let c in cells) {
	// 		if (cells[c].get_text().match(reg)) {
	// 			mlmd_path = cells[c].get_text().match(reg)[1];
	// 			json_path = mlmd_path.substr(0, mlmd_path.length - 5) + ".json";
	// 		}
	// 	}
	// 	cmf_code = '# This code is meant to send the mlmd file over a kafka pipeline to CMF' + `\n`;
	// 	cmf_code += 'import sys' + `\n`;
	// 	cmf_code += 'sys.path.insert(0, "./mlmdToJson")' + `\n`;
	// 	cmf_code += 'import mlmd2json' + `\n`;
	// 	cmf_code += 'cmf_data = mlmd2json.process_json(path="' + mlmd_path + '",json_path = "' + json_path + '")' + `\n`;
	// 	cmf_code += 'from kafka import KafkaProducer, errors' + `\n`;
	// 	cmf_code += 'try:' + `\n`;
	// 	cmf_code += '    producer = KafkaProducer(bootstrap_servers="10.93.246.17:9092",value_serializer=lambda x: dumps(x).encode("utf-8"),key_serializer=lambda x:x.encode("utf-8"))' + `\n`;
	// 	cmf_code += '    producer.send(topic = "jupy_cmf", value=cmf_data, key="' + mlmd_path.substr(0, mlmd_path.length - 5) + '")' + `\n`;
	// 	cmf_code += '    producer.flush()' + `\n`;
	// 	cmf_code += 'except (errors.NoBrokersAvailable, errors.UnrecognizedBrokerVersion) as ex:' + `\n`;
	// 	cmf_code += '    pass' + `\n`;
	// 	Jupyter.notebook.insert_cell_below('code').set_text(cmf_code);
	// };

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

		var config = Jupyter.notebook.config;
		if (config.data.hasOwnProperty("auth_token") && config.data["auth_token"] != '') {
			auth_token = config.data["auth_token"];
		}
		else {
			alert("Authentication Key is required.");
		}
		if (config.data.hasOwnProperty("api_base_url")) {
			api_base_url = config.data["api_base_url"];
			console.log("api URL", api_base_url);
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
				help: 'Create CMF Context & Execution (cell needs a stage tag)',
				icon: 'fa-code',
				handler: cmf_inject_exec_data
			}, 'Inject-CMF-Code', 'Inject_CMF_Code')
		])).find('.btn').attr('id', 'Inject_CMF_Code');

		// 3. Load dataset from a data store
		$(Jupyter.toolbar.add_buttons_group([
			Jupyter.keyboard_manager.actions.register({
				help: 'Load dataset from a data store',
				icon: 'fa-database',
				handler: get_data_sources
			}, 'Get-data-sources', 'Get_data_sources')
		])).find('.btn').attr('id', 'Get_data_sources');

		// 4. Log dataset with label
		$(Jupyter.toolbar.add_buttons_group([
			Jupyter.keyboard_manager.actions.register({
				help: 'Log dataset with label (log_dataset)',
				icon: 'fa-table',
				handler: cmf_log_dataset_with_label
			}, 'Log-CMF-Dataset-With-Label', 'Log_CMF_Dataset_With_Label')
		])).find('.btn').attr('id', 'Log_CMF_Dataset_With_Label');

		// 5. Log metrics (fine-grained)
		$(Jupyter.toolbar.add_buttons_group([
			Jupyter.keyboard_manager.actions.register({
				help: 'Log per-step metrics (log_metric)',
				icon: 'fa-line-chart',
				handler: cmf_log_metric
			}, 'Log-CMF-Metric', 'Log_CMF_Metric')
		])).find('.btn').attr('id', 'Log_CMF_Metric');

		// 6. Commit metrics
		$(Jupyter.toolbar.add_buttons_group([
			Jupyter.keyboard_manager.actions.register({
				help: 'Commit logged metrics (commit_metrics)',
				icon: 'fa-check-square',
				handler: cmf_commit_metrics
			}, 'Commit-CMF-Metrics', 'Commit_CMF_Metrics')
		])).find('.btn').attr('id', 'Commit_CMF_Metrics');

		// 7. Log model
		$(Jupyter.toolbar.add_buttons_group([
			Jupyter.keyboard_manager.actions.register({
				help: 'Log model (log_model)',
				icon: 'fa-cube',
				handler: cmf_log_model
			}, 'Inject-CMF-model-template', 'Inject_CMF_model_template')
		])).find('.btn').attr('id', 'Inject_CMF_model_template');

		// 8. Log execution metrics (coarse-grained)
		$(Jupyter.toolbar.add_buttons_group([
			Jupyter.keyboard_manager.actions.register({
				help: 'Log execution metrics (log_execution_metrics)',
				icon: 'fa-bar-chart',
				handler: cmf_log_execution_metrics
			}, 'Log-CMF-Execution-Metrics', 'Log_CMF_Execution_Metrics')
		])).find('.btn').attr('id', 'Log_CMF_Execution_Metrics');

		// UNUSED buttons (handlers commented out above)
		// $(Jupyter.toolbar.add_buttons_group([
		// 	Jupyter.keyboard_manager.actions.register({
		// 		help: 'Create execution stage cells',
		// 		icon: 'fa-magnet',
		// 		handler: cmf_stage_inject
		// 	}, 'cmf-stage-inject', 'cmf_stage_inject')
		// ])).find('.btn').attr('id', 'cmf_stage_inject');
		//
		// $(Jupyter.toolbar.add_buttons_group([
		// 	Jupyter.keyboard_manager.actions.register({
		// 		help: 'Inject CMF Dataset code',
		// 		icon: 'fa-gears',
		// 		handler: cmf_inject_dataset
		// 	}, 'Inject-CMF-Dataset-code', 'Inject_CMF_Dataset_code')
		// ])).find('.btn').attr('id', 'Inject_CMF_Dataset_code');
		//
		// $(Jupyter.toolbar.add_buttons_group([
		// 	Jupyter.keyboard_manager.actions.register({
		// 		help: 'Inject Kafka Code',
		// 		icon: 'fa-pencil',
		// 		handler: inject_shadow_pipeline
		// 	}, 'Inject-Kafka-Code', 'Inject_Kafka_Code')
		// ])).find('.btn').attr('id', 'Inject_Kafka_Code');

		// UNUSED: automatic injection of the CMF import on notebook load.
		// The "Create CMF class" button (1) replaces this behaviour.
		// console.log("Setting up CMF import statements");
		// require_import = true
		// for (let i in Jupyter.notebook.get_cells()) {
		// 	if (Jupyter.notebook.get_cells()[i].get_text().match("from cmflib import cmf.*")) {
		// 		console.log("Import statement exists")
		// 		require_import = false;
		// 		break;
		// 	}
		// 	else {
		// 		require_import = true;
		// 	}
		// }
		// if (require_import) {
		// 	cmf_code = 'from cmflib import cmf' + `\n`;
		// 	cmf_code += 'metawriter = cmf.Cmf(filepath="' + Jupyter.notebook.notebook_name.substr(0, Jupyter.notebook.notebook_name.length - 6) + '.mlmd", pipeline_name="' + Jupyter.notebook.notebook_name.substr(0, Jupyter.notebook.notebook_name.length - 6) + '", custom_properties={}, graph=False, is_server=False)' + `\n`;
		// 	Jupyter.notebook.insert_cell_at_index("code", 0).set_text(cmf_code)
		// }

	}

	return {
		load_ipython_extension: load_ipython_extension
	};
});
