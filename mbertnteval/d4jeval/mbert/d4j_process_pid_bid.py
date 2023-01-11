import os
from os.path import isfile, join, isdir

import pandas as pd

from codebertnt.locs_request import BusinessFileRequest
from mbertnteval.d4jeval.d4j_project import D4jProject
from mbertnteval.d4jeval.mbert.d4j_mbert_request import D4jRequest


def get_args():
    import argparse
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('-fix_commit_changes_csv', dest='fix_commit_changes_csv')
    parser.add_argument('-config', dest='config', help='config yaml file.')
    args = parser.parse_args()

    if args.fix_commit_changes_csv is None or not isfile(args.config):
        parser.print_help()
        raise AttributeError
    return args


def load_config(config_file: str):
    # import pyyaml module
    import yaml
    from yaml.loader import SafeLoader

    # Open the file and load the file
    with open(config_file) as f:
        data = yaml.load(f, Loader=SafeLoader)
        return data


def create_mbert_request(project: D4jProject, csv_path: str,
                         output_dir: str, max_processes_number: int = 4, all_lines=True) -> D4jRequest:
    df = pd.read_csv(csv_path)
    if project.version == 'b':
        v = 0
    else:
        v = 1
    dfv = df[df['version'] == v]

    reqs = {BusinessFileRequest(row['file'], None if all_lines else str(row['lines']))
            for index, row in dfv.iterrows() if row['file'].endswith('.java')}
    return D4jRequest(project=project, file_requests=reqs, repo_path=project.repo_path, output_dir=output_dir,
                      max_processes_number=max_processes_number)


def create_request(config, job_name) -> D4jRequest:
    #  job_name = Math_2.src.patch.csv -> pid_bid = Math_2
    pid_bid = job_name.split(".")[0]
    pid_bid_splits = pid_bid.split('_')
    d4j_project = D4jProject(os.path.expanduser(config['defects4j']['containing_dir']),
                             os.path.expanduser(config['tmp_large_memory']['d4jRepos']), pid=pid_bid_splits[0],
                             bid=pid_bid_splits[1],
                             jdk8=os.path.expanduser(config['java']['home8']),
                             jdk7=os.path.expanduser(config['java']['home7']))

    fix_commit_changes_csv = join(os.path.expanduser(config['defects4j']['fix_commit_changes_dir']), job_name)
    output_dir = join(os.path.expanduser(config['output_dir']), pid_bid)
    if not isdir(output_dir):
        try:
            os.makedirs(output_dir)
        except FileExistsError:
            print("two threads created the directory concurrently.")

    return create_mbert_request(d4j_project, fix_commit_changes_csv, output_dir,
                                config['exec']['max_processes'], config['exec']['all_lines'])


if __name__ == '__main__':
    args = get_args()
    job_name = args.fix_commit_changes_csv
    config = load_config(args.config)

    request: D4jRequest = create_request(config, job_name)

    request.call(os.path.expanduser(config['java']['home8']))
