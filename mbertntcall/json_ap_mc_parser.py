import logging
import sys
from enum import Enum
from os.path import isfile
from typing import List, Dict

import pandas as pd
from pandas import DataFrame
from pydantic import BaseModel

from cb.code_bert_mlm import CodeBertMlmFillMask, MAX_TOKENS, MASK, \
    ListCodeBertPrediction
from cb.json_locs_parser import Mutant
from cb.predict_json_locs import cut_method, surround_method, load_file
from cb.replacement_mutants import FileReplacementMutants, ReplacementMutant, DetailedReplacementMutant

log = logging.getLogger(__name__)
log.addHandler(logging.StreamHandler(sys.stdout))


class PredicateAstType(Enum):
    do_stmt = 19
    return_stmt = 41
    if_stmt = 25
    while_stmt = 61
    conditionalexpression_stmt = 16

    @staticmethod
    def parse(ast_type):
        for name, member in PredicateAstType.__members__.items():
            if ast_type + '_stmt' == name:
                return member
        raise Exception('{0} not implemented '.format(ast_type))


class JavaFile(BaseModel):
    path: str


class ApMcPredicates(BaseModel):
    lineNumber: int
    astStmtType: int
    codeString: str
    start: int
    end: int
    methodStartPos: int
    methodEndPos: int
    newMaskedPredicates: List[str]
    predictions: Dict[str, ListCodeBertPrediction] = None
    unique_predictions: Dict[str, List[int]] = dict()
    start_mutant_id: int = -1
    stripped_unique_preds: Dict[str, List[int]] = None

    @staticmethod
    def _remove_spaces(s: str):
        return " ".join(s.split()).replace(" ", "")

    def is_masked_on_added(self, pred):
        return self._remove_spaces(self.codeString) in self._remove_spaces(pred)

    # todo add an accessor to unique_predictions
    def get_unique_preds(self):
        if self.stripped_unique_preds is None:
            stripped_preds = dict()
            for p in self.unique_predictions.keys():
                s_p = self._remove_spaces(p)
                if s_p in stripped_preds.keys():
                    stripped_preds[s_p].append(p)
                else:
                    stripped_preds[s_p] = [p]
            diff = len(stripped_preds) - len(self.unique_predictions)
            if diff > 0:
                log.info("{0} duplicate predictions ".format(diff))
                self.stripped_unique_preds = {
                    stripped_preds[s_p][0]: [id for p in stripped_preds[s_p] for id in self.unique_predictions[p]] for
                    s_p in stripped_preds}
            else:
                log.info("skip ")
                self.stripped_unique_preds = self.unique_predictions
        return self.stripped_unique_preds

    def process_locs(self, cbm: CodeBertMlmFillMask, file_string: str, start_mutant_id: int,
                     max_size: int = MAX_TOKENS):
        self.start_mutant_id = start_mutant_id
        if self.methodStartPos >= 0 and self.methodEndPos >= 0:
            method_start = self.methodStartPos
            method_end = self.methodEndPos
        else:
            method_start = self.start - 1
            method_end = self.end + 1
        method_string = file_string[method_start: method_end + 1]
        if len(method_string.strip()) == 0:
            log.error('Failed to load method in [ {0} , {1} ] named : {2}'.format(method_start, method_end,
                                                                                  self.lineNumber))
            return

        max_tokens_to_add = max_size
        method_before_str = file_string[max(0, method_start - max_tokens_to_add):method_start - 1]
        method_after_str = file_string[method_end + 1:min(method_end + 1 + max_tokens_to_add, len(file_string) - 1)]
        method_before_tokens = [] if len(method_before_str.strip()) == 0 else cbm.tokenize(method_before_str)
        method_after_tokens = [] if len(method_after_str.strip()) == 0 else cbm.tokenize(method_after_str)

        reqs = []
        for nmp in self.newMaskedPredicates:
            nmp_masked_method = file_string[method_start:self.start] + nmp + file_string[
                                                                             self.end: method_end + 1]
            nmp_masked_method_tokens = cbm.tokenize(nmp_masked_method)
            if len(nmp_masked_method_tokens) < max_size:
                nmp_masked_method_tokens, method_before_tokens, method_after_tokens = surround_method(
                    nmp_masked_method_tokens, method_before_tokens, method_after_tokens, max_size)
            if len(nmp_masked_method_tokens) > max_size:
                start_cutting_index, nmp_masked_method_tokens = cut_method(nmp_masked_method_tokens, max_size,
                                                                           int(max_size / 3), MASK)
            reqs.append(nmp_masked_method_tokens)

        # predict
        masked_codes = [cbm.decode_tokens_to_str(masked_code_tokens_req) for masked_code_tokens_req in reqs]

        for code in masked_codes:
            assert 0 < cbm.tokens_count(code) <= 512

        # predicting...
        predictions_arr_arr = cbm.call_func(masked_codes)

        # checking that nothing is missing else ignore these locs.
        if not (len(predictions_arr_arr) == len(self.newMaskedPredicates) == len(reqs) == len(masked_codes)):
            log.error(
                '{0} locations (tokens) are ignored in line {1} because of a missing param: '
                'masked_code or masked_token'.format(str(len(predictions_arr_arr) - len(self.newMaskedPredicates)),
                                                     str(self.lineNumber)))
            return

        for i in range(len(predictions_arr_arr)):
            predictions_arr_arr[i].add_mutant_id(start_mutant_id)
            start_mutant_id = start_mutant_id + 5

        self.start_mutant_id = start_mutant_id

        #  adding of the prediction matches the masked token.
        self.predictions = {self.newMaskedPredicates[i]: predictions_arr_arr[i]
                            for i in range(len(self.newMaskedPredicates))}

        for p in self.predictions.keys():
            for pred in self.predictions[p].__root__:
                predicate_str = pred.put_token_inplace(p, '')
                if predicate_str in self.unique_predictions.keys():
                    self.unique_predictions[predicate_str].append(pred.id)
                else:
                    self.unique_predictions[predicate_str] = [pred.id]


class ApMcFileLocations(BaseModel):
    javaFile: JavaFile
    allMaskedPredicates: List[ApMcPredicates]
    start_mutant_id = -1

    def process_locs(self, cbm: CodeBertMlmFillMask, start_mutant_id, max_size=MAX_TOKENS):
        self.start_mutant_id = start_mutant_id
        log.info('pred : file {0}'.format(self.javaFile.path))
        try:
            file_string = load_file(self.javaFile.path)
            for pred in self.allMaskedPredicates:
                pred.process_locs(cbm, file_string, self.start_mutant_id, max_size=max_size)
                self.start_mutant_id = pred.start_mutant_id
        except UnicodeDecodeError:
            log.exception('Failed to load file : {0}'.format(self.javaFile.path))


class ApMcListFileLocations(BaseModel):
    fileRequests: List[ApMcFileLocations]
    start_mutant_id = -1

    def process_locs(self, cbm, start_mutant_id, max_size=MAX_TOKENS):
        self.start_mutant_id = start_mutant_id
        for file_loc in self.fileRequests:
            file_loc.process_locs(cbm, self.start_mutant_id, max_size=max_size)
            self.start_mutant_id = file_loc.start_mutant_id

    @staticmethod
    def get_executed_or_first(mutant_ids, executed_mutants_ids) -> int:
        if executed_mutants_ids is not None and len(mutant_ids) > 1 and len(executed_mutants_ids) > 0:
            intersection = set(mutant_ids).intersection(set(executed_mutants_ids))
            if len(intersection) >= 1:
                return sorted(list(intersection))[0]
        return sorted(mutant_ids)[0]

    def to_mutants(self, proj_bug_id, version, no_duplicates=True,
                   executed_mutants_ids: List[int] = None) -> DataFrame:
        return pd.DataFrame(
            [vars(Mutant(proj_bug_id, mutant.id, mutant.cosine, mutant.rank, version, mutant.match_org, mutant.score,
                         fileP.javaFile.path, '', '', maskedPredicates.lineNumber,
                         False, str(maskedPredicates.astStmtType), 'condition_seeding',
                         maskedPredicates.start, maskedPredicates.end,
                         masked_on_added=maskedPredicates.is_masked_on_added(m),
                         old_val=maskedPredicates.codeString, new_val=m))

             for fileP in self.fileRequests
             for maskedPredicates in fileP.allMaskedPredicates
             for m in maskedPredicates.get_unique_preds().keys()
             for predictions_list in maskedPredicates.predictions.values()
             for mutant in self.get_exec_or_1st_no_dupl(predictions_list, maskedPredicates.get_unique_preds()[m],
                                                        executed_mutants_ids, no_duplicates=no_duplicates)
             ])

    def get_exec_or_1st_no_dupl(self, predictions_list, unique_preds, executed_ids, no_duplicates=True):
        res = []
        for mutant in predictions_list.__root__:
            is_duplicate = (mutant.id != self.get_executed_or_first(unique_preds, executed_ids))
            if not no_duplicates or not is_duplicate:
                res.append(mutant)
        return res

    def get_mutant_by_id(self, include):
        if include is None:
            return self.get_mutants_to_exec(self, None)
        elif isinstance(include, (list, tuple, set)):
            include_ids = set(include)
        else:
            include_ids = {include}

        result = [DetailedReplacementMutant(maskedPredicates.lineNumber, maskedPredicates.codeString,
                                            str(maskedPredicates.astStmtType),
                                            maskedPredicates.unique_predictions[m][0], fileP.javaFile.path,
                                            maskedPredicates.start, maskedPredicates.end, m)
                  for fileP in self.fileRequests
                  for maskedPredicates in fileP.allMaskedPredicates
                  for m in maskedPredicates.unique_predictions.keys()
                  if len(include_ids.intersection(set(maskedPredicates.unique_predictions[m]))) > 0]

        return result

    def get_mutants_to_exec(self, output_csv) -> List[FileReplacementMutants]:
        result = []
        if output_csv is None or not isfile(output_csv):
            already_treated_mutant_ids = set()
        else:
            already_treated_mutant_df = pd.read_csv(output_csv)
            already_treated_mutant_ids = set(already_treated_mutant_df['id'].unique())

        for fileP in self.fileRequests:
            mutants = [ReplacementMutant(sorted(maskedPredicates.get_unique_preds()[m])[0], fileP.javaFile.path,
                                         maskedPredicates.start, maskedPredicates.end, m)

                       for maskedPredicates in fileP.allMaskedPredicates
                       for m in maskedPredicates.get_unique_preds().keys()
                       if already_treated_mutant_ids.isdisjoint(set(maskedPredicates.get_unique_preds()[m]))
                       ]
            if len(mutants) > 0:
                result.append(FileReplacementMutants(fileP.javaFile.path, mutants))

        return result

    def count_predictions(self) -> DataFrame:

        tuples = [(fileP.javaFile.path, len(fileP.allMaskedPredicates), len(maskedPredicates.unique_predictions),
                   sum(len(v) for v in maskedPredicates.unique_predictions.values()))

                  for fileP in self.fileRequests
                  for maskedPredicates in fileP.allMaskedPredicates]
        df = pd.DataFrame(tuples, columns=['file','masked_preds','uniq_preds','all_preds'])
        return df


def predict_ap_mc_locs(sc_json_file: str, cbm: CodeBertMlmFillMask = None, start_mutant_id=0, max_size=MAX_TOKENS):
    if cbm is None:
        cbm = CodeBertMlmFillMask()
    file_locs: ApMcListFileLocations = ApMcListFileLocations.parse_file(sc_json_file)
    print('++++++ attempt process json {0} ++++++'.format(sc_json_file))
    file_locs.process_locs(cbm, start_mutant_id, max_size=max_size)
    return file_locs
