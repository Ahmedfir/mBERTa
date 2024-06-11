import logging
import os
from os.path import isfile, join, isdir
from pathlib import Path
from typing import Dict

import pandas as pd
import torch

from codebertnt.locs_request import BusinessFileRequest
from mavenrunner.cli_target_files_tests_parser import parse_target_files_tests
from mavenrunner.mvn_mbert_request import MvnRequest
from mavenrunner.mvn_project import MvnProject
from mbertnteval.d4jeval.yaml_utils import load_config

git_url = "https://github.com/aws/event-ruler.git"
rev_id = "48db0b03449451ee02723f8e648f2f4aef18cbdb"
csv_file = "/home/asmahamidi/code/mBERTa/mavenrunner/gitbug-projects/aws-event-ruler.csv"


def _get_test_dummy_project_path():
    logging.critical("!!! DUMMY PROJECT SELECTED !!! You have to pass YOUR repo path or a git_url.")
    return join(Path(__file__).parent.parent, 'test', 'res', 'exampleclass', 'DummyProject')


def get_args():
    import argparse
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('-target_files_csv', dest='target_files_csv',
                        help="optional: csv file containing a list of java files and lines to mutate: one file per row. Also you can pass the tests to run. \nColumns are 'filename';'lines';'tests' and the separator is ';'. \nThe tests must be separated by a ',' and formatted as follows:\n pkg.cls#method\n Note that when 'all_lines' is set True in the config file, the 'lines' column will be ignored.")
    parser.add_argument('-target_files', dest='target_files',
                        help="optional: list of java files to mutate separated by a coma. ")
    parser.add_argument('-tests', dest='tests',
                        help="optional: list of tests to target separated by a coma. "
                             "The tests should be of this format: pkg.cls#method ")

    parser.add_argument('-git_url', dest='git_url', help='optional if a repo_path is given: git url to your repo.')
    parser.add_argument('-rev_id', dest='rev_id', help='optional: rev_id (commit-hash) to checkout.')
    parser.add_argument('-repo_path', dest='repo_path', default=_get_test_dummy_project_path(),
                        help='optional if a git_url is given: the path to your maven project.')
    parser.add_argument('-config', dest='config',
                        help='required: config yaml file.', default=join(Path(__file__).parent,
                                                                         'mbert_config.yml'))  # i.e. , default=os.path.expanduser('~/PycharmProjects/CBMuPy/d4j/mbert/local_config.yml'))
    args = parser.parse_args()

    if (not isfile(args.config) and not isfile(os.path.expanduser(args.config))) or (
            args.repo_path is None and args.git_url is None):
        parser.print_help()
        raise AttributeError
    if args.target_files_csv is not None and args.target_files is not None:
        parser.print_help()
        raise AttributeError('Use -target_files_csv or -target_files to pass the target files.')
    return args


def create_mbert_request(project: MvnProject, files_tests: Dict[BusinessFileRequest, str], tests: str,
                         output_dir: str, max_processes_number: int = 4,
                         simple_only=False, force_reload=False,
                         mask_full_conditions=False, remove_project_on_exit=True, model=None) -> MvnRequest:
    return MvnRequest(project=project, files_tests_map=files_tests, tests=tests, repo_path=project.repo_path,
                      output_dir=output_dir,
                      max_processes_number=max_processes_number, simple_only=simple_only,
                      force_reload=force_reload, mask_full_conditions=mask_full_conditions,
                      remove_project_on_exit=remove_project_on_exit, model=model)


def create_request(config, cli_args, simple_only=False, no_comments=False, force_reload=False,
                   mask_full_conditions=False, remove_project_on_exit=True, model=None) -> MvnRequest:
    mvn_project = MvnProject(repo_path=cli_args.repo_path,
                             repos_path=os.path.expanduser(config['tmp_large_memory']['repos_path']),
                             jdk_path=os.path.expanduser(config['java']['home8']),
                             mvn_home=os.path.expanduser(config['maven']), vcs_url=cli_args.git_url,
                             rev_id=cli_args.rev_id, no_comments=no_comments,
                             tests_timeout=config['exec']['tests_timeout'])

    reqs = parse_target_files_tests(cli_args, config['exec']['all_lines'])
    # won't be used if tests are already set in the csv passed via -target_files_csv.
    tests = cli_args.tests

    output_dir = join(os.path.expanduser(config['output_dir']), Path(mvn_project.repo_path).name)
    if not isdir(output_dir):
        try:
            os.makedirs(output_dir)
        except FileExistsError:
            print("two threads created the directory concurrently.")

    return create_mbert_request(mvn_project, reqs, tests, output_dir, config['exec']['max_processes'],
                                simple_only=simple_only, force_reload=force_reload,
                                mask_full_conditions=mask_full_conditions,
                                remove_project_on_exit=remove_project_on_exit, model=model)


def main_function(conf, cli_args):
    config = load_config(conf)
    # this option sets the max number of process in pytorch, for a multi-cpu processing.
    if 'torch_processes' in config['exec'] and config['exec']['torch_processes']:
        torch.set_num_threads(config['exec']['torch_processes'])
    # this option removes all comments from the repo before the mutation.
    no_comments = 'no_comments' in config['exec'] and config['exec']['no_comments']
    if no_comments and cli_args.git_url is None:
        logging.warning("You are about to remove all the comments from your repo!")
    # this option adds extra mutants where the full if condition is masked.
    mask_full_conditions = 'mask_full_conditions' in config['exec'] and config['exec']['mask_full_conditions']
    # this option limits the generation to generating only simple mutants without the condition seeding ones.
    simple_only = 'simple_only' in config['exec'] and config['exec']['simple_only']
    # this option sets the model to use for predictions
    if 'model_name' in config['exec']['language_model'] and config['exec']['language_model']['model_name']:
        model = config['exec']['language_model']['model_name']

    # this option removes the project at the end when set to true.
    # by default, if a -git_url is given, the clone will be removed in the end, otherwise not.
    remove_project_on_exit = cli_args.git_url is not None
    if 'remove_project_on_exit' in config['exec'] and config['exec']['remove_project_on_exit'] is not None:
        remove_project_on_exit = config['exec']['remove_project_on_exit']

    request: MvnRequest = create_request(config, cli_args, simple_only=simple_only, no_comments=no_comments,
                                         mask_full_conditions=mask_full_conditions,
                                         remove_project_on_exit=remove_project_on_exit, model=model)
    request.call(os.path.expanduser(config['java']['home8']))


if __name__ == '__main__':
    args = get_args()
    main_function(os.path.expanduser(args.config), args)
