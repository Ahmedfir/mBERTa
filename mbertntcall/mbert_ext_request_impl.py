import concurrent
import concurrent.futures
import logging
import multiprocessing
import sys
from concurrent.futures import ProcessPoolExecutor
from typing import List

from tqdm import tqdm

from cb.replacement_mutants import ReplacementMutant
from mbertntcall.mbert_ext_request import MbertAdditivePatternsLocationsRequest
from mbertntcall.mbert_project import MbertProject
from utils.file_read_write import write_csv_row

log = logging.getLogger(__name__)
log.addHandler(logging.StreamHandler(sys.stdout))


class MbertRequestImpl(MbertAdditivePatternsLocationsRequest):
    def __init__(self, project: MbertProject, max_processes_number=4, remove_project_on_exit=True, *args, **kargs):
        super(MbertRequestImpl, self).__init__(*args, **kargs)
        self.project: MbertProject = project
        self.max_processes_number = max_processes_number
        self.projects = None
        self.remove_project_on_exit = remove_project_on_exit

    def preprocess(self) -> bool:
        # checkout fixed version of the project and check that it's valid, i.e. compiles and all tests are passing.
        return True

    @staticmethod
    def process_mutant(mutant: ReplacementMutant, repo_path, projects: List[MbertProject], mutants_csv_file,
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

        # lock the csv file to print to it
        with output_csv_lock:
            # print line to csv
            write_csv_row(mutants_csv_file, [mutant.id, mutant.compilable, mutant.broken_tests])
            # unlock the csv file

    def create_project_copies(self):
        copies_project = self.project.copy(self.max_processes_number - 1)
        for p in copies_project:
            try:
                p.copy_content_from(self.project.repo_path)
                self.projects.append(p)
            except BaseException as e:
                log.error('could not copy project {0}'.format(p), e)
                break

    def process_mutants(self, mutants: List[ReplacementMutant], mutant_classes_output_dir=None, patch_diff=False,
                        java_file=False):
        self.projects = [self.project]
        if len(mutants) > self.max_processes_number:
            # create copies of the repo to parallellise the mutants processing.
            self.create_project_copies()
        self.max_processes_number = len(self.projects)

        with ProcessPoolExecutor(max_workers=self.max_processes_number) as executor:
            try:
                m = multiprocessing.Manager()
                # set a lock to the output csv
                output_csv_lock = m.Lock()
                # set a lock to every project
                for p in self.projects:
                    lock = m.Lock()
                    p.set_lock(lock)

                futures = {
                    executor.submit(MbertRequestImpl.process_mutant, mutant, self.repo_path, self.projects,
                                    self.mutants_csv_file,
                                    output_csv_lock, mutant_classes_output_dir, patch_diff, java_file): mutant.id for
                    mutant in mutants}
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
                raise e

    def has_executed(self) -> bool:
        return super(MbertRequestImpl, self).has_executed() or (
                self.has_mutants_csv_output() and self.has_treated_all_mutants(
            self.get_remaining_mutants_to_process()))

    def on_exit(self, reason):
        super(MbertRequestImpl, self).on_exit(reason)
        if self.remove_project_on_exit:
            self.project.remove()
        elif self.project.no_comments:
            # Checkout the project newly without removing the commits.
            self.project.no_comments = False
            self.project.checkout()
        if self.projects is not None and len(self.projects) > 0:
            if not self.remove_project_on_exit and self.project in self.projects:
                self.projects.remove(self.project)
            for p in self.projects:
                p.remove()

    def on_failed(self, reason):
        self.print_progress('failed', reason)
        if self.remove_project_on_exit:
            self.project.remove()
        if self.projects is not None and len(self.projects) > 0:
            if not self.remove_project_on_exit and self.project in self.projects:
                self.projects.remove(self.project)
            for p in self.projects:
                p.remove()
