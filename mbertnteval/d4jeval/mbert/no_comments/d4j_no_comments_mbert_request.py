import logging
import sys
from os.path import join
from pathlib import Path

from mbertnteval.d4jeval.d4j_project import D4jProject
from mbertnteval.d4jeval.mbert.d4j_mbert_request import D4jRequest

log = logging.getLogger(__name__)
log.addHandler(logging.StreamHandler(sys.stdout))

COMMENTS_REMOVER_JAR = join(Path(__file__).parent, 'comment-remover-1.2-SNAPSHOT-jar-with-dependencies.jar')


class NoCommentD4jRequest(D4jRequest):

    def __init__(self, project: D4jProject, *args, **kargs):
        super(NoCommentD4jRequest, self).__init__(project, *args, **kargs)

    def remove_comments_from_repo(self, c_r_jar: str = COMMENTS_REMOVER_JAR, check_compile=True,
                                  vm_options="-Xms1024m -Xmx1024m -Xss512m"):
        log.info("removing comments.")

        cmd = "JAVA_HOME='" + self.project.jdk + "' " + join(self.project.jdk, 'bin',
                                                                                'java') + " " + vm_options + " "  + " -jar " + c_r_jar + " " + self.repo_path
        print("call jar cmd ... {0}".format(cmd))
        from utils.cmd_utils import shellCallTemplate
        output = shellCallTemplate(cmd)
        log.info(output)
        if check_compile:
            return self.project.compile()
        else:
            log.warning("skipping compilation check after removing")
            return True

    def preprocess(self) -> bool:
        # checkout fixed version of the project and check that it's valid.
        if self.project.checkout_validate_fixed_version():
            # remove comments
            return self.remove_comments_from_repo()
