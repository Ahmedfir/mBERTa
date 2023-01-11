import concurrent
import concurrent.futures
import logging
import multiprocessing
import sys
from concurrent.futures import ProcessPoolExecutor
from typing import List

from tqdm import tqdm

from cb.replacement_mutants import ReplacementMutant, TESTS_TIME_OUT_RESULT
from mbertnteval.d4jeval.d4j_project import D4jProject
from mbertntcall.mbert_ext_request_impl import MbertRequestImpl
from mbertnteval.sim_utils import calc_ochiai
from utils.file_read_write import write_csv_row

log = logging.getLogger(__name__)
log.addHandler(logging.StreamHandler(sys.stdout))


def process_mutant(mutant: ReplacementMutant, repo_path, projects: List[D4jProject], mutants_csv_file,
                   output_csv_lock, broken_tests_orig_bug, mutant_classes_output_dir, patch_diff, java_file):
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

    # calculate ochiai and coupling
    if not mutant.compilable or mutant.broken_tests is None or TESTS_TIME_OUT_RESULT == mutant.broken_tests or len(
            mutant.broken_tests) == 0:
        ochiai = 0.0
        is_coupled = False
    else:
        ochiai = calc_ochiai(mutant.broken_tests, broken_tests_orig_bug)
        is_coupled = len(mutant.broken_tests) > 0 and set(mutant.broken_tests).issubset(set(broken_tests_orig_bug))

    log.info('csv - {0} - in {1}'.format(str(mutant.id), p.repo_path))

    # lock the csv file to print to it
    with output_csv_lock:
        # print line to csv
        write_csv_row(mutants_csv_file, [mutant.id, mutant.compilable, mutant.broken_tests, ochiai, is_coupled])
        # unlock the csv file


class D4jRequest(MbertRequestImpl):

    def __init__(self, project: D4jProject, *args, **kargs):
        super(D4jRequest, self).__init__(project, *args, **kargs)

    def preprocess(self) -> bool:
        # checkout fixed version of the project and check that it's valid.
        return self.project.checkout_validate_fixed_version()

    def csv_header(self):
        return ['id', 'compilable', 'broken_tests', 'ochiai', 'is_coupled']

    def create_project_copies(self):
        copies_project = self.project.copy(self.max_processes_number - 1)
        for p in copies_project:
            try:
                p.checkout()
                self.projects.append(p)
            except BaseException as e:
                log.error('could not checkout project {0}'.format(p), e)
                break

    def process_mutants(self, mutants: List[ReplacementMutant], mutant_classes_output_dir=None, patch_diff=False, java_file=False):
        self.projects = [self.project]
        if len(mutants) > self.max_processes_number:
            # create copies of the repo to parallellise the mutants processing.
            self.create_project_copies()
        self.max_processes_number = len(self.projects)

        # load this only once.
        broken_tests_orig_bug = self.project.get_failing_tests()

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
                                    output_csv_lock,
                                    broken_tests_orig_bug, mutant_classes_output_dir, patch_diff, java_file): mutant.id for mutant in mutants}
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
