###
# Copyright (2025) Hewlett Packard Enterprise Development LP
#
# Licensed under the Apache License, Version 2.0 (the "License");
# You may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
###

"""
Layer 2: CLI Argument Parser Tests

These tests focus on the argparse configuration and argument validation.
Tests verify that CLI arguments are parsed correctly and routed to the right commands.

Test Coverage:
- Command routing (metadata, artifact, init, etc.)
- Required vs optional arguments
- Argument validation and defaults
- Error handling for missing/invalid arguments
- Help text and usage
- Mutually exclusive arguments (if any)
- Short and long flag forms
"""

import pytest
import argparse
from unittest.mock import Mock, patch

from cmflib.cli import parse_args, CmfParserError
from cmflib.cli.parser import get_main_parser, CmfParser
from cmflib.commands.metadata import push as metadata_push_module
from cmflib.commands.metadata import pull as metadata_pull_module
from cmflib.commands.metadata import export as metadata_export_module
from cmflib.commands.artifact import push as artifact_push_module
from cmflib.commands.artifact import pull as artifact_pull_module
from cmflib.commands.artifact import list as artifact_list_module


class TestCLIParser:
    """Test suite for main CLI parser configuration"""

    # ============================================================================
    # PARSER INITIALIZATION TESTS
    # ============================================================================

    def test_get_main_parser_returns_cmf_parser(self):
        """
        Test that get_main_parser returns a CmfParser instance.
        """
        # Act
        parser = get_main_parser()
        
        # Assert
        assert isinstance(parser, CmfParser)
        assert parser.prog == "cmf"


    def test_parser_has_help_option(self):
        """
        Test that parser has --help/-h option configured.
        """
        # Arrange
        parser = get_main_parser()
        
        # Act - try parsing help (should not raise error)
        with pytest.raises(SystemExit):  # argparse exits with help
            parser.parse_args(['--help'])


    def test_parser_description_set(self):
        """
        Test that parser has description set.
        """
        # Arrange
        parser = get_main_parser()
        
        # Assert
        assert parser.description is not None
        assert "metadata" in parser.description.lower() or "cmf" in parser.description.lower()


    # ============================================================================
    # COMMAND ROUTING TESTS
    # ============================================================================

    def test_metadata_push_command_routing(self):
        """
        Test that 'cmf metadata push' routes to correct command class.
        """
        # Act
        args = parse_args(['metadata', 'push', '-p', 'test-pipeline', '-f', './mlmd'])
        
        # Assert
        assert args.cmd == 'metadata'
        assert hasattr(args, 'func')
        assert args.func is not None


    def test_metadata_pull_command_routing(self):
        """
        Test that 'cmf metadata pull' routes to correct command class.
        """
        # Act
        args = parse_args(['metadata', 'pull', '-p', 'test-pipeline', '-f', './mlmd', '-e', 'uuid-123'])
        
        # Assert
        assert args.cmd == 'metadata'
        assert hasattr(args, 'func')


    def test_metadata_export_command_routing(self):
        """
        Test that 'cmf metadata export' routes to correct command class.
        """
        # Act
        args = parse_args(['metadata', 'export', '-p', 'test-pipeline', '-f', './mlmd'])
        
        # Assert
        assert args.cmd == 'metadata'
        assert hasattr(args, 'func')


    def test_artifact_push_command_routing(self):
        """
        Test that 'cmf artifact push' routes to correct command class.
        """
        # Act
        args = parse_args(['artifact', 'push', '-p', 'test-pipeline', '-f', './mlmd', '-j', '4'])
        
        # Assert
        assert args.cmd == 'artifact'
        assert hasattr(args, 'func')


    def test_artifact_pull_command_routing(self):
        """
        Test that 'cmf artifact pull' routes to correct command class.
        """
        # Act
        args = parse_args(['artifact', 'pull', '-p', 'test-pipeline', '-f', './mlmd'])
        
        # Assert
        assert args.cmd == 'artifact'
        assert hasattr(args, 'func')


    def test_artifact_list_command_routing(self):
        """
        Test that 'cmf artifact list' routes to correct command class.
        """
        # Act
        args = parse_args(['artifact', 'list', '-p', 'test-pipeline', '-f', './mlmd'])
        
        # Assert
        assert args.cmd == 'artifact'
        assert hasattr(args, 'func')


    def test_pipeline_list_command_routing(self):
        """
        Test that 'cmf pipeline list' routes to correct command class.
        """
        # Act
        args = parse_args(['pipeline', 'list', '-f', './mlmd'])
        
        # Assert
        assert args.cmd == 'pipeline'
        assert hasattr(args, 'func')


    def test_execution_list_command_routing(self):
        """
        Test that 'cmf execution list' routes to correct command class.
        """
        # Act
        args = parse_args(['execution', 'list', '-p', 'test-pipeline', '-f', './mlmd'])
        
        # Assert
        assert args.cmd == 'execution'
        assert hasattr(args, 'func')


    def test_init_local_command_routing(self):
        """
        Test that 'cmf init local' routes to correct command class.
        """
        # Act
        args = parse_args([
            'init', 'local',
            '--path', '/tmp/data',
            '--git-remote-url', 'https://github.com/user/repo.git',
            '--cmf-server-url', 'http://localhost:80'
        ])
        
        # Assert
        assert args.cmd == 'init'
        assert hasattr(args, 'func')


    def test_repo_push_command_routing(self):
        """
        Test that 'cmf repo push' routes to correct command class.
        """
        # Act
        args = parse_args(['repo', 'push', '-p', 'test-pipeline', '-f', './mlmd'])
        
        # Assert
        assert args.cmd == 'repo'
        assert hasattr(args, 'func')


    def test_repo_pull_command_routing(self):
        """
        Test that 'cmf repo pull' routes to correct command class.
        """
        # Act
        args = parse_args(['repo', 'pull', '-p', 'test-pipeline', '-f', './mlmd', '-e', 'uuid-123'])
        
        # Assert
        assert args.cmd == 'repo'
        assert hasattr(args, 'func')


    # ============================================================================
    # REQUIRED ARGUMENTS TESTS
    # ============================================================================

    def test_metadata_push_requires_pipeline_name(self):
        """
        Test that metadata push requires -p/--pipeline-name argument.
        """
        # Act & Assert
        with pytest.raises(SystemExit):  # argparse exits on missing required arg
            parse_args(['metadata', 'push', '-f', './mlmd'])


    def test_metadata_push_requires_file_name(self):
        """
        Test that metadata push requires -f/--file-name argument.
        """
        # Act & Assert
        with pytest.raises(SystemExit):
            parse_args(['metadata', 'push', '-p', 'test-pipeline'])


    def test_artifact_push_requires_pipeline_and_file(self):
        """
        Test that artifact push requires both pipeline and file arguments.
        """
        # Act & Assert
        with pytest.raises(SystemExit):
            parse_args(['artifact', 'push'])


    def test_pipeline_list_requires_file_name(self):
        """
        Test that pipeline list requires file name argument.
        """
        # Act & Assert
        with pytest.raises(SystemExit):
            parse_args(['pipeline', 'list'])


    def test_init_local_requires_path(self):
        """
        Test that init local requires --path argument.
        """
        # Act & Assert
        with pytest.raises(SystemExit):
            parse_args(['init', 'local', '--git-remote-url', 'url', '--cmf-server-url', 'url'])


    # ============================================================================
    # OPTIONAL ARGUMENTS TESTS
    # ============================================================================

    def test_metadata_push_execution_uuid_optional(self):
        """
        Test that execution UUID is optional for metadata push.
        """
        # Act
        args = parse_args(['metadata', 'push', '-p', 'test-pipeline', '-f', './mlmd'])
        
        # Assert
        assert hasattr(args, 'execution_uuid')
        assert args.execution_uuid is None or args.execution_uuid == []


    def test_metadata_push_with_execution_uuid(self):
        """
        Test parsing metadata push with optional execution UUID.
        """
        # Act
        args = parse_args([
            'metadata', 'push',
            '-p', 'test-pipeline',
            '-f', './mlmd',
            '-e', 'uuid-123'
        ])
        
        # Assert
        assert args.execution_uuid is not None
        assert 'uuid-123' in args.execution_uuid


    def test_metadata_push_tensorboard_path_optional(self):
        """
        Test that tensorboard path is optional for metadata push.
        """
        # Act
        args = parse_args(['metadata', 'push', '-p', 'test-pipeline', '-f', './mlmd'])
        
        # Assert
        assert hasattr(args, 'tensorboard_path')
        assert args.tensorboard_path is None or args.tensorboard_path == []


    def test_metadata_push_with_tensorboard_path(self):
        """
        Test parsing metadata push with optional tensorboard path.
        """
        # Act
        args = parse_args([
            'metadata', 'push',
            '-p', 'test-pipeline',
            '-f', './mlmd',
            '-t', '/path/to/tensorboard'
        ])
        
        # Assert
        assert args.tensorboard_path is not None
        assert '/path/to/tensorboard' in args.tensorboard_path


    def test_artifact_push_jobs_optional(self):
        """
        Test that jobs parameter is optional for artifact push.
        """
        # Act
        args = parse_args(['artifact', 'push', '-p', 'test-pipeline', '-f', './mlmd'])
        
        # Assert
        assert hasattr(args, 'jobs')
        # Should have default value or be None


    def test_artifact_push_with_jobs(self):
        """
        Test parsing artifact push with jobs parameter.
        """
        # Act
        args = parse_args([
            'artifact', 'push',
            '-p', 'test-pipeline',
            '-f', './mlmd',
            '-j', '8'
        ])
        
        # Assert
        assert args.jobs is not None
        assert '8' in args.jobs


    def test_artifact_list_artifact_name_optional(self):
        """
        Test that artifact name is optional for artifact list.
        """
        # Act
        args = parse_args(['artifact', 'list', '-p', 'test-pipeline', '-f', './mlmd'])
        
        # Assert
        assert hasattr(args, 'artifact_name')
        assert args.artifact_name is None or args.artifact_name == []


    def test_artifact_list_with_artifact_name(self):
        """
        Test parsing artifact list with specific artifact name.
        """
        # Act
        args = parse_args([
            'artifact', 'list',
            '-p', 'test-pipeline',
            '-f', './mlmd',
            '-a', 'model.pkl'
        ])
        
        # Assert
        assert args.artifact_name is not None
        assert 'model.pkl' in args.artifact_name


    def test_metadata_export_json_file_optional(self):
        """
        Test that json file name is optional for metadata export.
        """
        # Act
        args = parse_args(['metadata', 'export', '-p', 'test-pipeline', '-f', './mlmd'])
        
        # Assert
        assert hasattr(args, 'json_file_name')
        # Should be None or have default value


    def test_metadata_export_with_json_file(self):
        """
        Test parsing metadata export with json output file.
        """
        # Act
        args = parse_args([
            'metadata', 'export',
            '-p', 'test-pipeline',
            '-f', './mlmd',
            '-j', 'output.json'
        ])
        
        # Assert
        assert args.json_file_name is not None
        assert 'output.json' in args.json_file_name


    # ============================================================================
    # ARGUMENT VARIATIONS TESTS
    # ============================================================================

    def test_pipeline_name_accepts_various_formats(self):
        """
        Test that pipeline names with various formats are accepted.
        """
        test_cases = [
            'simple-pipeline',
            'pipeline_with_underscore',
            'pipeline123',
            'Pipeline-With-Caps',
            'pipeline.with.dots'
        ]
        
        for pipeline_name in test_cases:
            # Act
            args = parse_args(['metadata', 'push', '-p', pipeline_name, '-f', './mlmd'])
            
            # Assert
            assert pipeline_name in args.pipeline_name


    def test_file_path_accepts_absolute_and_relative(self):
        """
        Test that file paths accept both absolute and relative paths.
        """
        test_cases = [
            './mlmd',
            '/absolute/path/to/mlmd',
            '../relative/mlmd',
            'mlmd',
            '/tmp/test-mlmd'
        ]
        
        for file_path in test_cases:
            # Act
            args = parse_args(['metadata', 'push', '-p', 'test-pipeline', '-f', file_path])
            
            # Assert
            assert file_path in args.file_name


    def test_execution_uuid_accepts_various_uuid_formats(self):
        """
        Test that execution UUID accepts various UUID formats.
        """
        test_cases = [
            'f9da581c-d16c-11ef-9809-9350156ed1ac',
            '123e4567-e89b-12d3-a456-426614174000',
            'simple-uuid-format'
        ]
        
        for uuid in test_cases:
            # Act
            args = parse_args([
                'metadata', 'push',
                '-p', 'test-pipeline',
                '-f', './mlmd',
                '-e', uuid
            ])
            
            # Assert
            assert uuid in args.execution_uuid


    # ============================================================================
    # INVALID ARGUMENTS TESTS
    # ============================================================================

    def test_invalid_command_raises_error(self):
        """
        Test that invalid command raises parser error.
        """
        # Act & Assert
        with pytest.raises((SystemExit, CmfParserError)):
            parse_args(['invalid-command'])


    def test_invalid_subcommand_raises_error(self):
        """
        Test that invalid subcommand raises parser error.
        """
        # Act & Assert
        with pytest.raises(SystemExit):
            parse_args(['metadata', 'invalid-subcommand'])


    def test_unrecognized_argument_raises_error(self):
        """
        Test that unrecognized arguments raise error.
        """
        # Act & Assert
        with pytest.raises((SystemExit, CmfParserError)):
            parse_args([
                'metadata', 'push',
                '-p', 'test-pipeline',
                '-f', './mlmd',
                '--invalid-flag', 'value'
            ])


    def test_argument_without_value_raises_error(self):
        """
        Test that arguments requiring values raise error when value missing.
        """
        # Act & Assert
        with pytest.raises(SystemExit):
            parse_args(['metadata', 'push', '-p', 'test-pipeline', '-f'])


    def test_multiple_values_for_single_arg_handled(self):
        """
        Test behavior when multiple values provided for single argument.
        
        Note: Depending on nargs configuration, this might be accepted or rejected.
        """
        # This test documents current behavior - adjust based on design
        # If single value expected but multiple provided:
        try:
            args = parse_args([
                'metadata', 'push',
                '-p', 'pipeline1', 'pipeline2',
                '-f', './mlmd'
            ])
            # If accepted, pipeline2 might be treated as positional arg or error
        except SystemExit:
            # Expected if parser rejects multiple values
            pass


    # ============================================================================
    # COMMAND COMBINATION TESTS
    # ============================================================================

    def test_metadata_push_all_optional_args(self):
        """
        Test metadata push with all optional arguments provided.
        """
        # Act
        args = parse_args([
            'metadata', 'push',
            '-p', 'test-pipeline',
            '-f', './mlmd',
            '-e', 'uuid-123',
            '-t', '/tensorboard/logs'
        ])
        
        # Assert
        assert 'test-pipeline' in args.pipeline_name
        assert './mlmd' in args.file_name
        assert 'uuid-123' in args.execution_uuid
        assert '/tensorboard/logs' in args.tensorboard_path


    def test_repo_push_with_all_options(self):
        """
        Test repo push with all optional arguments.
        """
        # Act
        args = parse_args([
            'repo', 'push',
            '-p', 'test-pipeline',
            '-f', './mlmd',
            '-e', 'uuid-123',
            '-t', '/tensorboard/logs',
            '-j', '4'
        ])
        
        # Assert
        assert args.cmd == 'repo'
        assert 'test-pipeline' in args.pipeline_name
        assert './mlmd' in args.file_name


    def test_init_local_with_neo4j_options(self):
        """
        Test init local with optional neo4j configuration.
        """
        # Act
        args = parse_args([
            'init', 'local',
            '--path', '/tmp/data',
            '--git-remote-url', 'https://github.com/user/repo.git',
            '--cmf-server-url', 'http://localhost:80',
            '--neo4j-user', 'neo4j',
            '--neo4j-password', 'password',
            '--neo4j-uri', 'bolt://localhost:7687'
        ])
        
        # Assert
        assert '/tmp/data' in args.path
        assert 'neo4j' in args.neo4j_user


    # ============================================================================
    # PARSER ATTRIBUTE TESTS
    # ============================================================================

    def test_parsed_args_contain_parser_reference(self):
        """
        Test that parsed args contain reference to parser.
        
        This is useful for showing help on errors.
        """
        # Act
        args = parse_args(['metadata', 'push', '-p', 'test-pipeline', '-f', './mlmd'])
        
        # Assert
        assert hasattr(args, 'parser')
        assert args.parser is not None


    def test_parsed_args_contain_func_callable(self):
        """
        Test that parsed args contain callable func for command execution.
        """
        # Act
        args = parse_args(['metadata', 'push', '-p', 'test-pipeline', '-f', './mlmd'])
        
        # Assert
        assert hasattr(args, 'func')
        assert callable(args.func)


    # ============================================================================
    # SPECIAL CASES
    # ============================================================================

    def test_no_arguments_shows_help(self):
        """
        Test that calling cmf without arguments shows help.
        """
        # Act & Assert
        with pytest.raises((SystemExit, CmfParserError)):
            parse_args([])


    def test_command_without_subcommand_shows_help(self):
        """
        Test that calling 'cmf metadata' without subcommand shows help.
        """
        # Act & Assert
        with pytest.raises((SystemExit, CmfParserError)):
            parse_args(['metadata'])


    @pytest.mark.parametrize("command", ['metadata', 'artifact', 'init', 'pipeline', 'execution', 'repo'])
    def test_all_main_commands_accept_help_flag(self, command):
        """
        Test that all main commands accept --help flag.
        """
        # Act & Assert
        with pytest.raises(SystemExit):  # Help causes exit
            parse_args([command, '--help'])


    # ============================================================================
    # EDGE CASES
    # ============================================================================

    def test_empty_string_argument_values(self):
        """
        Test handling of empty string as argument value.
        """
        # Act
        args = parse_args(['metadata', 'push', '-p', '', '-f', './mlmd'])
        
        # Assert
        assert '' in args.pipeline_name


    def test_whitespace_argument_values(self):
        """
        Test handling of whitespace in argument values.
        """
        # Act
        args = parse_args(['metadata', 'push', '-p', '  test-pipeline  ', '-f', './mlmd'])
        
        # Assert
        # Parser doesn't strip by default
        assert '  test-pipeline  ' in args.pipeline_name


    def test_special_characters_in_arguments(self):
        """
        Test that special characters in arguments are preserved.
        """
        # Act
        args = parse_args([
            'metadata', 'push',
            '-p', 'pipeline-with-special_chars!@#',
            '-f', './mlmd'
        ])
        
        # Assert
        assert 'pipeline-with-special_chars!@#' in args.pipeline_name
