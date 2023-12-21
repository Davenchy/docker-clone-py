import subprocess
import sys


def main():
    commandIn = sys.argv[3]
    argsIn = sys.argv[4:]

    command = [commandIn, *argsIn]
    process = subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    print(stdout.decode("utf-8"), end="")
    print(stderr.decode("utf-8"), file=sys.stderr, end="")


if __name__ == "__main__":
    main()
