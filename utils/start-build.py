#!/usr/bin/env python3
#
# AppVeyor and GitLab only builds the tip of a multi-commit push.  This
# horrible hack trigger a build for every commit reachable from HEAD
# until either a new author is found or an already-built commit is
# encountered.

import json
import sys
from os import getenv
from subprocess import PIPE, run
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class AppVeyor:
    def __init__(self):
        self.url = getenv("APPVEYOR_URL")
        self.account = getenv("APPVEYOR_ACCOUNT_NAME")
        self.project = getenv("APPVEYOR_PROJECT_NAME")
        self.branch = getenv("APPVEYOR_REPO_BRANCH")
        self.key = getenv("API_KEY")

    def get_history(self):
        url = "{}/api/projects/{}/{}/history?recordsNumber=100".format(
            self.url, self.account, self.project
        )
        commits = []
        try:
            with urlopen(url) as res:
                obj = json.loads(res.read().decode())
                builds = obj.get("builds", [])
                for build in builds:
                    commits.append(build.get("commitId"))
        except HTTPError:
            sys.exit("ERROR: cannot retrieve history")
        return commits

    def start_build(self, commit):
        url = "{}/api/account/{}/builds".format(self.url, self.account)
        headers = {
            "Authorization": "Bearer {}".format(self.key),
            "Content-Type": "application/json",
        }
        data = {
            "accountName": self.account,
            "projectSlug": self.project,
            "branch": self.branch,
            "commitId": commit,
        }
        req = Request(url, data=json.dumps(data).encode(), headers=headers)
        try:
            urlopen(req)
        except HTTPError:
            sys.exit("ERROR: cannot start build")


class GitLab:
    def __init__(self):
        self.url = getenv("CI_API_V4_URL")
        self.project_id = getenv("CI_PROJECT_ID")
        self.branch = getenv("CI_COMMIT_BRANCH")
        self.token = getenv("CI_JOB_TOKEN")

    def get_history(self):
        url = "{}/projects/{}/pipelines".format(self.url, self.project_id)
        commits = []
        try:
            with urlopen(url) as res:
                for pipeline in json.loads(res.read().decode()):
                    commits.append(pipeline.get("sha"))
        except HTTPError:
            sys.exit("ERROR: cannot retrieve history")
        return commits

    def start_build(self, commit):
        url = "{}/projects/{}/trigger/pipeline".format(
            self.url, self.project_id
        )
        data = {
            "token": self.token,
            "ref": self.branch,
            "variables[CI_TRIGGER_COMMIT]": commit,
        }
        req = Request(url, data=urlencode(data).encode())
        try:
            urlopen(req)
        except HTTPError:
            sys.exit("ERROR: cannot start build")


def get_host():
    if getenv("APPVEYOR"):
        return AppVeyor()

    if getenv("GITLAB_CI"):
        return GitLab()

    sys.stderr.write("invalid host")
    sys.exit(1)


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


def main():
    if not getenv("CI_CAN_START_BUILD"):
        return

    host = get_host()
    author = get_author()
    history = host.get_history()
    commits = get_commits(author, history)

    for commit in commits:
        print("starting build for {}".format(commit))
        host.start_build(commit)


if __name__ == "__main__":
    main()
