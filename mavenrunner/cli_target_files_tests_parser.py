import logging
import sys
from os.path import isfile
from typing import Dict

import pandas as pd

from codebertnt.locs_request import BusinessFileRequest

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)
log.addHandler(logging.StreamHandler(sys.stdout))


def parse_target_files_tests(cli_args, all_lines: bool = True) -> Dict[BusinessFileRequest, str]:
    if cli_args is None:
        log.warning('No target files passed! You will target on all files! You will also run all tests!')
        return None
    reqs = None
    if cli_args.target_files_csv is not None and isfile(cli_args.target_files_csv):
        df = pd.read_csv(cli_args.target_files_csv, sep=';')
        if 'lines' not in df.columns or all_lines:
            df['lines'] = None
        if 'tests' not in df.columns:
            df['tests'] = cli_args.tests
        reqs = {BusinessFileRequest(row['filename'], None if all_lines else str(row['lines'])): row['tests']
                for index, row in df.iterrows() if row['filename'].endswith('.java')}
    elif cli_args.target_files is not None:
        reqs = {BusinessFileRequest(f.strip(), None): cli_args.tests
                for f in cli_args.target_files.split(',') if f.endswith('.java')}
    return reqs


