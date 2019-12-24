#!/usr/bin/env python3

import ssl
import sys
from argparse import ArgumentParser
from base64 import b64decode
from logging import DEBUG, basicConfig
from os import getenv

from irc.client import IRC
from irc.connection import Factory


class AppVeyor:
    @property
    def branch(self):
        return getenv("APPVEYOR_REPO_BRANCH")

    @property
    def commit(self):
        return getenv("APPVEYOR_REPO_COMMIT")

    @property
    def project(self):
        return getenv("APPVEYOR_PROJECT_NAME")

    @property
    def url(self):
        return "{url}/project/{account}/{project}/builds/{build}".format(
            url=getenv("APPVEYOR_URL"),
            account=getenv("APPVEYOR_ACCOUNT_NAME"),
            project=getenv("APPVEYOR_PROJECT_NAME"),
            build=getenv("APPVEYOR_BUILD_ID"),
        )

    @property
    def irc_server(self):
        return getenv("IRC_SERVER")

    @property
    def irc_port(self):
        return int(getenv("IRC_PORT"))

    @property
    def irc_nick(self):
        return getenv("IRC_NICK")

    @property
    def irc_targets(self):
        return getenv("IRC_TARGETS")

    @property
    def irc_extra(self):
        return ""


class GitLab:
    @property
    def branch(self):
        return getenv("CI_COMMIT_BRANCH")

    @property
    def commit(self):
        return getenv("CI_TRIGGER_COMMIT", getenv("CI_COMMIT_SHA"))

    @property
    def project(self):
        return getenv("CI_PROJECT_NAME")

    @property
    def url(self):
        return getenv("CI_JOB_URL")

    @property
    def irc_server(self):
        return b64decode(getenv("IRC_SERVER")).decode()

    @property
    def irc_port(self):
        return int(b64decode(getenv("IRC_PORT")).decode())

    @property
    def irc_nick(self):
        return b64decode(getenv("IRC_NICK")).decode()

    @property
    def irc_targets(self):
        return b64decode(getenv("IRC_TARGETS")).decode()

    @property
    def irc_extra(self):
        return "{}: ".format(getenv("IRC_EXTRA"))


def get_host():
    if getenv("APPVEYOR"):
        return AppVeyor()

    if getenv("GITLAB_CI"):
        return GitLab()

    sys.stderr.write("invalid host")
    sys.exit(1)


def green(msg):
    return "\x0303{}\x0f".format(msg)


def red(msg):
    return "\x0304{}\x0f".format(msg)


def purple(msg):
    return "\x0306{}\x0f".format(msg)


def yellow(msg):
    return "\x0308{}\x0f".format(msg)


def parse_args():
    ap = ArgumentParser()
    ap.add_argument(
        "--debug",
        default=bool(int(getenv("IRC_DEBUG", "0"))),
        action="store_true",
        help="Enable debug messages.",
    )
    ap.add_argument(
        "--no-ssl",
        default=bool(int(getenv("IRC_NO_SSL", "0"))),
        action="store_true",
        help="Disable SSL connections.",
    )
    ap.add_argument(
        "--stage",
        choices=["start", "success", "failure"],
        required=True,
        help="Current stage.",
    )

    args = ap.parse_args()
    for value in vars(args).values():
        if value is None:
            ap.print_usage()
            sys.exit(1)
    return args


def format_message(host, stage):
    if stage == "start":
        s = yellow("starting")
    elif stage == "success":
        s = green("success")
    else:
        s = red("failure")
    return "{extra}{s}: {project} at {commit} on {branch} - {url}".format(
        project=host.project,
        branch=host.branch,
        url=host.url,
        extra=host.irc_extra,
        commit=purple(host.commit),
        s=s,
    )


def on_welcome(connection, _event):
    connection.privmsg_many(connection.targets, connection.message)
    connection.disconnect()


def on_disconnect(_connection, _event):
    raise SystemExit()


def on_nicknameinuse(connection, _event):
    connection.nickname += "_"
    connection.nick(connection.nickname)


def main():
    args = parse_args()

    if args.debug:
        basicConfig(level=DEBUG)

    if args.no_ssl:
        factory = Factory()
    else:
        factory = Factory(wrapper=ssl.wrap_socket)

    host = get_host()
    client = IRC()
    connection = client.server().connect(
        host.irc_server, host.irc_port, host.irc_nick, connect_factory=factory
    )
    connection.targets = host.irc_targets.split(",")
    connection.message = format_message(host, args.stage)
    connection.add_global_handler("welcome", on_welcome)
    connection.add_global_handler("disconnect", on_disconnect)
    connection.add_global_handler("nicknameinuse", on_nicknameinuse)
    client.process_forever()


if __name__ == "__main__":
    main()
