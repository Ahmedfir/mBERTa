import datetime
import logging
import sys
from os import makedirs
from os.path import join, isfile, isdir
from pathlib import Path
from typing import List

import pandas as pd
from pandas import DataFrame

from cb import PREDICTIONS_FILE_NAME, predict_json_locs, CodeBertMlmFillMask, ListFileLocations, CodeT5FillMask
from cb.code_bert_mlm import MAX_TOKENS, MAX_BATCH_SIZE
from cb.job_config import NOCOSINE_JOB_CONFIG
from cb.replacement_mutants import ReplacementMutant
from codebertnt.locs_request import LOCATIONS_FILE_NAME, MUTANTS_OUTPUT_CSV, BUSINESS_LOCATIONS_JAR, BusinessFileRequest
from codebertnt.rank_lines import order_lines_by_naturalness
from commons.pickle_utils import save_zipped_pickle, load_zipped_pickle
from mbertntcall.json_ap_mc_parser import ApMcListFileLocations, predict_ap_mc_locs
from utils.cmd_utils import shellCallTemplate
from utils.file_read_write import write_csv_row
from utils.file_search import contains

log = logging.getLogger(__name__)
log.addHandler(logging.StreamHandler(sys.stdout))

MBERT_ADDITIVE_PATTERNS_JAR = join(Path(__file__).parent,
                                   'mBERT-addconditions/mbert-additive-patterns-1.0-SNAPSHOT-jar-with-dependencies.jar')
ADDITIVE_PATTERNS_FILE_NAME = 'add_predicates.json'

LLM_MAP = {
    "codeBERT": CodeBertMlmFillMask,
    "codeT5": CodeT5FillMask
}


class MbertAdditivePatternsLocationsRequest:

    def __init__(self, file_requests: List[BusinessFileRequest], repo_path: str, output_dir: str, preds_output_dir=None,
                 mutants_output_dir=None,
                 locs_file=LOCATIONS_FILE_NAME,
                 add_patterns_mc=ADDITIVE_PATTERNS_FILE_NAME,
                 pickle_file_name=PREDICTIONS_FILE_NAME,
                 ap_mc_pickle_file_name='ap_mc_' + PREDICTIONS_FILE_NAME,
                 mutants_test_csv_file=MUTANTS_OUTPUT_CSV,
                 job_config=NOCOSINE_JOB_CONFIG,
                 progress_file='p_log.out',
                 force_reload=False,
                 auto_path_adapt=True,
                 simple_only=False,
                 max_size=MAX_TOKENS,
                 mutant_classes_output_dir=None, patch_diff=False, java_file=False, mask_full_if_conditions=False,
                 model=None):
        self.mask_full_if_conditions = mask_full_if_conditions
        self.repo_path: str = str(Path(repo_path).absolute())
        self.file_requests: List[BusinessFileRequest] = file_requests
        self.output_dir = output_dir
        self.locs_output_file = join(output_dir, locs_file)
        self.ap_mc_output_file = join(output_dir, add_patterns_mc)
        self.force_reload = force_reload
        self.progress_file = join(output_dir, progress_file)
        if preds_output_dir is None:
            preds_output_dir = output_dir
        self.preds_output_dir = preds_output_dir
        self.locs_preds_pickle_file = join(preds_output_dir, pickle_file_name)
        self.ap_mc_preds_pickle_file = join(preds_output_dir, ap_mc_pickle_file_name)
        if mutants_output_dir is None:
            mutants_output_dir = output_dir
        self.mutants_output_dir = mutants_output_dir
        self.mutants_csv_file = join(mutants_output_dir, mutants_test_csv_file)
        self.job_config = job_config
        self.auto_path_adapt = auto_path_adapt
        self.simple_only = simple_only
        self.pred_max_size = max_size
        self.mutated_classes_output_dir = mutant_classes_output_dir
        self.patch_diff = patch_diff
        self.java_file = java_file
        self.model = model

    def has_call_output(self) -> bool:
        return self.has_locs_output() and (self.simple_only or self.has_ap_mc_output())

    def has_locs_output(self) -> bool:
        return isfile(self.locs_output_file)

    def has_locs_preds_output(self) -> bool:
        return isfile(self.locs_preds_pickle_file)

    def has_ap_mc_output(self) -> bool:
        return isfile(self.ap_mc_output_file)

    def has_mutants_csv_output(self) -> bool:
        return isfile(self.mutants_csv_file)

    def has_ap_mc_preds_output(self) -> bool:
        return isfile(self.ap_mc_preds_pickle_file)

    def to_str(self) -> str:
        fr = set(filter(None, {s.to_str(self.repo_path) for s in self.file_requests}))
        if len(fr) > 0:
            return " ".join(fr) + " " + "-out=" + self.output_dir
        else:
            log.error('MbertLocationsRequest failed to collect any input files {0}'.format(self.repo_path))
            return None

    def has_executed(self) -> bool:
        line_done = self.locs_output_file + ',exit,has_treated_all_mutants'
        return self.progress_file is not None and contains(self.progress_file, line_done)

    def print_progress(self, status, reason):
        if self.progress_file is not None:
            with open(self.progress_file, mode='a') as p_file:
                print(self.locs_output_file + ',' + status + ',' + reason, file=p_file)

    def _call_jar(self, request: str, jdk_path: str, jar_path: str, vm_options='') -> str:

        vm_opt = ' ' + vm_options if len(vm_options) > 0 else ''
        cmd = ("JAVA_HOME='" + jdk_path + "' " + join(jdk_path, 'bin',
                                                      'java') + vm_opt + " -jar " + jar_path + " " + request)
        print("call jar cmd ... {0}".format(cmd))
        return shellCallTemplate(cmd)

    def _call_mbert_locs(self, jdk_path: str, mbert_locs_jar_path: str) -> bool:
        request = self.to_str()
        if request is None:
            log.error('Empty request {0}'.format(self.repo_path))
            return False
        if self.mask_full_if_conditions:
            output = self._call_jar(request, jdk_path, mbert_locs_jar_path, vm_options="-DIF_CONDITIONS_AS_TKN=True")
        else:
            output = self._call_jar(request, jdk_path, mbert_locs_jar_path)
        log.info(output)
        return self.has_locs_output()

    def _call_mbert_ap_mc(self, jdk_path: str, mbert_ap_mc_jar_path: str) -> bool:
        request = self.to_str()
        if request is None:
            log.error('Empty request {0}'.format(self.repo_path))
            return False
        output = self._call_jar(request, jdk_path, mbert_ap_mc_jar_path)
        log.info(output)
        return self.has_ap_mc_output()

    def preprocess(self) -> bool:
        return isdir(self.repo_path)

    def predict_simple_mutants(self, jdk_path: str, prediction_cost_results_file: str,
                               mbert_locs_jar_path: str = BUSINESS_LOCATIONS_JAR, batch_size=MAX_BATCH_SIZE):
        self.print_progress('info', 'call')
        if not self.force_reload and self.has_executed():
            log.error('has_treated_all_mutants')
            return None
        if not self.preprocess():
            log.error('exit_preprocess')
            return None
        if not self.has_locs_output():
            if not self._call_mbert_locs(jdk_path, mbert_locs_jar_path):
                log.error('exit_call_mbert_locs')
                return None
        start = datetime.datetime.now()
        raw_mutants = self.predict_on_mbert_locs(batch_size=batch_size)
        pred_time = datetime.datetime.now() - start
        print('prediction took : {0} '.format(str(pred_time)))
        if prediction_cost_results_file is not None:
            if not isdir(Path(prediction_cost_results_file).parent):
                makedirs(Path(prediction_cost_results_file).parent)
            with open(prediction_cost_results_file, mode='a') as p_file:
                print(self.locs_output_file + ',' + str(raw_mutants.last_id() + 1) + ',' + str(pred_time), file=p_file)
        return self.locs_output_file

    def call(self, jdk_path: str, mbert_locs_jar_path: str = BUSINESS_LOCATIONS_JAR,
             mbert_ap_mc_jar_path: str = MBERT_ADDITIVE_PATTERNS_JAR) -> str:
        self.print_progress('info', 'call')
        if not self.force_reload and self.has_executed():
            self.on_exit('has_treated_all_mutants')
            return None
        if not self.preprocess():
            self.on_exit('exit_preprocess')
            return None
        if not self.has_locs_output():
            if not self._call_mbert_locs(jdk_path, mbert_locs_jar_path):
                self.on_exit('exit_call_mbert_locs')
                return None
        if not self.simple_only and not self.has_ap_mc_output():
            if not self._call_mbert_ap_mc(jdk_path, mbert_ap_mc_jar_path):
                log.error("call_mbert_ap_mc failed!")
        self.postprocess()
        # self.postprocess() is comnpiling and executing the tests.
        self.on_exit('done')
        # next lines will make sure that "has_treated_all_mutants" flag is added to the progress file.
        if self.has_treated_all_mutants(self.get_remaining_mutants_to_process()):
            self.on_exit('has_treated_all_mutants')
        return self.locs_output_file

    def predict_on_mbert_locs(self, batch_size=MAX_BATCH_SIZE) -> ListFileLocations:
        results: ListFileLocations = None
        if not self.has_locs_output() and not self.has_locs_preds_output():
            log.error('files not found : \n{0} \n{1}'.format(self.locs_output_file, self.locs_preds_pickle_file))
        elif self.force_reload or not self.has_locs_preds_output():
            if self.model is None:
                model_class = LLM_MAP.get("codeBERT")
            else:
                model_class = LLM_MAP.get(self.model)
            cbm = model_class()
            if not isdir(self.preds_output_dir):
                try:
                    makedirs(self.preds_output_dir)
                except FileExistsError:
                    log.debug("two threads created the directory concurrently.")
            results = predict_json_locs(self.locs_output_file, cbm, self.job_config, max_size=self.pred_max_size,
                                        batch_size=batch_size, repo_dir=self.repo_path)
            json = results.json()
            save_zipped_pickle(json, self.locs_preds_pickle_file)
        else:
            results = ListFileLocations.parse_raw(load_zipped_pickle(self.locs_preds_pickle_file))
        return results

    def predict_on_mbert_ap_mc(self, start_mutant_id) -> ApMcListFileLocations:
        results: ApMcListFileLocations = None
        if not self.has_ap_mc_output() and not self.has_ap_mc_preds_output():
            log.error('files not found : \n{0} \n{1}'.format(self.ap_mc_output_file, self.ap_mc_preds_pickle_file))
        elif self.force_reload or not self.has_ap_mc_preds_output():
            cbm = CodeBertMlmFillMask()
            if not isdir(self.preds_output_dir):
                try:
                    makedirs(self.preds_output_dir)
                except FileExistsError:
                    log.debug("two threads created the directory concurrently.")
            results = predict_ap_mc_locs(self.ap_mc_output_file, cbm, start_mutant_id, max_size=self.pred_max_size)
            json = results.json()
            save_zipped_pickle(json, self.ap_mc_preds_pickle_file)
        else:
            results = ApMcListFileLocations.parse_raw(load_zipped_pickle(self.ap_mc_preds_pickle_file))
        return results

    def process_mutants(self, mutants: List[ReplacementMutant], mutant_classes_output_dir=None, patch_diff=False,
                        java_file=False):
        raise Exception("implement this to process your mutants!")

    def csv_header(self):
        return ['id', 'compilable', 'broken_tests']

    def create_output_csv(self):
        write_csv_row(self.mutants_csv_file, self.csv_header())

    def normal_mutants_to_df(self, project_name, version='f', stats=None) -> DataFrame:
        assert self.has_locs_preds_output()
        normal_mutants_df = ListFileLocations.parse_raw(load_zipped_pickle(self.locs_preds_pickle_file)).to_mutants(
            project_name, version, None, None, stats)
        normal_mutants_df['simple_replacement'] = 1
        return normal_mutants_df

    def additive_mutants_to_df(self, project_name, version='f', executed_mutants_ids: List[int] = None) -> DataFrame:
        assert self.has_ap_mc_preds_output()
        df = ApMcListFileLocations.parse_raw(load_zipped_pickle(self.ap_mc_preds_pickle_file)).to_mutants(
            project_name, version, executed_mutants_ids)
        df['simple_replacement'] = 0
        return df

    def lines_order_by_naturalness(self, project_name, version='f', preds_per_token=1, fl_column='fl'):
        if not self.has_locs_preds_output():
            log.error("Couldn't find file:" + self.locs_preds_pickle_file)
            return None
        mutants_df = self.normal_mutants_to_df(project_name, version)
        return order_lines_by_naturalness(mutants_df, preds_per_token=preds_per_token, fl_column=fl_column)

    def load_merged_mutants_results(self, project_name, stats=None, intermediate_pickle_file=None, version='f',
                                    force_reload=False, cached_only=False, compilable_only=True) -> (bool, DataFrame):
        if force_reload or intermediate_pickle_file is None or not isfile(intermediate_pickle_file):
            if cached_only:
                return False, None
            if not self.has_locs_preds_output():
                log.error("Couldn't find file:" + self.locs_preds_pickle_file)
                return False, None
            if not isfile(self.mutants_csv_file):
                log.error("Couldn't find file:" + self.mutants_csv_file)
                return False, None
            exec_results = pd.read_csv(self.mutants_csv_file)
            assert len(exec_results) == exec_results['id'].nunique()
            # executed mutant ids - to know if we're done with the exec step or not.
            treated_ids = list(exec_results['id'].unique())
            if stats is not None:
                stats['treated_ids'] = len(treated_ids)

            if compilable_only:
                # we keep only the exec results of the compilable ones.
                exec_results = exec_results[exec_results['compilable']]
                if len(exec_results) <= 0:
                    log.error("all mutants are not compilable:" + self.mutants_csv_file)
                    return False, None
            mutants_df = self.normal_mutants_to_df(project_name, version, stats)
            if stats is not None:
                stats['simp_no_redundant'] = len(mutants_df)

            if not self.has_ap_mc_preds_output():
                log.error("Couldn't find file:" + self.ap_mc_preds_pickle_file)
            else:
                additive_mutants_df = self.additive_mutants_to_df(project_name, version=version,
                                                                  executed_mutants_ids=treated_ids)
                if stats is not None:
                    stats['all_ap_predictions'] = self.count_additive_predictions()['all_preds'].sum()
                    stats['ap_no_redundant'] = len(additive_mutants_df)
                    stats['ap_dupl'] = stats['all_ap_predictions'] - stats['ap_no_redundant']
                mutants_df = pd.concat([mutants_df, additive_mutants_df], ignore_index=True)

            if len(mutants_df) == 0:
                log.error(" 0 mutants for " + self.repo_path + " : \n ")
                return False, None

            # check that everything has been treated
            assert len(mutants_df) == mutants_df['id'].nunique()
            missing_ids = [i for i in mutants_df['id'].unique() if i not in treated_ids]
            if len(missing_ids) > 0:
                log.error(
                    str(len(missing_ids)) + " mutants were not treated for " + self.repo_path + " : \n ")
                log.debug('mutant ids : ' + str(missing_ids))
                return False, None

            # merge the exec results with the predictions.
            # this dataset may be smaller if you pick only compilable mutants.
            merged_df = pd.merge(mutants_df, exec_results, how="inner", left_on=['id'], right_on=['id'])
            assert len(merged_df) == merged_df['id'].nunique()

            save_zipped_pickle(merged_df, intermediate_pickle_file)
        else:
            merged_df = load_zipped_pickle(intermediate_pickle_file)
        return True, merged_df

    def get_remaining_mutants_to_process(self) -> List[ReplacementMutant]:
        normal_mutants_raw = self.predict_on_mbert_locs()
        if normal_mutants_raw is not None:
            replacement_mutants = normal_mutants_raw.get_mutants_to_exec(
                self.mutants_csv_file)
            if not self.simple_only and self.has_ap_mc_output():
                start_mutant_id = normal_mutants_raw.last_id() + 1
                additive_mutants_raw = self.predict_on_mbert_ap_mc(start_mutant_id)
                replacement_mutants = replacement_mutants + additive_mutants_raw.get_mutants_to_exec(
                    self.mutants_csv_file)
            return [mutant for file in replacement_mutants for mutant in file.mutants]
        return []

    def has_treated_all_mutants(self, replacement_mutants):
        log.debug("remaining mutants to process = " + str(len(replacement_mutants)) + " for " + self.repo_path)
        return len(replacement_mutants) == 0

    def postprocess(self):
        log.info("post processing mutants")
        replacement_mutants = self.get_remaining_mutants_to_process()
        if not self.has_treated_all_mutants(replacement_mutants):
            if not isfile(self.mutants_csv_file):
                if not isdir(self.mutants_output_dir):
                    try:
                        makedirs(self.mutants_output_dir)
                    except FileExistsError:
                        log.debug("two threads created the directory concurrently.")
                self.create_output_csv()
            if self.auto_path_adapt:
                self.auto_adapt_paths(replacement_mutants)
            self.process_mutants(replacement_mutants, mutant_classes_output_dir=self.mutated_classes_output_dir,
                                 patch_diff=self.patch_diff, java_file=self.java_file)
        else:
            self.on_exit('has_treated_all_mutants')

    def auto_adapt_paths(self, replacement_mutants):
        for m in replacement_mutants:
            if not isfile(m.file_path):
                repo_dir = Path(self.repo_path).name
                if repo_dir in m.file_path:
                    m.file_path = self.repo_path + m.file_path.split(repo_dir)[1]
                else:
                    m.file_path = self.repo_path + m.file_path

                assert isfile(m.file_path), 'auto_path_adapt failed to fix absolute mutant file path \n' \
                                            '-> adapted path : {0}'.format(m.file_path)

    def get_not_printed_mutants(self, project_name, intermediate_pickle_file, bin_f=False) -> List[ReplacementMutant]:
        b, df = self.load_merged_mutants_results(project_name, intermediate_pickle_file=intermediate_pickle_file)
        if not b:
            return []
        mutants = [ReplacementMutant(id, file_path, start, end, replacement) for
                   id, file_path, start, end, replacement in
                   zip(df['id'].astype(int), df['file_path'].astype(str), df['start_pos'].astype(int),
                       df['end_pos'].astype(int) + df['simple_replacement'].astype(int),
                       # dirtiest quick-fix in history  ever:
                       # a bug was introduced at some point about the end-index for the simple mutants.
                       df['pred_token'].astype(str))]
        if not isdir(self.mutated_classes_output_dir):
            mutants_to_print = mutants
        else:
            mutants_to_print = [m for m in mutants if not
            isfile(m.mutated_output_bin_file(self.mutated_classes_output_dir) if bin_f else m.mutated_output_java_file(
                self.mutated_classes_output_dir))]

        return mutants_to_print

    def on_exit(self, reason):
        self.print_progress('exit', reason)

    def count_additive_predictions(self) -> DataFrame:
        assert self.has_ap_mc_preds_output()
        df = ApMcListFileLocations.parse_raw(load_zipped_pickle(self.ap_mc_preds_pickle_file)).count_predictions()
        return df
