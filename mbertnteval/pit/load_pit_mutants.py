import os
from enum import Enum
from os import makedirs
from os.path import join, isfile, dirname, abspath, isdir, getsize
from typing import List, Dict, Set
from xml.etree import ElementTree as ET

from commons import pickle_utils

PIT_XML_FILE_NAME = 'mutations.xml'


class PitVersions(Enum):
    v_1_9 = "pit"
    v_1_7 = "pit_rv"


# default patterns
PIT_DEFAULT_MUTATORS: Dict[PitVersions, Set[str]] = {
    PitVersions.v_1_9: {
        'InvertNegsMutator',
        'MathMutator',
        'VoidMethodCallMutator',
        'NegateConditionalsMutator',
        'ConditionalsBoundaryMutator',
        'IncrementsMutator',
        'BooleanTrueReturnValsMutator',
        'BooleanFalseReturnValsMutator',
        'EmptyObjectReturnValsMutator',
        'NullReturnValsMutator'},
    PitVersions.v_1_7: {
        'ConditionalsBoundaryMutator',
        'IncrementsMutator',
        'InvertNegsMutator',
        'MathMutator',
        'NegateConditionalsMutator',
        'VoidMethodCallMutator',
        'EmptyObjectReturnValsMutator',
        'BooleanFalseReturnValsMutator',
        'BooleanTrueReturnValsMutator',
        'NullReturnValsMutator',
        'PrimitiveReturnsMutator'}
}


class DetectionStatus(Enum):
    """ @see org.pitest.mutationtest.DetectionStatus """
    s = 'SURVIVED'
    nc = 'NO_COVERAGE'
    k = 'KILLED'
    to = 'TIMED_OUT'
    nv = 'NON_VIABLE'
    me = 'MEMORY_ERROR'
    re = 'RUN_ERROR'


class PitMutant:

    def __init__(self, detected: bool, status: DetectionStatus, sourceFile: str, mutatedClass: str, mutatedMethod: str,
                 lineNumber: int, mutator: str, killingTests: List[str]):
        self.detected = detected
        self.status = status
        self.sourceFile = sourceFile
        self.mutatedClass = mutatedClass
        self.mutatedMethod = mutatedMethod
        self.lineNumber = lineNumber
        self.mutator = mutator
        self.killingTests = killingTests


def parse_xml_file(containing_dir, xml_file_name=PIT_XML_FILE_NAME, output_file='mutants.pickle', force_reload=False) -> \
        List[PitMutant]:
    def split_tests(tests_str):
        if tests_str is None or len(tests_str.strip()) == 0:
            return []
        else:
            tests = tests_str.split('|')
            return [t.split('(')[0] for t in tests]

    if force_reload or not isfile(output_file):
        output_dir = abspath(dirname(output_file))
        if not isdir(output_dir):
            try:
                makedirs(output_dir)
            except FileExistsError:
                print("two threads created the directory concurrently.")
        xml_file = join(containing_dir, xml_file_name)
        assert isfile(xml_file) and getsize(xml_file) > 0
        tree = ET.parse(xml_file)

        res = [PitMutant(mutant_xml.attrib['detected'] == 'true',
                         DetectionStatus(mutant_xml.attrib['status']),
                         mutant_xml.find('sourceFile').text,
                         mutant_xml.find('mutatedClass').text,
                         mutant_xml.find('mutatedMethod').text,
                         int(mutant_xml.find('lineNumber').text),
                         mutant_xml.find('mutator').text,
                         split_tests(mutant_xml.find('killingTests').text))
               for mutant_xml in tree.getroot().findall('mutation')]

        pickle_utils.save_zipped_pickle(res, output_file)
    else:
        try:
            res = pickle_utils.load_zipped_pickle(output_file)
        except BaseException:
            print('issue in loading pickle {0}'.format(output_file))
            os.remove(output_file)
            return parse_xml_file(containing_dir, xml_file_name=xml_file_name, output_file=output_file,
                                  force_reload=force_reload)
    return res


def parse_default_mutants_from_all_mutants_xml_file(containing_dir, pit_default_mutators,
                                                    xml_file_name=PIT_XML_FILE_NAME,
                                                    all_output_file='mutants.pickle',
                                                    output_file='def_mutants.pickle',
                                                    force_reload=False) -> List[PitMutant]:
    if force_reload or not isfile(output_file):
        output_dir = abspath(dirname(output_file))
        if not isdir(output_dir):
            try:
                makedirs(output_dir)
            except FileExistsError:
                print("two threads created the directory concurrently.")
        all_mutants = parse_xml_file(containing_dir, xml_file_name=xml_file_name, output_file=all_output_file,
                                     force_reload=force_reload)
        default_mutants = [m for m in all_mutants if m.mutator.split('.')[-1] in pit_default_mutators]
        pickle_utils.save_zipped_pickle(default_mutants, output_file)
    else:
        default_mutants = pickle_utils.load_zipped_pickle(output_file)
    return default_mutants


class PitMutators(Enum):
    ALL = "ALL"
    DEF = "DEF"


class PitResults:
    def __init__(self, xml_dir, pickle_dir, pid_bid, version: PitVersions = PitVersions.v_1_9,
                 mutators: PitMutators = PitMutators.ALL):
        self.project_name = pid_bid
        self.version = version
        self.xml_dir = xml_dir
        self.pickle_dir = pickle_dir
        self.mutators = mutators

    def get_results_dir(self):
        xml_dir = join(self.xml_dir, self.project_name)
        pit_mutations_xml_file = join(xml_dir, PIT_XML_FILE_NAME)
        if isfile(pit_mutations_xml_file) and getsize(pit_mutations_xml_file) > 0:
            return xml_dir
        else:
            return None

    def get_mutants(self):
        xml_dir = self.get_results_dir()
        if xml_dir is not None:
            if self.mutators == PitMutators.ALL:
                return parse_xml_file(xml_dir, output_file=join(self.pickle_dir, self.project_name + '_pit.pickle'))
            elif self.mutators == PitMutators.DEF:
                all_output_file = join(self.pickle_dir, self.project_name + '_pit.pickle')
                default_output_file = join(self.pickle_dir, self.project_name + '_pit_def.pickle')

                return parse_default_mutants_from_all_mutants_xml_file(xml_dir, PIT_DEFAULT_MUTATORS[self.version],
                                                                       all_output_file=all_output_file,
                                                                       output_file=default_output_file)
        else:
            return None

    def get_mutants_df(self):
        mutants = self.get_mutants()
        if mutants is not None and len(mutants) > 0:
            import pandas as pd
            mutants_df = pd.DataFrame([vars(m) for m in mutants])
            mutants_df['proj_bug_id'] = self.project_name
            return mutants_df
        else:
            return None
