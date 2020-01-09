#!/usr/bin/env python3

import ssl
import sys
from argparse import ArgumentParser
from base64 import b64decode
from os import getenv
from socket import AF_INET, SOCK_STREAM, socket


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
        return getenv("IRC_TARGETS").split(",")

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
        return b64decode(getenv("IRC_TARGETS")).decode().split(",")

    @property
    def irc_extra(self):
        return "{}: ".format(getenv("IRC_EXTRA"))


def get_host():
    if getenv("APPVEYOR"):
        return AppVeyor()

    if getenv("GITLAB_CI"):
        return GitLab()

    sys.stderr.write("invalid host\n")
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
        "--stage",
        choices=["start", "success", "failure"],
        required=True,
        help="Current stage.",
    )
    return ap.parse_args()


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


def report(server, port, nick, targets, message):
    ctx = ssl.create_default_context()
    with socket(AF_INET, SOCK_STREAM) as plain:
        with ctx.wrap_socket(plain, server_hostname=server) as sock:
            sock.connect((server, port))
            sock.send("NICK {}\r\n".format(nick).encode())
            sock.send("USER {0} {0} {0} {0}\r\n".format(nick).encode())

            f = sock.makefile()
            while True:
                line = f.readline()
                if not line:
                    break

                fields = line.split()
                if len(fields) >= 1:
                    if fields[0] == "PING":
                        sock.send("PONG {}\r\n".format(fields[1]).encode())
                    elif fields[1] == "376":
                        for target in targets:
                            sock.send(
                                "PRIVMSG {} :{}\r\n".format(
                                    target, message
                                ).encode()
                            )
                            sock.send("QUIT\r\n".encode())
                    elif fields[1] == "433":
                        nick += "_"
                        sock.send("NICK {}\r\n".format(nick).encode())


def main():
    args = parse_args()
    host = get_host()
    message = format_message(host, args.stage)
    report(
        host.irc_server,
        host.irc_port,
        host.irc_nick,
        host.irc_targets,
        message,
    )


if __name__ == "__main__":
    main()
