import sys
import ctypes
import os
import shutil
import subprocess
import tempfile

CLONE_NEWPID = 0x20000000


def run(command, *args):
    tempRootPath = tempfile.mkdtemp()
    commandFileName = os.path.basename(command)
    commandPath = os.path.join("/", commandFileName)

    shutil.copy2(command, tempRootPath)
    os.chroot(tempRootPath)

    libc = ctypes.CDLL(None)
    libc.unshare(CLONE_NEWPID)

    process = subprocess.Popen(
        [commandPath, *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    stdout, stderr = process.communicate()

    print(stdout.decode("utf-8"), end="")
    print(stderr.decode("utf-8"), file=sys.stderr, end="")

    code = process.wait()
    sys.exit(code)
