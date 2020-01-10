import json
from os import environ
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .exceptions import CIError
from .utils import base64decode, get_author, get_commits, info, split


class Pipeline:
    env = {}

    def trigger(self):
        author = get_author()
        history = self.get_history()
        commits = get_commits(author, history)
        for commit in commits:
            info("starting build for {}", commit)
            self.start_build(commit)

    @staticmethod
    def start_build(commit):
        pass

    @staticmethod
    def get_history():
        return []

    def __getattr__(self, key):
        entry = self.env.get(key)
        if entry:
            names = []
            fns = []
            if isinstance(entry, list):
                for x in entry:
                    if isinstance(x, str):
                        names.append(x)
                    elif callable(x):
                        fns.append(x)

            value = next(
                (y for y in (environ.get(x) for x in names or [entry]) if y),
                None,
            )
            if value:
                for fn in fns:
                    value = fn(value)
                return value
        raise CIError("no value for {}".format(key))


class AppVeyor(Pipeline):
    env = {
        "url": "APPVEYOR_URL",
        "token": "API_KEY",
        "account": "APPVEYOR_ACCOUNT_NAME",
        "project": "APPVEYOR_PROJECT_NAME",
        "project_id": "APPVEYOR_PROJECT_ID",
        "build_id": "APPVEYOR_BUILD_ID",
        "branch": "APPVEYOR_REPO_BRANCH",
        "commit": "APPVEYOR_REPO_COMMIT",
        "irc_server": "IRC_SERVER",
        "irc_port": ["IRC_PORT", int],
        "irc_nick": "IRC_NICK",
        "irc_targets": ["IRC_TARGETS", split],
    }

    @property
    def build_url(self):
        return "{}/project/{}/{}/builds/{}".format(
            self.url, self.account, self.project, self.build_id
        )

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
            raise CIError("cannot retrieve history")
        return commits

    def start_build(self, commit):
        url = "{}/api/account/{}/builds".format(self.url, self.account)
        headers = {
            "Authorization": "Bearer {}".format(self.token),
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
            raise CIError("cannot start build")


class GitLab(Pipeline):
    env = {
        "url": "CI_API_V4_URL",
        "token": "CI_JOB_TOKEN",
        "account": "CI_PROJECT_NAMESPACE",
        "project": "CI_PROJECT_NAME",
        "project_id": "CI_PROJECT_ID",
        "branch": "CI_COMMIT_BRANCH",
        "commit": ["CI_TRIGGER_COMMIT", "CI_COMMIT_SHA"],
        "build_url": "CI_JOB_URL",
        "registry_url": "CI_REGISTRY",
        "registry_namespace_url": "CI_REGISTRY_IMAGE",
        "registry_username": "CI_REGISTRY_USER",
        "registry_password": "CI_REGISTRY_PASSWORD",
        "irc_server": ["IRC_SERVER", base64decode],
        "irc_port": ["IRC_PORT", base64decode, int],
        "irc_nick": ["IRC_NICK", base64decode],
        "irc_targets": ["IRC_TARGETS", base64decode, split],
    }

    def get_history(self):
        url = "{}/projects/{}/pipelines".format(self.url, self.project_id)
        commits = []
        try:
            ids = []
            with urlopen(url) as res:
                for pipeline in json.loads(res.read().decode()):
                    commits.append(pipeline.get("sha"))
                    ids.append(pipeline.get("id"))
            # The commit hash has to be extracted from the environment
            # variables for triggered builds.
            for pipeline in ids:
                with urlopen("{}/{}/variables".format(url, pipeline)) as res:
                    for elt in json.loads(res.read().decode()):
                        if elt.get("key") == "CI_TRIGGER_COMMIT":
                            commits.append(elt.get("value"))
        except HTTPError:
            raise CIError("cannot retrieve history")
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
            raise CIError("cannot start build")


def get():
    if environ.get("APPVEYOR"):
        return AppVeyor()
    if environ.get("GITLAB_CI"):
        return GitLab()
    raise CIError("unknown environment")
