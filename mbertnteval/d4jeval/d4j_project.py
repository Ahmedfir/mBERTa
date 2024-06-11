import logging
import sys
from os import listdir, makedirs
from os.path import join, isdir, isfile
from pathlib import Path
from subprocess import SubprocessError, TimeoutExpired, CompletedProcess
from typing import List

import pandas as pd

from mbertntcall.mbert_project import MbertProject
from utils import file_read_write
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


def scc_kolcs(in_path, output_file):
    if isinstance(in_path, str):
        target_paths = in_path
    elif isinstance(in_path, list):
        target_paths = ' '.join(in_path)
    else:
        raise Exception('IllegalArgumentException {0} as in_path for scc_klocs'.format(in_path))
    target_paths = target_paths.replace('$', "\$")
    if not isdir(Path(output_file).parent):
        makedirs(Path(output_file).parent)
    cmd = 'scc ' + target_paths + ' -f csv -o ' + output_file
    try:
        output = shell_call(cmd)
        text = output.stdout
        if len(text) == 0:
            text = output.stderr
        # log.info(text)
        return text
    except SubprocessError as e:
        log.critical("scc_kolcs failed for {0}".format(str(in_path)), e, exc_info=True)
        raise e


def coverage_output_line_to_tuple(line):
    assert len(line) > 0
    splits = line.split(':')
    col = splits[0]
    val = splits[1].strip()
    if val.endswith('%'):
        return col, float(val.replace('%', ''))
    else:
        return col, int(val)


def coverage_to_csv(output: CompletedProcess, csv_file):
    assert len(output.stdout.strip()) > 0
    out_lines = list(
        map(lambda x: coverage_output_line_to_tuple(x),
            {l.strip() for l in output.stdout.split('\n') if l and len(l.split(':')) == 2}))
    pd.DataFrame(out_lines, columns=['k', 'v'], index=None).set_index('k').transpose().to_csv(csv_file, index=False)


class D4jProject(MbertProject):
    def __init__(self, d4j_path, repos_path, pid, bid, jdk8, jdk7=None, version='f', no_comments=False, tests_timeout=DEFAULT_TIMEOUT_S):
        super(D4jProject, self).__init__(None, None, None, None, repos_path, no_comments, tests_timeout=tests_timeout)
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
        self.source_dir = None
        self.bin_dir = None
        self.target_classes = None

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

    def checkout_compile_buggy_version(self, jdk=None, force_reload=False):
        assert 'b' == self.version
        if jdk is not None:
            self.jdk = jdk
        elif self.jdk is None:
            self.jdk = self.jdk8
        else:
            return True
        self.checkout(force_reload=force_reload)

        try:
            failed = not self.compile()

        except SubprocessError:
            failed = True

        if failed:
            self.jdk = None
            if jdk is not None or self.jdk7 is None:
                return False
            else:
                return self.checkout_compile_buggy_version(self.jdk7)
        else:
            return True

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
            log.debug(text)
            return isdir(self.repo_path) and len(listdir(self.repo_path)) > 0 and (
                    not self.no_comments or self.remove_comments_from_repo())  # remove comments
        except SubprocessError as e:
            log.critical("checkout failed for {0}".format(self.pid_bid), e, exc_info=True)
            raise e

    def compile_command(self) -> str:
        return self.cmd_base() + " compile"

    def coverage_command(self, relevant_tests=True) -> str:
        cmd = self.cmd_base() + " coverage"
        if self.relevant_tests_exec_only_possible and relevant_tests:
            cmd = cmd + " -r"
        return cmd

    def test_command(self, relevant_tests=True) -> str:
        cmd = self.cmd_base() + " test"
        if self.relevant_tests_exec_only_possible and relevant_tests:
            cmd = cmd + " -r"
        return cmd

    def test(self, relevant_tests=True) -> List[str]:
        """test project"""
        with safe_chdir(self.repo_path):
            log.debug('testing {0} in {1}'.format(self.pid_bid, self.repo_path))
            cmd = self.test_command(relevant_tests)
            log.info('-- executing shell cmd = {0}'.format(cmd))
            try:
                output = shell_call(cmd, timeout=self.tests_timeout)
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
        cmd = self.cmd_base() + " export -p {0} -w {1}".format(prop, self.repo_path)
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

    def get_src_dir(self):
        if self.source_dir is None:
            self.source_dir = self.export_prop('dir.src.classes')
        return self.source_dir

    def get_modified_classes(self):
        if self.target_classes is None:
            self.target_classes = self.export_prop('classes.modified')
        return self.target_classes

    def output_project_klocs(self, file_project_klocs, force_reload=False):
        if force_reload or not isfile(file_project_klocs):
            repo = join(self.repo_path, self.get_src_dir())
            exec_res = scc_kolcs(repo, file_project_klocs)
            assert isfile(file_project_klocs), exec_res

    def get_target_file_paths(self):
        return [join(self.repo_path, self.get_src_dir(), f.replace('.', '/') + '.java') for f in
                self.get_modified_classes().split('\n') if f]

    def output_target_classes_klocs(self, file_target_classes_klocs, target_files=None, force_reload=False):
        if force_reload or not isfile(file_target_classes_klocs):
            if target_files is None:
                target_files = self.get_target_file_paths()
            exec_res = scc_kolcs(list(target_files), file_target_classes_klocs)
            assert isfile(file_target_classes_klocs), exec_res

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

    def output_target_classes_coverage(self, file_target_classes_coverage, timeout=DEFAULT_TIMEOUT_S,
                                       relevant_tests=True, force_reload=False):
        if force_reload or not isfile(file_target_classes_coverage):
            """coverage of impacted classes project"""
            with safe_chdir(self.repo_path):
                log.debug('coverage {0} in {1}'.format(self.pid_bid, self.repo_path))
                cmd = self.coverage_command(relevant_tests)
                log.info('{1} -- executing shell cmd = {0}'.format(cmd, self.pid_bid))
                try:
                    output = shell_call(cmd, timeout=timeout)
                    file_read_write.write_file(join(Path(file_target_classes_coverage).parent,
                                                    'raw_' + Path(file_target_classes_coverage).name.replace('.csv',
                                                                                                             '.txt')),
                                               str(output))
                    coverage_to_csv(output, file_target_classes_coverage)
                    return output
                except TimeoutExpired as te:
                    log.critical('{0} timeout'.format(self.pid_bid), te, exc_info=True)
                    raise te
                except SubprocessError as e:
                    log.critical("coverage failed for {0}".format(self.pid_bid), e, exc_info=True)
                    raise e

    def output_tests_count(self, file_relevant_tests_count, force_reload=False):
        if force_reload or not isfile(file_relevant_tests_count):
            relevant_tests = {t for t in self.export_prop('tests.relevant').strip().split('\n') if t}
            all_tests = {t for t in self.export_prop('tests.all').strip().split('\n') if t}
            relevant_only_possible = self.relevant_tests_exec_only_possible
            if not isdir(Path(file_relevant_tests_count).parent):
                makedirs(Path(file_relevant_tests_count).parent)
            file_read_write.write_file(file_relevant_tests_count,
                                       'pi_bid,count_relevant_tests,count_all_tests,relevant_only_possible\n'
                                       '{0},{1},{2},{3}\n'.format(self.pid_bid,
                                                                  str(len(relevant_tests)),
                                                                  str(len(all_tests)),
                                                                  str(relevant_only_possible)))
