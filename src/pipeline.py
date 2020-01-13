from os import environ

from .exceptions import CIError
from .utils import base64decode, get_author, get_commits, info, split, urlreq


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
        with urlreq(url) as res:
            return [build.get("commitId") for build in res.get("builds", [])]

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
        with urlreq(url, data=data, headers=headers):
            pass


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
        headers = {"PRIVATE-TOKEN": self.token}
        commits = []
        ids = []
        with urlreq(url, headers=headers) as res:
            for pipeline in res:
                commits.append(pipeline.get("sha"))
                ids.append(pipeline.get("id"))

        # The commit hash has to be extracted from the environment
        # variables for triggered builds because the "sha" field seems
        # to be inherited from the build that does the triggering.
        for pipeline in ids:
            vurl = "{}/{}/variables".format(url, pipeline)
            with urlreq(vurl, headers=headers) as res:
                for elt in res:
                    if elt.get("key") == "CI_TRIGGER_COMMIT":
                        commits.append(elt.get("value"))

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
        with urlreq(url, data=data, is_json=False):
            pass


def get():
    if environ.get("APPVEYOR"):
        return AppVeyor()
    if environ.get("GITLAB_CI"):
        return GitLab()
    raise CIError("unknown environment")
