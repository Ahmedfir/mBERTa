import logging
import sys
from os.path import join, isdir
from pathlib import Path

COMMENTS_REMOVER_JAR = join(Path(__file__).parent, 'comment-remover-1.2-SNAPSHOT-jar-with-dependencies.jar')

log = logging.getLogger(__name__)
log.addHandler(logging.StreamHandler(sys.stdout))


def remove_comments_from_repo(repo_path, c_r_jar: str = COMMENTS_REMOVER_JAR, jdk=None,
                              vm_options="-Xms1024m -Xmx1024m -Xss512m"):
    log.info("removing comments.")

    cmd_arr = []
    if jdk is not None and isdir(jdk):
        cmd_arr.append("JAVA_HOME='" + jdk + "'")
        cmd_arr.append(join(jdk, 'bin', 'java'))
    else:
        cmd_arr.append("java")
    if vm_options:
        cmd_arr.append(vm_options)
    cmd_arr.append("-jar")
    cmd_arr.append(c_r_jar)
    cmd_arr.append(repo_path)
    cmd = " ".join(cmd_arr)
    print("call jar cmd ... {0}".format(cmd))
    from utils.cmd_utils import shellCallTemplate
    return shellCallTemplate(cmd)
