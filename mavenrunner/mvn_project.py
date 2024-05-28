import logging
import sys
from os import listdir, makedirs
from os.path import join, isdir, isfile
from pathlib import Path
from subprocess import SubprocessError, TimeoutExpired, CompletedProcess
from typing import List
from git import GitCommandError

import pandas as pd

from mbertntcall.mbert_project import MbertProject
from utils import file_read_write
from utils.cmd_utils import safe_chdir, shell_call, DEFAULT_TIMEOUT_S
from utils.git_utils import clone_checkout

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)
log.addHandler(logging.StreamHandler(sys.stdout))


def adapt_tests(x):
    return x.replace('::', '.').replace(
        "'", "").replace("[", '').replace(']', '')


def string_to_array(x, test_splitter=','):
    tests = [] if not x or x is None or x == 'nan' or x == ['nan'] or x == "['nan']" or len(x) == 0 else adapt_tests(
        x).split(
        test_splitter)
    return [t.strip() for t in tests if t is not None and len(t.strip()) > 0]


class MvnProject(MbertProject):


    @staticmethod
    def get_project_name_from_git_url(vcs_url):
        return vcs_url.replace('.git','').split('/')[-1]
    def __init__(self,repo_path, repos_path, jdk_path=None, mvn_home= None, vcs_url=None, rev_id=None):
        super(MvnProject, self).__init__(repo_path, jdk_path, None, None, repos_path)
        if self.repo_path is None or not isdir(self.repo_path):
            if vcs_url is None:
                raise Exception("Pleas pass a valid git url or repo path.")
            self.repo_path = str(join(repos_path, self.get_project_name_from_git_url(vcs_url)))
            log.info("repo path will be: " + self.repo_path)
        self.mvn_home = mvn_home
        self.vcs_url = vcs_url
        self.rev_id = rev_id
        self.failing_tests = None
        self.lock = None
        self.relevant_tests_exec_only_possible = True
        self.source_dir = None
        self.bin_dir = None
        self.target_classes = None

    def cp(self, n):
        copy = super(MvnProject, self).cp(n)
        # fixme
        copy.repo_path = join(copy.repos_path, self.repo_path.name)
        return copy

    def cmd_base(self):
        cmd_arr = []
        if self.jdk is not None and isdir(self.jdk):
            cmd_arr.append("JAVA_HOME='" + self.jdk + "'")
        if self.mvn_home is not None and isdir(self.mvn_home):
            cmd_arr.append("M2_HOME='" + self.mvn_home + "'")
        cmd_arr.append('mvn')
        return " ".join(cmd_arr)

    def checkout_validate_fixed_version(self) -> bool:
        # fixme
        return self.validate_fixed_version_project(force_reload=True)

    def checkout_compile_buggy_version(self, force_reload=False):
        self.checkout(force_reload=force_reload)
        try:
            success = self.compile()
        except SubprocessError:
            success = False
        return success

    def validate_fixed_version_project(self, jdk=None, force_reload=False) -> bool:
        # compiles and tests pass for the fixed version.
        # set the jdk that works fine for this project.
        # this implementation tries only 1 jdk7 and 1 jdk8.
        self.checkout(force_reload=force_reload)

        try:
            failed = not self.compile()
            if not failed:
                try:
                    broken_tests = self.test()
                    failed = len(broken_tests) > 0
                except SubprocessError:
                    self.relevant_tests_exec_only_possible = False
                    broken_tests = self.test()
                    failed = len(broken_tests) > 0
        except SubprocessError:
            failed = True

        return not failed

    def checkout(self, force_reload=True):
        """checkout project"""
        if self.repo_path is not None and isdir(self.repo_path) and len(listdir(self.repo_path)) > 0:
            if force_reload:
                self.remove()
            else:
                return self.repo_path + ' dir exists and is not empty.'
        if not isdir(join(self.repos_path)):
            try:
                makedirs(join(self.repos_path))
            except FileExistsError:
                log.debug("two threads created the directory concurrently.")
        try:
            if self.repo_path is None:
                self.repo_path = self.repos_path
            clone_checkout(self.vcs_url, self.repo_path, self.rev_id)
            return isdir(self.repo_path) and len(listdir(self.repo_path)) > 0
        except GitCommandError as e:
            log.error('failed to clone and checkout repo {0} {1}'.format(self.vcs_url, self.rev_id))
            log.critical("checkout failed for {0}".format(self.repo_path), e, exc_info=True)
            import traceback
            traceback.print_exc()
            raise e

    def compile_command(self) -> str:
        return self.cmd_base() + " compile"

    def on_has_compiled(self, output) -> bool:
        text = output.stdout
        if len(text) == 0:
            text = output.stderr
            log.error(text)
        else:
            log.debug(text)
        return len(output.stdout) > 0 and len(output.stderr) == 0

    def coverage_command(self, relevant_tests=True) -> str:
        raise Exception('Not implemented yet!')

    def test_command(self, relevant_tests=True) -> str:
        cmd = self.cmd_base() + " test"
        # todo implement this
        if self.relevant_tests_exec_only_possible and relevant_tests:
            cmd = cmd + " -r"
        return cmd

    def test(self, timeout=DEFAULT_TIMEOUT_S, relevant_tests=True) -> List[str]:
        """test project"""
        with safe_chdir(self.repo_path):
            log.debug('testing {0} in {1}'.format(self.pid_bid, self.repo_path))
            cmd = self.test_command(relevant_tests)
            log.info('-- executing shell cmd = {0}'.format(cmd))
            try:
                output = shell_call(cmd, timeout=timeout)
                return self.on_tests_run(output)
            except TimeoutExpired as te:
                log.debug('timeout')
                raise te
            except SubprocessError as e:
                log.critical("compilation failed for {0}".format(self.pid_bid), e, exc_info=True)
                raise e

    def get_src_dir(self):
        # todo
        if self.source_dir is None:
            self.source_dir = self.export_prop('dir.src.classes')
        return self.source_dir

    def adapt_file_abs_path(self, file_path):
        if isinstance(file_path, str):
            res_path = file_path
            if not isfile(res_path):
                repo_dir = Path(self.repo_path).name
                if repo_dir in res_path:
                    f = res_path.split(repo_dir)[1]
                    res_path = self.repo_path + f
                    if not isfile(res_path):
                        res_path = join(self.repo_path, f)
                else:
                    res_path = self.repo_path + res_path
                    if not isfile(res_path):
                        res_path = join(self.repo_path, file_path)

                assert isfile(res_path), 'auto_path_adapt failed to fix absolute file path \n' \
                                         '-> adapted path : {0}'.format(file_path)
            return res_path
        elif isinstance(file_path, list):
            return [self.adapt_file_abs_path(f) for f in file_path]
