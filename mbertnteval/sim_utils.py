import math
from typing import List


def calc_ochiai(mutant_failing_tests: List[str], bug_failing_tests: List[str]):
    prod = len(set(mutant_failing_tests)) * len(set(bug_failing_tests))
    if prod <= 0:
        return 0.0
    inter = len(set(mutant_failing_tests).intersection(set(bug_failing_tests)))
    return float(inter) / math.sqrt(prod)


def calc_fdb(mutant_failing_tests: List[str], bug_failing_tests: List[str]):
    assert len(bug_failing_tests) > 0
    l_m_failing_tests = len(set(mutant_failing_tests))
    if l_m_failing_tests <= 0:
        return 0.0
    inter = len(set(mutant_failing_tests).intersection(set(bug_failing_tests)))
    if inter <= 0:
        return 0.0
    return float(inter) / float(l_m_failing_tests)