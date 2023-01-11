import logging
import sys
from os.path import join
from pathlib import Path

from utils.cmd_utils import shell_call, DAY_S

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
log.addHandler(logging.StreamHandler(sys.stdout))

PIT_JAR = join(Path(__file__).parent, 'pitest-command-line-1.0.0-SNAPSHOT-jar-with-dependencies.jar')
PIT_RV_JAR = join(Path(__file__).parent, 'pitest-command-line-1.7.4-SNAPSHOT-jar-with-dependencies.jar')


def pit_generate_mutants(jdk_path, class_patch, source_dir, tests_dir, target_classes, target_tests,
                         output_dir, pit_jar_path=PIT_JAR, threads=0, mutators='ALL', max_mut_per_class=5):
    '''
    example from the docs:
    java -cp <your classpath including pit jar and dependencies> \
    org.pitest.mutationtest.commandline.MutationCoverageReport \
    --reportDir <outputdir> \
    --targetClasses example.foo.Specfic, example.foo.Other \
    --targetTests example.ReflectionSuite
    --sourceDirs c:\\myProject\\src
    --threads
    --mutators
    --maxMutationsPerClass
    --outputFormats HTML,CSV
    --timestampedReports=false
    '''

    # cp = pit_jar_path + ':' + class_patch
    cmd = "JAVA_HOME='" + jdk_path + "' " + join(jdk_path, 'bin',
                                                 'java') + " -jar " + pit_jar_path \
          + " --classPath '" + class_patch + "'" \
          + " --reportDir '" + output_dir + "'" \
          + " --targetClasses '" + target_classes + "'" \
          + " --targetTests '" + target_tests + "'" \
          + " --sourceDirs '" + source_dir + ',' + tests_dir + "'" \
          + (" --threads " + str(threads) if threads > 0 else "") \
          + " --mutators " + mutators \
          + " --maxMutationsPerClass " + str(max_mut_per_class) \
          + " --outputFormats XML" \
          + " --timestampedReports=false" \
          + " --fullMutationMatrix=true"

    log.debug('exec cmd >> ' + cmd)

    return shell_call(cmd, timeout=2 * DAY_S)
