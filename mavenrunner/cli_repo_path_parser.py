import logging
import sys
from os.path import isfile

import pandas as pd
from pydantic import BaseModel

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)
log.addHandler(logging.StreamHandler(sys.stdout))


class RepoCliInfos(BaseModel):
    git_url: str = None
    rev_id: str = None
    repo_path: str = None
    project_name: str = None

    def invalid(self):
        return (self.git_url is None or len(self.git_url) == 0) and (self.repo_path is None or len(self.repo_path) == 0)


def parse_repo_cli_infos(cli_args) -> RepoCliInfos:
    if cli_args is None:
        raise Exception('No args passed!')
    if cli_args.project_url_csv is not None and isfile(cli_args.project_url_csv):
        df = pd.read_csv(cli_args.project_url_csv, sep=';')
        if len(df) != 1:
            raise Exception('expected one row dataset but received {0} rows'.format(str(len(df))))
        row = df.loc[0]
        result: RepoCliInfos = RepoCliInfos(git_url=row['git_url'] if 'git_url' in df.columns else (
            cli_args.git_url if hasattr(cli_args, 'git_url') else None),
                                            rev_id=row['rev_id'] if 'rev_id' in df.columns else (
                                                cli_args.rev_id if hasattr(cli_args, 'rev_id') else None),
                                            repo_path=row['repo_path'] if 'repo_path' in df.columns else (
                                                cli_args.repo_path if hasattr(cli_args, 'repo_path') else None),
                                            project_name=row['project_name'] if 'project_name' in df.columns else None)
    else:
        result: RepoCliInfos = RepoCliInfos(git_url=(cli_args.git_url if hasattr(cli_args, 'git_url') else None),
                                            rev_id=(cli_args.rev_id if hasattr(cli_args, 'rev_id') else None),
                                            repo_path=(cli_args.repo_path if hasattr(cli_args, 'repo_path') else None))
    return result
