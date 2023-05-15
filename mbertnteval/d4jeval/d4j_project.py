import logging
import sys
from os import listdir, makedirs
from os.path import join, isdir
from subprocess import SubprocessError, TimeoutExpired
from typing import List

from mbertntcall.mbert_project import MbertProject
from utils.cmd_utils import safe_chdir, shell_call, DEFAULT_TIMEOUT_S

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


class D4jProject(MbertProject):
    def __init__(self, d4j_path, repos_path, pid, bid, jdk8, jdk7=None, version='f'):
        super(D4jProject, self).__init__(None, None, None, None, repos_path)
        self.d4j_path = d4j_path
        self.pid = pid
        self.bid = bid
        self.pid_bid = pid + '_' + str(bid)
        self.repo_path = join(repos_path, version, self.pid_bid)
        self.jdk8 = jdk8
        self.jdk7 = jdk7
        self.version = version
        self.failing_tests = None
        self.lock = None
        self.relevant_tests_exec_only_possible = True

    def cp(self, n):
        copy = super(D4jProject, self).cp(n)
        copy.repo_path = join(copy.repos_path, self.version, self.pid_bid)
        return copy

    def d4j_exec_path(self):
        return join(self.d4j_path, 'defects4j', 'framework', 'bin', 'defects4j')

    def cmd_base(self):
        return "JAVA_HOME='" + self.jdk + "' " + self.d4j_exec_path()

    def checkout_validate_fixed_version(self) -> bool:
        return self.validate_fixed_version_project(force_reload=True)

    def validate_fixed_version_project(self, jdk=None, force_reload=False) -> bool:
        assert 'f' == self.version

        if jdk is not None:
            self.jdk = jdk
        elif self.jdk is None:
            self.jdk = self.jdk8
        else:
            return True

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

        if failed:
            self.jdk = None
            if jdk is not None or self.jdk7 is None:
                return False
            else:
                return self.validate_fixed_version_project(self.jdk7)
        else:
            return True

    def checkout(self, force_reload=True):
        """checkout project"""
        if isdir(self.repo_path) and len(listdir(self.repo_path)) > 0:
            if force_reload:
                self.remove()
            else:
                return self.repo_path + ' dir exists and is not empty.'
        if not isdir(join(self.repos_path, self.version)):
            try:
                makedirs(join(self.repos_path, self.version))
            except FileExistsError:
                log.debug("two threads created the directory concurrently.")
        cmd = self.cmd_base() + " checkout -p " + self.pid + " -v " + str(
            self.bid) + self.version + " -w " + self.repo_path

        log.info('-- executing shell cmd = {0}'.format(cmd))
        try:
            output = shell_call(cmd)
            text = output.stdout
            if len(text) == 0:
                text = output.stderr
            #log.info(text)
            return text
        except SubprocessError as e:
            log.critical("checkout failed for {0}".format(self.pid_bid), e, exc_info=True)
            raise e

    def compile_command(self) -> str:
        return self.cmd_base() + " compile"

    def test_command(self, relevant_tests=True) -> str:
        cmd = self.cmd_base() + " test"
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

    def get_failing_tests(self) -> List[str]:
        if self.failing_tests is not None:
            return self.failing_tests
        try:
            text = self.export_prop('tests.trigger')
            self.failing_tests = text.split('\n')
            return self.failing_tests
        except SubprocessError as e:
            log.critical("get_failing_tests failed for {0}".format(self.pid_bid), e, exc_info=True)
            raise e

    def export_prop(self, prop: str) -> str:
        log.debug('get_failing_tests {0}'.format(self.pid_bid))
        cmd = self.d4j_exec_path() + " export -p {0} -w {1}".format(prop, self.repo_path)
        log.debug('-- executing shell cmd = {0}'.format(cmd))
        output = shell_call(cmd)
        text = output.stdout
        if len(text) == 0:
            text = output.stderr
        elif '$' in text:
            # ${test.classes.dir} ${classes.dir} are sometimes in the output.
            log.warning('$ character is in the result: this can cause issues.')
            log.warning(text)
        return text
