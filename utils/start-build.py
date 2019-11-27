#!/usr/bin/env python3
#
# AppVeyor only builds the tip of a multi-commit push.  This horrible
# hack trigger a build for every commit reachable from HEAD until either
# a new author is found or an already-built commit is encountered.

import json
import sys
from argparse import ArgumentParser
from os import getenv
from subprocess import PIPE, run
from urllib.error import HTTPError
from urllib.request import Request, urlopen

API_URL = "https://ci.appveyor.com/api/"


def get_author():
    rv = run(["git", "log", "-1", "--format=%ae"], stdout=PIPE)
    if rv.returncode:
        sys.exit("ERROR: cannot retrieve author")
    return rv.stdout.decode().strip()


def get_commits(author, history):
    rv = run(["git", "log", "--format=%H %ae", "HEAD^1"], stdout=PIPE)
    if rv.returncode:
        sys.exit("ERROR: cannot retrieve commits")

    commits = []
    for line in rv.stdout.decode().strip().split("\n"):
        hsh, athr = line.split(" ")
        if athr != author or hsh in history:
            break
        commits.append(hsh)
    return commits


def get_history(account, project):
    url = f"{API_URL}/projects/{account}/{project}/history?recordsNumber=100"
    commits = []
    try:
        with urlopen(url) as res:
            obj = json.loads(res.read())
            builds = obj.get("builds", [])
            for build in builds:
                commits.append(build.get("commitId"))
    except HTTPError:
        sys.exit("ERROR: cannot retrieve history")
    return commits


def start_build(api_key, account, project, branch, commit):
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    data = {
        "accountName": account,
        "projectSlug": project,
        "commitId": commit,
        "branch": branch,
    }
    url = f"{API_URL}/account/{account}/builds"

    req = Request(url, data=json.dumps(data).encode(), headers=headers)
    try:
        urlopen(req)
    except HTTPError:
        sys.exit("ERROR: cannot start build")


def parse_args():
    ap = ArgumentParser()
    ap.add_argument(
        "--api-key", default=getenv("API_KEY"), help="AppVeyor API key."
    )
    ap.add_argument(
        "--account",
        default=getenv("APPVEYOR_ACCOUNT_NAME"),
        help="AppVeyor account name.",
    )
    ap.add_argument(
        "--project",
        default=getenv("APPVEYOR_PROJECT_NAME"),
        help="AppVeyor project name.",
    )
    ap.add_argument(
        "--branch",
        default=getenv("APPVEYOR_REPO_BRANCH"),
        help="Branch being built.",
    )

    args = ap.parse_args()
    for value in vars(args).values():
        if value is None:
            ap.print_usage()
            sys.exit(1)
    return args


def main():
    args = parse_args()
    author = get_author()
    history = get_history(args.account, args.project)
    commits = get_commits(author, history)

    for commit in commits:
        print(f"starting build for {commit}")
        start_build(
            args.api_key, args.account, args.project, args.branch, commit
        )


if __name__ == "__main__":
    main()
