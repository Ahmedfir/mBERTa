import os
from os.path import isfile, join, isdir

import pandas as pd
import torch

from codebertnt.locs_request import BusinessFileRequest
from mbertnteval.d4jeval.d4j_project import D4jProject
from mbertnteval.d4jeval.mbert.d4j_mbert_request import D4jRequest
from mbertnteval.d4jeval.yaml_utils import load_config


def get_args():
    import argparse
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('-fix_commit_changes_csv',
                        dest='fix_commit_changes_csv')  # i.e. , default='Csv_9.src.patch.csv')
    parser.add_argument('-config', dest='config',
                        help='config yaml file.')  # i.e. , default=os.path.expanduser('~/PycharmProjects/CBMuPy/d4j/mbert/local_config.yml'))
    args = parser.parse_args()

    if args.fix_commit_changes_csv is None or (not isfile(args.config) and not isfile(os.path.expanduser(args.config))):
        parser.print_help()
        raise AttributeError
    return args


def create_mbert_request(project: D4jProject, csv_path: str,
                         output_dir: str, max_processes_number: int = 4, all_lines=True,
                         simple_only=False, force_reload=False,
                         mask_full_if_conditions=False) -> D4jRequest:
    df = pd.read_csv(csv_path)
    if project.version == 'b':
        v = 0
    else:
        v = 1
    dfv = df[df['version'] == v]

    reqs = {BusinessFileRequest(row['file'], None if all_lines else str(row['lines']))
            for index, row in dfv.iterrows() if row['file'].endswith('.java')}

    return D4jRequest(project=project, file_requests=reqs, repo_path=project.repo_path, output_dir=output_dir,
                      max_processes_number=max_processes_number, simple_only=simple_only,
                      force_reload=force_reload, mask_full_if_conditions=mask_full_if_conditions)


def create_request(config, job_name, simple_only=False, no_comments=False, force_reload=False,
                   mask_full_if_conditions=False) -> D4jRequest:
    #  job_name = Math_2.src.patch.csv -> pid_bid = Math_2
    pid_bid = job_name.split(".")[0]
    pid_bid_splits = pid_bid.split('_')
    d4j_project = D4jProject(os.path.expanduser(config['defects4j']['containing_dir']),
                             os.path.expanduser(config['tmp_large_memory']['d4jRepos']), pid=pid_bid_splits[0],
                             bid=pid_bid_splits[1],
                             jdk8=os.path.expanduser(config['java']['home8']),
                             jdk7=os.path.expanduser(config['java']['home7']), no_comments=no_comments)

    fix_commit_changes_csv = join(os.path.expanduser(config['defects4j']['fix_commit_changes_dir']), job_name)
    output_dir = join(os.path.expanduser(config['output_dir']), pid_bid)
    if not isdir(output_dir):
        try:
            os.makedirs(output_dir)
        except FileExistsError:
            print("two threads created the directory concurrently.")

    return create_mbert_request(d4j_project, fix_commit_changes_csv, str(output_dir),
                                config['exec']['max_processes'], config['exec']['all_lines'],
                                simple_only=simple_only, force_reload=force_reload,
                                mask_full_if_conditions=mask_full_if_conditions)


def main_function(conf, changes_csv):
    config = load_config(conf)
    # this option sets the max number of process in pytorch, for a multi-cpu processing.
    if 'torch_processes' in config['exec'] and config['exec']['torch_processes']:
        torch.set_num_threads(config['exec']['torch_processes'])
    # this option removes all comments from the repo before the mutation.
    no_comments = 'no_comments' in config['exec'] and config['exec']['no_comments']
    # this option adds extra mutants where the full if condition is masked.
    mask_full_if_conditions = 'mask_full_if_conditions' in config['exec'] and config['exec']['mask_full_if_conditions']
    # this option limits the generation to generating only simple mutants without the condition seeding ones.
    simple_only = 'mask_full_if_conditions' in config['exec'] and config['exec']['mask_full_if_conditions']
    request: D4jRequest = create_request(config, changes_csv, simple_only=simple_only, no_comments=no_comments,
                                         mask_full_if_conditions=mask_full_if_conditions)
    request.call(os.path.expanduser(config['java']['home8']))


if __name__ == '__main__':
    args = get_args()
    job_name = args.fix_commit_changes_csv
    main_function(os.path.expanduser(args.config), job_name)
