import logging
import sys
from typing import List, Any, Set

from pydantic import BaseModel
from ttp import ttp

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)
log.addHandler(logging.StreamHandler(sys.stdout))


class MvnFailingTest(BaseModel):
    method_name: str = None
    class_name: str = None
    reason: str = None

    def is_invalid(self):
        return self.class_name is None or self.method_name is None

    def is_error(self):
        return self.reason is None

    def is_failure(self):
        return self.reason is not None

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, MvnFailingTest):
            # don't attempt to compare against unrelated types
            return NotImplemented
        return self.method_name == other.method_name and self.class_name == other.class_name and self.reason == other.reason

    def __hash__(self):
        # necessary for instances to behave sanely in dicts and sets.
        return hash((self.method_name, self.class_name, self.reason))

    @staticmethod
    def get_template() -> List:
        return ["""-Failed tests: {{ method_name }}({{ class_name }}): {{ reason | ORPHRASE }}""",
                """-Tests in error: \n-  {{ method_name }}({{ class_name }})""",
                """- {{ method_name }}({{ class_name }}): {{ reason | ORPHRASE }}""",
                ]


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
        return """Tests run: {{ run }}, Failures: {{ fa }}, Errors: {{ err }}, Skipped: {{ sk }}"""


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
    return parser.result(format='json')[0]


def parse_broken_tests(data_to_parse) -> Set[MvnFailingTest]:
    unique_broken_tests = set()
    for template in MvnFailingTest.get_template():
        results_str = parse_to_json(data_to_parse.replace('\n', '\n' + '-'), template)
        parsed = MvnFailingTestsArray.parse_raw(results_str)
        parsed.remove_invalid()
        unique_broken_tests.update(parsed.__root__)
    return unique_broken_tests


def exec_res_to_broken_tests_arr(data_to_parse) -> Set[MvnFailingTest]:
    results_str = parse_to_json(data_to_parse, MvnTestExecSummary.get_template())
    exec_summary: MvnTestExecSummary = MvnSummaryArray.parse_raw(results_str).get_summary()
    if exec_summary.run == 0:
        raise Exception("0 tests run!")
    if exec_summary.fa > 0 or exec_summary.err > 0:
        unique_broken_tests = parse_broken_tests(data_to_parse)

        if len({t for t in unique_broken_tests if t.is_error()}) != exec_summary.err\
                or len({t for t in unique_broken_tests if t.is_failure()}) != exec_summary.fa:
            log.critical(
                "Wrong tests parsing! "
                "Received different number of tests when parsing the results than parsing the failing tests!"
                " \n --- parsed:")
            for t in unique_broken_tests:
                log.critical(t.json())
            log.critical(' --- instead of:\n{0}'.format(exec_summary.json()))
            raise Exception("Wrong tests parsing! Received different number of Errors and Failures!")
        return unique_broken_tests
    return set()
