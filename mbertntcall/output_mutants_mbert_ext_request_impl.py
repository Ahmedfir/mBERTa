from typing import List

from cb.replacement_mutants import ReplacementMutant
from commons.pool_executors import process_parallel_run
from mbertntcall.mbert_ext_request import MbertAdditivePatternsLocationsRequest
from utils.file_read_write import load_file


class OutputMutatedClasses(MbertAdditivePatternsLocationsRequest):

    def __init__(self, mutated_classes_output_dir, max_processes_number=16, *args, **kargs):
        super(OutputMutatedClasses, self).__init__(*args, **kargs)
        self.max_processes_number = max_processes_number
        self.mutated_classes_output_dir = mutated_classes_output_dir

    @staticmethod
    def process_mutant(mutant: ReplacementMutant, output_dir: str, tmp_original_file):
        mutant.output_mutated_file(output_dir, tmp_original_file)

    def process_mutants(self, mutants: List[ReplacementMutant]):
        mutants_by_file = {f: [m for m in mutants if m.file_path == f] for f in {m.file_path for m in mutants}}
        for f in mutants_by_file:
            process_parallel_run(self.process_mutant, mutants_by_file[f], self.mutated_classes_output_dir, load_file(f),
                                 max_workers=self.max_processes_number)