import subprocess
import tempfile
import shutil
import sys
import os


def run(command, *args):
    tempRootPath = tempfile.mkdtemp()
    commandFileName = os.path.basename(command)
    commandPath = os.path.join('/', commandFileName)

    shutil.copy2(command, tempRootPath)
    os.chroot(tempRootPath)

    process = subprocess.Popen(
        [commandPath, *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()

    print(stdout.decode("utf-8"), end="")
    print(stderr.decode("utf-8"), file=sys.stderr, end="")

    code = process.wait()
    sys.exit(code)


def main():
    command = sys.argv[3]
    args = sys.argv[4:]

    run(command, *args)


if __name__ == "__main__":
    main()
