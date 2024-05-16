import re
from os import makedirs
from os.path import isfile, join, isdir
from pathlib import Path
from typing import List

import pandas as pd
from pandas import DataFrame

from commons.pickle_utils import load_zipped_pickle, save_zipped_pickle

DETAILS_FILE_NAME = 'details.txt'


class PitMutantDetailsTxt:
    path = ''
    dir_id = -1
    mutatedClass = ''
    mutatedMethod = ''
    # self.methodDescription = self._parse_element_by_tag(content, 'methodDesc')
    lineNumber = -1
    block = []
    indexes = []
    description = []

    def set_file(self, file):
        path = Path(file)
        assert isfile(file)
        assert path.name == DETAILS_FILE_NAME
        self.path = file
        self.dir_id = int(str(path.parent.name))
        return self

    @staticmethod
    def _parse_element_by_tag(content, tag, unique=True):
        res = re.findall(tag + '=(.*?),', content)
        if unique:
            assert len(res) == 1
            return res[0]
        else:
            return res

    def parse_details(self, content):
        self.mutatedClass = self._parse_element_by_tag(content, 'clazz')
        self.mutatedMethod = self._parse_element_by_tag(content, 'method')
        self.lineNumber = int(self._parse_element_by_tag(content, 'lineNumber'))
        self.block = eval(self._parse_element_by_tag(content, 'block'))
        self.indexes = eval(self._parse_element_by_tag(content, 'indexes'))
        self.description = self._parse_element_by_tag(content, 'description')
        # self.methodDescription = self._parse_element_by_tag(content, 'methodDesc')
        return self

    def parse_details_file(self):
        with open(self.path, "r") as f:
            f_content = f.read()
            self.parse_details(f_content)
            return self


def cols_to_str(dfs: List[DataFrame], cols: List[str]):
    ''' specific to pandas: to be able to make a join/merge on a column it has to be hashable for pandas. '''
    from pandas.api.types import is_hashable
    for df in dfs:
        for c in cols:
            if not is_hashable(df[c]):
                df[c] = df[c].astype(str)


def join_mutated_classes_with_results(results_df: DataFrame, mutated_classes_df: DataFrame):
    merging_cols = ['proj_bug_id', 'mutatedClass', 'mutatedMethod', 'lineNumber', 'block', 'indexes', 'description']
    cols_to_str([results_df, mutated_classes_df], merging_cols)
    merged_df = pd.merge(results_df, mutated_classes_df, how="left",
                         left_on=merging_cols,
                         right_on=merging_cols)
    assert merged_df.groupby(['path', 'dir_id']).ngroups == merged_df['path'].nunique() == len(merged_df) == len(
        results_df)
    assert set(merged_df['id'].unique()) == set(results_df['id'].unique())
    return merged_df


class PitExportedMutants:

    def __init__(self, parent_dir, project_name, pickles_dir):
        self.project_name = project_name
        self.path = join(parent_dir, project_name)
        self.pickle_file = join(pickles_dir, project_name + '_exportdetails.pickle')

    def get_mutants(self):
        if not isdir(self.path):
            print('not a dir: ' + self.path)
            return None
        return [PitMutantDetailsTxt().set_file(f).parse_details_file() for f in
                Path(self.path).rglob('*/mutants/*/' + DETAILS_FILE_NAME)]

    def get_mutants_df(self):
        if isfile(self.pickle_file):
            return load_zipped_pickle(self.pickle_file)
        else:
            mutants = self.get_mutants()
            if mutants is not None and len(mutants) > 0:
                import pandas as pd
                mutants_df = pd.DataFrame([vars(m) for m in mutants])
                mutants_df['proj_bug_id'] = self.project_name
                if not isdir(Path(self.pickle_file).parent):
                    makedirs(Path(self.pickle_file).parent)
                save_zipped_pickle(mutants_df, self.pickle_file)
                return mutants_df
            else:
                print('no mutants: ' + self.project_name)
                return None

    def append_export_details(self, results_df: DataFrame) -> DataFrame:
        details_df = self.get_mutants_df()
        if details_df is not None:
            return join_mutated_classes_with_results(results_df, details_df)
        else:
            return None
