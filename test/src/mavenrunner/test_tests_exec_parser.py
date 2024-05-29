from os.path import join
from pathlib import Path
from unittest import TestCase
from utils.file_read_write import load_file

from mavenrunner.tests_exec_parser import exec_res_to_broken_tests_arr, MvnFailingTest, FailCategory


class TestMvnProject(TestCase):

    def setUp(self):
        self.TEST_PATH = Path(__file__).parent.parent.parent
        self.RES_PATH = join(self.TEST_PATH, 'res')
        self.failing_tests_example = load_file(join(self.RES_PATH, 'mavenrunner/failing_tests_mvn_output.txt'))
        self.failing_and_error_tests_example = load_file(join(self.RES_PATH, 'mavenrunner/error_failing_tests_mvn_output.txt'))
        self.passing_tests_example = "\n".join(['[INFO]',
                                                '[INFO] ----------------------< org.example:DummyProject '
                                                '>----------------------',
                                                '[INFO] Building DummyProject 1.0-SNAPSHOT',
                                                '[INFO] --------------------------------[ jar '
                                                ']---------------------------------',
                                                '[INFO]',
                                                '[INFO] --- maven-resources-plugin:2.6:resources (default-resources) @ '
                                                'DummyProject ---',
                                                '[WARNING] Using platform encoding (UTF-8 actually) to copy filtered '
                                                'resources, i.e. build is platform dependent!',
                                                '[INFO] Copying 0 resource',
                                                '[INFO]',
                                                '[INFO] --- maven-compiler-plugin:3.1:compile (default-compile) @ '
                                                'DummyProject ---',
                                                '[INFO] Nothing to compile - all classes are up to date',
                                                '[INFO]',
                                                '[INFO] --- maven-resources-plugin:2.6:testResources (default-testResources) '
                                                '@ DummyProject ---',
                                                '[WARNING] Using platform encoding (UTF-8 actually) to copy filtered '
                                                'resources, i.e. build is platform dependent!',
                                                '[INFO] skip non existing resourceDirectory '
                                                '/Users/ahmed.khanfir/PycharmProjects/mBERTa/test/res/exampleclass/DummyProject/src/test/resources',
                                                '[INFO]',
                                                '[INFO] --- maven-compiler-plugin:3.1:testCompile (default-testCompile) @ '
                                                'DummyProject ---',
                                                '[INFO] Nothing to compile - all classes are up to date',
                                                '[INFO]',
                                                '[INFO] --- maven-surefire-plugin:2.12.4:test (default-test) @ DummyProject '
                                                '---',
                                                '[INFO] Surefire report directory: '
                                                '/Users/ahmed.khanfir/PycharmProjects/mBERTa/test/res/exampleclass/DummyProject/target/surefire-reports',
                                                'Downloading from central: '
                                                'https://repo.maven.apache.org/maven2/org/apache/maven/surefire/surefire-junit47/2.12.4/surefire-junit47-2.12.4.pom',
                                                'Progress (1): 2.7/3.7 kB',
                                                'Progress (1): 3.7 kB',
                                                'Downloaded from central: '
                                                'https://repo.maven.apache.org/maven2/org/apache/maven/surefire/surefire-junit47/2.12.4/surefire-junit47-2.12.4.pom '
                                                '(3.7 kB at 8.7 kB/s)',
                                                'Downloading from central: '
                                                'https://repo.maven.apache.org/maven2/org/apache/maven/surefire/common-junit48/2.12.4/common-junit48-2.12.4.pom',
                                                'Progress (1): 2.5 kB',
                                                'Downloaded from central: '
                                                'https://repo.maven.apache.org/maven2/org/apache/maven/surefire/common-junit48/2.12.4/common-junit48-2.12.4.pom '
                                                '(2.5 kB at 49 kB/s)',
                                                'Downloading from central: '
                                                'https://repo.maven.apache.org/maven2/org/apache/maven/surefire/common-junit4/2.12.4/common-junit4-2.12.4.pom',
                                                'Progress (1): 1.7 kB',
                                                'Downloaded from central: '
                                                'https://repo.maven.apache.org/maven2/org/apache/maven/surefire/common-junit4/2.12.4/common-junit4-2.12.4.pom '
                                                '(1.7 kB at 50 kB/s)',
                                                'Downloading from central: '
                                                'https://repo.maven.apache.org/maven2/org/apache/maven/surefire/common-junit3/2.12.4/common-junit3-2.12.4.pom',
                                                'Progress (1): 1.6 kB',
                                                'Downloaded from central: '
                                                'https://repo.maven.apache.org/maven2/org/apache/maven/surefire/common-junit3/2.12.4/common-junit3-2.12.4.pom '
                                                '(1.6 kB at 54 kB/s)',
                                                'Downloading from central: '
                                                'https://repo.maven.apache.org/maven2/org/apache/maven/surefire/surefire-grouper/2.12.4/surefire-grouper-2.12.4.pom',
                                                'Progress (1): 2.5 kB',
                                                'Downloaded from central: '
                                                'https://repo.maven.apache.org/maven2/org/apache/maven/surefire/surefire-grouper/2.12.4/surefire-grouper-2.12.4.pom '
                                                '(2.5 kB at 52 kB/s)',
                                                'Downloading from central: '
                                                'https://repo.maven.apache.org/maven2/org/apache/maven/surefire/common-junit3/2.12.4/common-junit3-2.12.4.jar',
                                                'Downloading from central: '
                                                'https://repo.maven.apache.org/maven2/org/apache/maven/surefire/surefire-junit47/2.12.4/surefire-junit47-2.12.4.jar',
                                                'Downloading from central: '
                                                'https://repo.maven.apache.org/maven2/org/apache/maven/surefire/surefire-grouper/2.12.4/surefire-grouper-2.12.4.jar',
                                                'Downloading from central: '
                                                'https://repo.maven.apache.org/maven2/org/apache/maven/surefire/common-junit48/2.12.4/common-junit48-2.12.4.jar',
                                                'Downloading from central: '
                                                'https://repo.maven.apache.org/maven2/org/apache/maven/surefire/common-junit4/2.12.4/common-junit4-2.12.4.jar',
                                                'Progress (1): 2.7/11 kB',
                                                'Progress (1): 5.5/11 kB',
                                                'Progress (1): 8.2/11 kB',
                                                'Progress (1): 11/11 kB',
                                                'Progress (1): 11 kB',
                                                'Downloaded from central: '
                                                'https://repo.maven.apache.org/maven2/org/apache/maven/surefire/common-junit3/2.12.4/common-junit3-2.12.4.jar '
                                                '(11 kB at 281 kB/s)',
                                                'Progress (1): 2.7/47 kB',
                                                'Progress (1): 5.5/47 kB',
                                                'Progress (1): 8.2/47 kB',
                                                'Progress (1): 11/47 kB',
                                                'Progress (1): 14/47 kB',
                                                'Progress (1): 16/47 kB',
                                                'Progress (1): 19/47 kB',
                                                'Progress (1): 22/47 kB',
                                                'Progress (1): 25/47 kB',
                                                'Progress (1): 27/47 kB',
                                                'Progress (1): 30/47 kB',
                                                'Progress (1): 33/47 kB',
                                                'Progress (1): 36/47 kB',
                                                'Progress (1): 38/47 kB',
                                                'Progress (1): 41/47 kB',
                                                'Progress (2): 41/47 kB | 2.7/38 kB',
                                                'Progress (3): 41/47 kB | 2.7/38 kB | 2.7/15 kB',
                                                'Progress (4): 41/47 kB | 2.7/38 kB | 2.7/15 kB | 2.7/28 kB',
                                                'Progress (4): 44/47 kB | 2.7/38 kB | 2.7/15 kB | 2.7/28 kB',
                                                'Progress (4): 44/47 kB | 5.5/38 kB | 2.7/15 kB | 2.7/28 kB',
                                                'Progress (4): 44/47 kB | 5.5/38 kB | 5.5/15 kB | 2.7/28 kB',
                                                'Progress (4): 44/47 kB | 8.2/38 kB | 5.5/15 kB | 2.7/28 kB',
                                                'Progress (4): 44/47 kB | 8.2/38 kB | 5.5/15 kB | 5.5/28 kB',
                                                'Progress (4): 46/47 kB | 8.2/38 kB | 5.5/15 kB | 5.5/28 kB',
                                                'Progress (4): 46/47 kB | 8.2/38 kB | 5.5/15 kB | 8.2/28 kB',
                                                'Progress (4): 46/47 kB | 11/38 kB | 5.5/15 kB | 8.2/28 kB',
                                                'Progress (4): 46/47 kB | 11/38 kB | 5.5/15 kB | 11/28 kB',
                                                'Progress (4): 46/47 kB | 11/38 kB | 8.2/15 kB | 11/28 kB',
                                                'Progress (4): 46/47 kB | 11/38 kB | 8.2/15 kB | 14/28 kB',
                                                'Progress (4): 46/47 kB | 14/38 kB | 8.2/15 kB | 14/28 kB',
                                                'Progress (4): 47 kB | 14/38 kB | 8.2/15 kB | 14/28 kB',
                                                'Progress (4): 47 kB | 16/38 kB | 8.2/15 kB | 14/28 kB',
                                                'Progress (4): 47 kB | 16/38 kB | 8.2/15 kB | 16/28 kB',
                                                'Progress (4): 47 kB | 16/38 kB | 11/15 kB | 16/28 kB',
                                                'Progress (4): 47 kB | 16/38 kB | 11/15 kB | 19/28 kB',
                                                'Progress (4): 47 kB | 16/38 kB | 14/15 kB | 19/28 kB',
                                                'Progress (4): 47 kB | 19/38 kB | 14/15 kB | 19/28 kB',
                                                'Progress (4): 47 kB | 19/38 kB | 14/15 kB | 22/28 kB',
                                                'Progress (4): 47 kB | 22/38 kB | 14/15 kB | 22/28 kB',
                                                'Progress (4): 47 kB | 22/38 kB | 15 kB | 22/28 kB',
                                                'Progress (4): 47 kB | 22/38 kB | 15 kB | 25/28 kB',
                                                'Progress (4): 47 kB | 25/38 kB | 15 kB | 25/28 kB',
                                                'Progress (4): 47 kB | 25/38 kB | 15 kB | 27/28 kB',
                                                'Progress (4): 47 kB | 27/38 kB | 15 kB | 27/28 kB',
                                                'Progress (4): 47 kB | 27/38 kB | 15 kB | 28 kB',
                                                'Progress (4): 47 kB | 30/38 kB | 15 kB | 28 kB',
                                                'Progress (4): 47 kB | 33/38 kB | 15 kB | 28 kB',
                                                'Progress (4): 47 kB | 36/38 kB | 15 kB | 28 kB',
                                                'Progress (4): 47 kB | 38 kB | 15 kB | 28 kB',
                                                'Downloaded from central: '
                                                'https://repo.maven.apache.org/maven2/org/apache/maven/surefire/surefire-junit47/2.12.4/surefire-junit47-2.12.4.jar '
                                                '(47 kB at 515 kB/s)',
                                                'Downloaded from central: '
                                                'https://repo.maven.apache.org/maven2/org/apache/maven/surefire/common-junit48/2.12.4/common-junit48-2.12.4.jar '
                                                '(28 kB at 291 kB/s)',
                                                'Downloaded from central: '
                                                'https://repo.maven.apache.org/maven2/org/apache/maven/surefire/surefire-grouper/2.12.4/surefire-grouper-2.12.4.jar '
                                                '(38 kB at 367 kB/s)',
                                                'Downloaded from central: '
                                                'https://repo.maven.apache.org/maven2/org/apache/maven/surefire/common-junit4/2.12.4/common-junit4-2.12.4.jar '
                                                '(15 kB at 150 kB/s)',
                                                '-------------------------------------------------------',
                                                'T E S T S',
                                                '-------------------------------------------------------',
                                                "Concurrency config is parallel='classes', perCoreThreadCount=true, "
                                                'threadCount=2, useUnlimitedThreads=false',
                                                'Running example.DummyClassTest',
                                                'Tests run: 4, Failures: 0, Errors: 0, Skipped: 0, Time elapsed: 0.003 sec',
                                                'Results :',
                                                'Tests run: 4, Failures: 0, Errors: 0, Skipped: 0',
                                                '[INFO] '
                                                '------------------------------------------------------------------------',
                                                '[INFO] BUILD SUCCESS',
                                                '[INFO] '
                                                '------------------------------------------------------------------------',
                                                '[INFO] Total time:  2.558 s',
                                                '[INFO] Finished at: 2024-05-28T14:25:20+02:00',
                                                '[INFO] '
                                                '------------------------------------------------------------------------'])

    def test_exec_res_to_broken_tests_arr_pass(self):
        self.assertEqual(set(), exec_res_to_broken_tests_arr(self.passing_tests_example))

    def test_exec_res_to_broken_tests_arr_fail(self):
        self.assertEqual({MvnFailingTest(method_name='parseStringToInt_int', class_name='example.DummyClassTest',
                                         reason='expected:<4> but was:<1>', failing_category=FailCategory.Fail),
                          MvnFailingTest(method_name='addCalc', class_name='example.DummyClassTest',
                                         reason='expected:<6> but was:<5>', failing_category=FailCategory.Fail)},
                         exec_res_to_broken_tests_arr(self.failing_tests_example))

    def test_exec_res_to_broken_tests_arr_fail_and_error(self):
        self.assertEqual({MvnFailingTest(method_name='parseStringToInt_int', class_name='example.DummyClassTest',
                                         reason='expected:<4> but was:<1>', failing_category=FailCategory.Fail),
                          MvnFailingTest(method_name='addCalc', class_name='example.DummyClassTest',
                                         reason='expected:<6> but was:<5>', failing_category=FailCategory.Fail),
                          MvnFailingTest(method_name='parseStringToInt_str', class_name='example.DummyClassTest',
                                         reason=None, failing_category=FailCategory.Err)
                          },
                         exec_res_to_broken_tests_arr(self.failing_and_error_tests_example))
