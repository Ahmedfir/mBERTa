import json
import logging
import sys
from typing import List, Any, Set, Dict
from enum import Enum

from pydantic import BaseModel
from ttp import ttp

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)
log.addHandler(logging.StreamHandler(sys.stdout))


class FailCategory(Enum):
    Err = 0
    Fail = 1
    Ukn = 2


class TestReportCategory(Enum):
    Surefire = 0
    JUnit = 1


class MvnFailingTest(BaseModel):
    method_name: str = None
    class_name: str = None
    reason: str = None
    failing_category: FailCategory = None

    def is_invalid(self):
        return self.class_name is None or self.method_name is None

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, MvnFailingTest):
            # don't attempt to compare against unrelated types
            return NotImplemented
        return self.method_name == other.method_name and self.class_name == other.class_name and self.reason == other.reason

    def __hash__(self):
        # necessary for instances to behave sanely in dicts and sets.
        return hash((self.method_name, self.class_name, self.reason))

    @staticmethod
    def get_template() -> dict[TestReportCategory, dict[FailCategory, list[str]]]:
        return {
            TestReportCategory.Surefire: {
                FailCategory.Ukn: [
                    """-[ERROR] Tests run: {{ ignore }}, Failures: {{ fa_class }}, Errors: {{ err_class }}, Skipped: {{ sk_class }}, Time elapsed: {{ ignore }} s *** FAILURE! - in {{class_name}}"""],
                FailCategory.Fail: ["""-[ERROR] {{ method_name }}  Time elapsed: {{ ignore }} s *** FAILURE!"""],
                FailCategory.Err: ["""-[ERROR] {{ method_name }} Time elapsed: {{ ignore }} s *** ERROR!"""],

            },
            TestReportCategory.JUnit: {
                FailCategory.Fail: ["""-Failed tests: {{ method_name }}({{ class_name }}): {{ reason | ORPHRASE }}""",
                                    """-Failed tests: {{ method_name }}({{ class_name }})""", ],
                FailCategory.Err: [
                    """-Tests in error: \n-  {{ method_name }}({{ class_name }}): {{ reason | ORPHRASE }}""",
                    """-Tests in error: \n-  {{ method_name }}({{ class_name }})"""],
                FailCategory.Ukn: ["""- {{ method_name }}({{ class_name }}): {{ reason | ORPHRASE }}""",
                                   """- {{ method_name }}({{ class_name }})"""]
            },
        }


class MvnFailingTestsArray(BaseModel):
    __root__: List[MvnFailingTest] = None

    def remove_invalid(self):
        self.__root__ = [t for t in self.__root__ if not t.is_invalid()]


class MvnTestExecSummary(BaseModel):
    run: int = None
    fa: int = None
    err: int = None
    sk: int = None

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, MvnTestExecSummary):
            # don't attempt to compare against unrelated types
            return NotImplemented
        return self.run == other.run and self.fa == other.fa and self.err == other.err and self.sk == other.sk

    def __hash__(self):
        # necessary for instances to behave sanely in dicts and sets.
        return hash((self.run, self.fa, self.err, self.sk))

    @staticmethod
    def get_template():
        return ["""Tests run: {{ run }}, Failures: {{ fa }}, Errors: {{ err }}, Skipped: {{ sk }}""",
                """[INFO] Tests run: {{ run }}, Failures: {{ fa }}, Errors: {{ err }}, Skipped: {{ sk }}""",
                """[ERROR] Tests run: {{ run }}, Failures: {{ fa }}, Errors: {{ err }}, Skipped: {{ sk }}""",
                """[WARNING] Tests run: {{ run }}, Failures: {{ fa }}, Errors: {{ err }}, Skipped: {{ sk }}"""]


class MvnSummaryArray(BaseModel):
    __root__: List[MvnTestExecSummary] = None

    def get_summary(self):
        result: MvnTestExecSummary = self.__root__[0]
        if len(self.__root__) != 1:
            log.warning("Unexpected results! {0} summaries for test exec!".format(str(len(self.__root__))))
            unique_res = set(self.__root__)
            if len(unique_res) != 1:
                raise Exception(
                    "Unexpected results! {0} different summaries for test exec!".format(str(len(unique_res))))
            else:
                result = list(unique_res)[0]
        return result


def parse_to_json(data_to_parse, template) -> str:
    parser = ttp(data=data_to_parse, template=template)
    parser.parse()
    res = parser.result(format='json')[0]
    return res


def parse_junit_test_report(results_str, category):
    parsed = MvnFailingTestsArray.parse_raw(results_str)
    parsed.remove_invalid()
    if len(parsed.__root__) == 0:
        # quick fix for when we get an array of array for no reason.
        results_json = json.loads(results_str)
        parsed_arr = []
        for rj in results_json:
            if len(rj) > 0:
                pa = MvnFailingTestsArray.parse_raw(json.dumps(rj))
                pa.remove_invalid()
                if len(pa.__root__) > 0:
                    parsed_arr.append(pa)
        if len(parsed_arr) > 0:
            parsed.__root__ = [pa_i for pa in parsed_arr for pa_i in pa.__root__]
    for p in parsed.__root__:
        p.failing_category = category
    return parsed.__root__


def parse_surefire_test_classes(results_str):
    classes = []
    #get list of classes
    results_json = json.loads(results_str)
    for rj in results_json:
        if isinstance(rj, dict):
            classes.append({'class_name': rj['class_name'], 'total_fa': rj['fa_class'], 'total_sk': rj['sk_class'],
                            'total_err': rj['err_class']})
        elif isinstance(rj, list):
            for c in rj:
                    classes.append({'class_name': c['class_name'], 'total_fa': c['fa_class'], 'total_sk': c['sk_class'], 'total_err' : c['err_class']})

    return classes

def parse_surefire_test_failures(results_str, category, classes) :
    # line contains method name
    methods = []
    results_json = json.loads(results_str)
    for rj in results_json:
        if len(rj) > 0:
            if isinstance(rj, dict):
                methods.append({'method_name': rj['method_name']})
            elif isinstance(rj, list):
                for m in rj:
                    methods.append({'method_name': m['method_name']})

    method_cpt = 0
    for c in classes:
        fa_cpt = 0
        while fa_cpt < int(c['total_fa']):
            method = methods[method_cpt]
            method['class_name'] = c['class_name']
            fa_cpt += 1
            method_cpt += 1

    results_str = json.dumps(methods, indent=2)
    return parse_junit_test_report(results_str, category)

def parse_surefire_test_errors(results_str, category, classes):
    # line contains method name
    methods = []
    results_json = json.loads(results_str)
    for rj in results_json:
        if len(rj) > 0:
            if isinstance(rj, dict):
                methods.append({'method_name': rj['method_name']})
            elif isinstance(rj, list) :
                for m in rj:
                    methods.append({'method_name': m['method_name']})

    method_cpt = 0
    for c in classes:
        err_cpt = 0
        while err_cpt < int(c['total_err']):
            method = methods[method_cpt]
            method['class_name'] = c['class_name']
            err_cpt += 1
            method_cpt += 1

    results_str = json.dumps(methods, indent=2)
    return parse_junit_test_report(results_str, category)


def parse_broken_tests(data_to_parse) -> Set[MvnFailingTest]:
    unique_broken_tests = set()
    # adding a minus to the start of every line to simplify the templates and enable the parsing with ttp lib.
    data_to_parse_with_suff = data_to_parse.replace('\n', '\n' + '-')
    data_to_parse_without_less = data_to_parse_with_suff.replace('<<<', '***')
    template_dict = MvnFailingTest.get_template()
    for group in template_dict:
        for category in template_dict[group]:
            for template in template_dict[group][category]:
                results_str = parse_to_json(data_to_parse_without_less, template)
                if group == TestReportCategory.Surefire and ('method_name' in results_str or 'class_name' in results_str):
                    if category == FailCategory.Ukn:
                        classes = parse_surefire_test_classes(results_str)
                    else:
                        if category == FailCategory.Fail:
                            unique_broken_tests.update(parse_surefire_test_failures(results_str, category, classes))
                        elif category == FailCategory.Err:
                            unique_broken_tests.update(parse_surefire_test_errors(results_str, category, classes))
                else:
                    unique_broken_tests.update(parse_junit_test_report(results_str, category))

        if len(unique_broken_tests) > 0:
            return unique_broken_tests


def exec_res_to_broken_tests_arr(data_to_parse) -> Set[MvnFailingTest]:
    templates = MvnTestExecSummary.get_template()
    for template in templates:
        results_str = parse_to_json(data_to_parse, template)
        exec_summary: MvnTestExecSummary = MvnSummaryArray.parse_raw(results_str).get_summary()
        if exec_summary.fa is not None and exec_summary.err is not None and exec_summary.sk is not None:
            break
    if exec_summary.run == 0:
        raise Exception("0 tests run!")
    if exec_summary.fa > 0 or exec_summary.err > 0:
        unique_broken_tests = parse_broken_tests(data_to_parse)
        if len(unique_broken_tests) != exec_summary.err + exec_summary.fa:
            log.critical(
                "Wrong tests parsing! "
                "Received different number of tests when parsing the results than parsing the failing tests!"
                " \n --- parsed:")
            for t in unique_broken_tests:
                log.critical(t.json())
            log.critical(' --- instead of:\n{0}'.format(exec_summary.json()))
            log.critical('--- data to parse \n ' + data_to_parse)
            raise Exception("Wrong tests parsing! Received different number of Errors and Failures!")

        # just trying to add types for the unkown ones by checking whether we have all error and failing ones.
        tests_with_unkown_failing = {t for t in unique_broken_tests if t.failing_category == FailCategory.Ukn}
        if len(tests_with_unkown_failing) > 0:
            # if all expected Fail tests have been categorised Fail, the rest is Err.
            if exec_summary.fa == 0 or exec_summary.fa == len(
                    {t for t in unique_broken_tests if t.failing_category == FailCategory.Fail}):
                for t in tests_with_unkown_failing:
                    t.failing_category = FailCategory.Err
            # if all expected Err tests have been categorised Err, the rest is Fail.
            elif exec_summary.err == 0 or exec_summary.err == len(
                    {t for t in unique_broken_tests if t.failing_category == FailCategory.Err}):
                for t in tests_with_unkown_failing:
                    t.failing_category = FailCategory.Fail

        return unique_broken_tests
    return set()
