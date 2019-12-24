#!/usr/bin/env python3

import ssl
import sys
from argparse import ArgumentParser
from logging import DEBUG, basicConfig
from os import getenv, environ

from irc.client import IRC
from irc.connection import Factory


variables = {
    "appveyor": {
        "branch": "{APPVEYOR_REPO_BRANCH}",
        "commit": "{APPVEYOR_REPO_COMMIT}",
        "project": "{APPVEYOR_PROJECT_NAME}",
        "url": (
            "{APPVEYOR_URL}/project/{APPVEYOR_ACCOUNT_NAME}/"
            "{APPVEYOR_PROJECT_NAME}/builds/{APPVEYOR_BUILD_ID}"
        ),
    }
}


def getvar(name):
    for key, value in variables.items():
        if getenv(key.upper()):
            return value[name].format(**environ)
    return getenv(name)


def green(msg):
    return f"\x0303{msg}\x0f"


def red(msg):
    return f"\x0304{msg}\x0f"


def purple(msg):
    return f"\x0306{msg}\x0f"


def yellow(msg):
    return f"\x0308{msg}\x0f"


def parse_args():
    ap = ArgumentParser()
    ap.add_argument(
        "--server",
        default=getenv("IRC_SERVER"),
        help="IRC server to connect to.",
    )
    ap.add_argument(
        "--port",
        default=int(getenv("IRC_PORT", "6697")),
        type=int,
        help="Port that the server is listening on.",
    )
    ap.add_argument(
        "--nick",
        default=getenv("IRC_NICK"),
        help="Nickname to use.  An underscore is appended if it's in use.",
    )
    ap.add_argument(
        "--channels",
        default=getenv("IRC_CHANNELS"),
        help="Comma-separated list of channels.",
    )
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


def format_message(args):
    if args.stage == "start":
        stage = yellow("starting")
    elif args.stage == "success":
        stage = green("success")
    else:
        stage = red("failure")

    url = getvar("url")
    project = getvar("project")
    branch = getvar("branch")
    commit = purple(getvar("commit"))

    return f"{stage}: {project} at {commit} on {branch} - {url}"


def on_welcome(connection, _event):
    connection.privmsg_many(connection.channels, connection.message)
    connection.disconnect()


def on_disconnect(_connection, _event):
    raise SystemExit()


def on_nicknameinuse(connection, _event):
    connection.nick(f"{connection.nickname}_")


def main():
    args = parse_args()

    if args.debug:
        basicConfig(level=DEBUG)

    if args.no_ssl:
        factory = Factory()
    else:
        factory = Factory(wrapper=ssl.wrap_socket)

    client = IRC()
    connection = client.server().connect(
        args.server, args.port, args.nick, connect_factory=factory
    )
    connection.channels = args.channels.split(",")
    connection.message = format_message(args)
    connection.add_global_handler("welcome", on_welcome)
    connection.add_global_handler("disconnect", on_disconnect)
    connection.add_global_handler("nicknameinuse", on_nicknameinuse)
    client.process_forever()


if __name__ == "__main__":
    main()
