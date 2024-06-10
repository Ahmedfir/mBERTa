import concurrent
import concurrent.futures
import json
import logging
import multiprocessing
import sys
from concurrent.futures import ProcessPoolExecutor
from os import listdir
from os.path import isdir
from pathlib import Path
from typing import List

from tqdm import tqdm

from cb.replacement_mutants import ReplacementMutant
from codebertnt.locs_request import BusinessFileRequest
from mavenrunner.mvn_project import MvnProject
from mbertntcall.mbert_ext_request_impl import MbertRequestImpl
from utils.file_read_write import write_csv_row

log = logging.getLogger(__name__)
log.addHandler(logging.StreamHandler(sys.stdout))


def process_mutant(mutant: ReplacementMutant, repo_path, projects: List[MvnProject], mutants_csv_file,
                   output_csv_lock, mutant_classes_output_dir, patch_diff, java_file):
    # select project that is not locked and lock it
    p = next(x for x in projects if x.acquire())
    log.debug('{0} - in {1}'.format(str(mutant.id), p.repo_path))
    #  adapt the file path to this project
    mutant.file_path = mutant.file_path.replace(repo_path, p.repo_path)
    try:
        #  compile and execute the mutant
        mutant.compile_execute(p, mutant_classes_output_dir, patch_diff=patch_diff, java_file=java_file)
    finally:
        #  unlock project
        p.lock.release()

    log.info('csv - {0} - in {1}'.format(str(mutant.id), p.repo_path))

    res = [mutant.id, mutant.compilable]
    try:
        if mutant.broken_tests is None:
            res = res + [None, None]
        else:
            res.append([t.class_name + '.' + t.method_name for t in mutant.broken_tests])
            res.append(json.dumps([t.json() for t in mutant.broken_tests]))
        # lock the csv file to print to it
        with output_csv_lock:
            # print line to csv
            write_csv_row(mutants_csv_file, res)
            # unlock the csv file, after <with>.
    except BaseException as e:
        log.error(e)
        log.critical("Failed to write mutant to the output csv. Please contact support with full trace", e)
        log.critical("Collected res: {0}".format(str(res)))
        log.critical("Mutant: {0}".format(str(mutant.__dict__)))
        raise e


class MvnRequest(MbertRequestImpl):

    def __init__(self, project: MvnProject, *args, **kargs):
        super(MvnRequest, self).__init__(project, *args, **kargs)

    def preprocess(self) -> bool:
        if not isdir(self.project.repo_path) or len(listdir(self.project.repo_path)) == 0 or (
                self.project.rev_id is not None and len(
            self.project.rev_id) > 0):  # whenever a revision id we recheckout
            # checkout revision version of the project and check that it's valid.
            res = self.project.checkout_validate_fixed_version()
        else:  # we simply use the local version without checkout
            res = self.project.validate_fixed_version_project()
            # remove comments.
            res = res and (not self.project.no_comments or self.project.remove_comments_from_repo())

        if res:
            if self.file_requests is None or len(self.file_requests) == 0:
                self.file_requests = {BusinessFileRequest(str(file))
                                      for file in Path(self.project.repo_path).rglob('*.java') if
                                      'test/java' not in str(file)}
            if self.file_requests is None or len(self.file_requests) == 0:
                raise Exception("Exiting! No java source file found.")
            return True
        else:
            return False

    def csv_header(self):
        return ['id', 'compilable', 'broken_tests', 'broken_tests_reason']

    def create_project_copies(self):
        if self.project.vcs_url is not None and len(self.project.vcs_url) > 0:
            copies_project = self.project.copy(self.max_processes_number - 1)
            for p in copies_project:
                try:
                    p.checkout()
                    self.projects.append(p)
                except BaseException as e:
                    log.error('could not checkout project {0}'.format(p), e)
                    break
        else:
            log.warning("Currently parallel mutants testing is only enabled when a -git_url is given.")

    def process_mutants(self, mutants: List[ReplacementMutant], mutant_classes_output_dir=None, patch_diff=False,
                        java_file=False):
        self.projects = [self.project]
        if len(mutants) > self.max_processes_number:
            # create copies of the repo to parallellise the mutants processing.
            self.create_project_copies()
        self.max_processes_number = len(self.projects)

        with ProcessPoolExecutor(
                max_workers=self.max_processes_number) as executor:
            try:
                m = multiprocessing.Manager()
                # set a lock to the output csv
                output_csv_lock = m.Lock()
                # set a lock to every project
                for p in self.projects:
                    lock = m.Lock()
                    p.set_lock(lock)

                futures = {
                    executor.submit(process_mutant, mutant, self.repo_path, self.projects, self.mutants_csv_file,
                                    output_csv_lock
                                    , mutant_classes_output_dir, patch_diff, java_file): mutant.id
                    for mutant in mutants}
                for future in concurrent.futures.as_completed(futures):
                    kwargs = {
                        'total': len(futures),
                        'unit': 'mutants',
                        'unit_scale': True,
                        'leave': False
                    }
                    # Print out the progress as tasks complete
                    for f in tqdm(concurrent.futures.as_completed(futures), **kwargs):
                        pass
            except BaseException as e:
                log.error(e)
                executor.shutdown()
                self.on_failed("mutants_exec")
                raise
