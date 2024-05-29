import logging
import shutil
import sys
from copy import deepcopy
from os import makedirs
from os.path import join, isdir
from pathlib import Path
from subprocess import SubprocessError, TimeoutExpired
from typing import List

from commentsremover.comments_remover import remove_comments_from_repo
from utils.cmd_utils import safe_chdir, shell_call, DEFAULT_TIMEOUT_S

log = logging.getLogger(__name__)
log.addHandler(logging.StreamHandler(sys.stdout))


class MbertProject:

    def __init__(self, repo_path, jdk_path, class_path, test_class_path, repos_path='/tmp_large_mem',
                 no_comments=False):
        self.repos_path = repos_path
        self.repo_path = repo_path
        self.jdk = jdk_path
        self.lock = None
        self.class_path = class_path
        self.test_class_path = test_class_path
        self.no_comments = no_comments

    def remove_comments_from_repo(self, check_compile=True,
                                  vm_options="-Xms1024m -Xmx1024m -Xss512m"):

        output = remove_comments_from_repo(self.repo_path, jdk=self.jdk, vm_options=vm_options)
        log.info(output)
        if check_compile:
            return self.compile()
        else:
            log.warning("skipping compilation check after removing")
            return True

    def __deepcopy__(self, memo):
        cls = self.__class__
        result = cls.__new__(cls)
        memo[id(self)] = result
        for k, v in self.__dict__.items():
            setattr(result, k, deepcopy(v, memo))
        return result

    def set_lock(self, lock):
        self.lock = lock

    def acquire(self, block=False) -> bool:
        return self.lock is not None and self.lock.acquire(blocking=block)

    def cp(self, n):
        repos_path = join(self.repos_path, 'c_' + str(n))
        if not isdir(repos_path):
            try:
                makedirs(repos_path)
            except FileExistsError:
                log.debug("two threads created the directory concurrently.")
        copy = deepcopy(self)
        copy.repos_path = repos_path
        copy.repo_path = join(repos_path, Path(self.repo_path).name)
        return copy

    def copy_content_from(self, src_dir):
        destination = shutil.copytree(src_dir, self.repo_path)
        log.info('copied {0} to {1}'.format(src_dir, destination))

    def copy(self, number):
        return [self.cp(n) for n in range(number)]

    def remove(self):
        if isdir(self.repo_path):
            shutil.rmtree(self.repo_path)

    def compile_command(self) -> str:
        return "JAVA_HOME='" + self.jdk + "' -cp " + self.class_path

    def test_command(self, *args, **kargs) -> str:
        return "JAVA_HOME='" + self.jdk + "' -cp " + self.test_class_path

    def on_has_compiled(self, output) -> bool:
        text = output.stdout
        if len(text) == 0:
            text = output.stderr
        log.debug(text)
        return text.strip().endswith(
            'Running ant (compile.tests)................................................ OK')

    def compile(self) -> bool:
        with safe_chdir(self.repo_path):
            log.debug('compiling {0}'.format(self.repo_path))
            cmd = self.compile_command()
            log.info('-- executing shell cmd = {0}'.format(cmd))
            try:
                output = shell_call(cmd)
                return self.on_has_compiled(output)
            except SubprocessError as e:
                log.debug("compilation failed for {0}".format(self.repo_path), e, exc_info=True)
                return False

    def on_tests_run(self, test_exec_output) -> List[str]:
        broken_tests = []
        text = test_exec_output.stdout
        if len(text) == 0:
            text = test_exec_output.stderr
        if not text.strip().endswith('Failing tests: 0'):
            #  ['  - org.apache.commons.math3.fraction.BigFractionTest::testDigitLimitConstructor']
            broken_tests = [t.replace('  - ', '').strip() for t in text.split('\n')[1:] if len(t.strip()) > 0]
        return broken_tests

    def test(self, timeout=DEFAULT_TIMEOUT_S) -> List[str]:
        """test project"""
        with safe_chdir(self.repo_path):
            log.debug('testing {0}'.format(self.repo_path))
            cmd = self.test_command()
            log.info('-- executing shell cmd = {0}'.format(cmd))
            try:
                output = shell_call(cmd, timeout=timeout)
                return self.on_tests_run(output)
            except TimeoutExpired as te:
                log.debug('timeout')
                raise te
            except SubprocessError as e:
                log.critical("compilation failed for {0}".format(self.repo_path), e, exc_info=True)
                raise e
