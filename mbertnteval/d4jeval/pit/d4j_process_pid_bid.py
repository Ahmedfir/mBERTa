import logging
import os
import sys
from os.path import isfile, join, isdir
from subprocess import SubprocessError, CalledProcessError

from mbertnteval.d4jeval.d4j_project import D4jProject
from mbertnteval.d4jeval.yaml_utils import load_config
from mbertnteval.pit.pit_command import pit_generate_mutants

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)
log.addHandler(logging.StreamHandler(sys.stdout))


def get_args():
    import argparse
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('-fix_commit_changes_csv', dest='fix_commit_changes_csv')
    parser.add_argument('-config', dest='config', help='config yaml file.')
    parser.add_argument('-max_mut_per_class', dest='max_mut_per_class', help='max_mut_per_class.')
    args = parser.parse_args()

    if args.fix_commit_changes_csv is None or not isfile(args.config):
        parser.print_help()
        raise AttributeError
    return args


def print_in_progress_file(progress_file, line):
    with open(progress_file, mode='a') as p_file:
        print(line, file=p_file)


def d4j_pit_generate_mutants(d4j_project: D4jProject, pit_jar_path, output_dir, threads, max_mutants_per_class=0,
                             output_format='XML'):
    try:
        cp = d4j_project.export_prop('cp.compile').replace(':', ',') + ',' + d4j_project.export_prop('cp.test').replace(
            ':', ',')
        source_dir = d4j_project.export_prop('dir.src.classes')
        tests_dir = d4j_project.export_prop('dir.src.tests')
        target_classes = d4j_project.export_prop('classes.modified')
        target_tests = d4j_project.export_prop(
            'tests.relevant') if d4j_project.relevant_tests_exec_only_possible else d4j_project.export_prop('tests.all')
    except SubprocessError as e:
        log.critical("loading config failed for {0}".format(d4j_project.pid_bid), e, exc_info=True)
        raise e
    try:
        from utils.delta_time_printer import DeltaTime
        delta_time = DeltaTime(logging_level=logging.DEBUG)
        res = pit_generate_mutants(d4j_project.jdk, cp,
                                   join(d4j_project.repo_path, source_dir),
                                   join(d4j_project.repo_path, tests_dir),
                                   target_classes.strip().replace('\n', ','),
                                   target_tests.strip().replace('\n', ','),
                                   output_dir, pit_jar_path=pit_jar_path,
                                   threads=threads, max_mut_per_class=max_mutants_per_class,
                                   output_format=output_format)
        delta_time.print('{0} : pit cost for mutants gen.'.format(d4j_project.pid_bid))
        return res
    except CalledProcessError as e:
        log.critical("executing pit failed for {0}".format(d4j_project.pid_bid), e, exc_info=True)
        raise e


def main_func(fix_commit_changes_csv, config, max_mutants_per_class, output_format='XML'):
    pid_bid = fix_commit_changes_csv.split(".")[0]
    pid_bid_splits = pid_bid.split('_')
    config = load_config(config)
    d4j_project = D4jProject(os.path.expanduser(config['defects4j']['containing_dir']),
                             os.path.expanduser(config['tmp_large_memory']['d4jRepos']), pid=pid_bid_splits[0],
                             bid=pid_bid_splits[1],
                             jdk8=os.path.expanduser(config['java']['home8']),
                             jdk7=os.path.expanduser(config['java']['home7']))

    # fix_commit_changes_csv = join(os.path.expanduser(config['defects4j']['fix_commit_changes_dir']),
    #                               fix_commit_changes_csv)
    output_dir = join(os.path.expanduser(config['output_dir']), pid_bid)
    if not isdir(output_dir):
        try:
            os.makedirs(output_dir)
        except FileExistsError:
            log.debug("two threads created the directory concurrently.")
    progress_file = join(output_dir, 'progress_file.log')

    if not d4j_project.checkout_validate_fixed_version():
        print_in_progress_file(progress_file, pid_bid + ',exit,project.checkout_validate_fixed_version')
        raise Exception

    res = d4j_pit_generate_mutants(d4j_project, os.path.expanduser(config['pit_jar']), output_dir,
                                    config['exec']['threads'], max_mutants_per_class=max_mutants_per_class,
                                    output_format=output_format)
    # d4j_project.remove()

    return res


if __name__ == '__main__':
    args = get_args()
    if args.max_mut_per_class is not None:
        # for HOM, no need to generate all possible mutants.
        max_mut_per_class = int(args.max_mut_per_class)
    else:
        max_mut_per_class = 0
    print(str(main_func(args.fix_commit_changes_csv, args.config, max_mut_per_class)))
