import re
import sys
from base64 import b64decode
from contextlib import contextmanager
from os import chdir, getcwd
from pathlib import Path
from subprocess import PIPE, STDOUT, Popen

from .exceptions import CIError

RED = "\033[01;31m"
GREEN = "\033[01;32m"
RESET = "\033[00m"


def info(fmt, *args, **kwargs):
    msg = fmt.format(*args, **kwargs)
    print("{}info{}: {}".format(GREEN, RESET, msg))


def error(fmt, *args, **kwargs):
    msg = fmt.format(*args, **kwargs)
    print("{}error{}: {}".format(RED, RESET, msg), file=sys.stderr)
    sys.exit(1)


def call(*args, stdin=None):
    args = [str(x) for x in args if x]
    try:
        p = Popen(
            args, stdin=PIPE if stdin else None, stdout=PIPE, stderr=STDOUT
        )
    except OSError as e:
        raise CIError(e.strerror)

    if stdin:
        try:
            p.stdin.write(stdin.encode())
            p.stdin.close()
        except ValueError:
            raise CIError("write failed")

    output = []
    for line in iter(p.stdout.readline, b""):
        s = line.decode()
        print(s, end="")
        output.append(s)

    p.wait()
    if p.returncode:
        raise CIError(args[0])
    return output


def get_os():
    release = {}
    rx = re.compile(r"([A-Z_]+)[ \t]*=[ \t]*(?:\"|')?([^\"'\n$]+)")
    path = Path("/etc/os-release")

    if path.is_file():
        with path.open("r") as f:
            for line in f.readlines():
                m = rx.match(line)
                if m:
                    release[m.group(1)] = m.group(2)

    return "{}-{}".format(
        release.get("ID", "unknown"), release.get("VERSION_ID", "0")
    )


def get_author():
    return call("git", "log", "-1", "--format=%ae")[-1]


def get_commits(author, history):
    lines = call(
        "git", "log", "--no-show-signature", "--format=%H %ae", "HEAD^1"
    )
    commits = []
    for line in lines:
        commit_hash, commit_author = line.split(" ")
        if commit_author != author or commit_hash in history:
            break
        commits.append(commit_hash)
    return commits


def iterdir(path, filters=None):
    filters = [Path(x).absolute().name for x in filters or []]
    for elt in path.is_dir() and path.iterdir() or []:
        if filters and elt.name not in filters:
            continue
        yield elt


def base64decode(s):
    return b64decode(s).decode()


def split(s):
    return s.split(",")


@contextmanager
def cd(path):
    old = getcwd()
    chdir(path)
    try:
        yield
    finally:
        chdir(old)
