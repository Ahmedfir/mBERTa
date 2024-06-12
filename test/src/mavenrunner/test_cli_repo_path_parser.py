import argparse
from os.path import join
from pathlib import Path
from unittest import TestCase

from mavenrunner.cli_repo_path_parser import parse_repo_cli_infos, RepoCliInfos


class Test(TestCase):

    def setUp(self):
        self.TEST_PATH = Path(__file__).parent.parent.parent
        self.RES_PATH = join(self.TEST_PATH, 'res')
        self.project_url_csv = join(self.RES_PATH, 'mavenrunner/repo_infos_csv.csv')

    def test_parse_repo_cli_infos(self):
        parser = argparse.ArgumentParser(description='')
        parser.add_argument('-project_url_csv', dest='project_url_csv', default=self.project_url_csv,
                            help="optional: if a repo_path or a git_url is given.\nIt can contain the following columns:\n"
                                 "'git_url': the git url of the project,\n"
                                 "'rev_id': the commit-hash to checkout,\n"
                                 "'project_name': the name of directory to clone the project in.")
        args = parser.parse_args()
        expected_obj = RepoCliInfos(git_url="https://github.com/Ahmedfir/JunitLab.git", rev_id="dummy_rev_id",
                                    project_name="JunitLab_1")
        obj = parse_repo_cli_infos(args)
        self.assertEqual(expected_obj, obj)
