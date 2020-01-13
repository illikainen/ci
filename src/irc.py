import ssl
from socket import AF_INET, SOCK_STREAM, socket

from . import pipeline
from .utils import get_os


def notify(stage):
    p = pipeline.get()
    message = _format_message(p, stage)
    ctx = ssl.create_default_context()

    with socket(AF_INET, SOCK_STREAM) as plain:
        with ctx.wrap_socket(plain, server_hostname=p.irc_server) as sock:
            sock.connect((p.irc_server, p.irc_port))
            nick = p.irc_nick
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
                        for target in p.irc_targets:
                            sock.send(
                                "PRIVMSG {} :{}\r\n".format(
                                    target, message
                                ).encode()
                            )
                            sock.send("QUIT\r\n".encode())
                    elif fields[1] == "433":
                        nick += "_"
                        sock.send("NICK {}\r\n".format(nick).encode())


def _format_message(p, stage):
    green = "\x0303{}\x0f"
    red = "\x0304{}\x0f"
    purple = "\x0306{}\x0f"
    yellow = "\x0308{}\x0f"

    if stage == "start":
        s = yellow.format("starting")
    elif stage == "success":
        s = green.format("success")
    else:
        s = red.format("failure")

    return "{os}: {s}: {project} at {commit} on {branch} - {url}".format(
        os=get_os(),
        project=p.project,
        branch=p.branch,
        url=p.build_url,
        commit=purple.format(p.commit),
        s=s,
    )
