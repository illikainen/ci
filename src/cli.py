#!/usr/bin/env python3

from argparse import ArgumentParser
from os import environ
from pathlib import Path

from .exceptions import CIError
from .utils import error, get_os, info, iterdir
from . import const, irc, image, pipeline


def main():
    environ["DOCKER_CONTENT_TRUST"] = "1"
    args = _parse_args()
    ci = const.LOCAL_SRC if args.local else const.CONTAINER_SRC
    notify = getattr(args, "notify", False) and not args.local

    info("running {}", "locally" if args.local else "on ci")

    if notify:
        irc.notify("start")

    try:
        args.fn(ci, args)
    except CIError as err:
        if notify:
            irc.notify("failure")
        error("{}", err)

    if notify:
        irc.notify("success")
    info("success")


def _parse_args():
    local = not environ.get("local")
    ap = ArgumentParser()
    ap.set_defaults(fn=lambda *_args, **_kwargs: ap.error("missing action"))
    sp = ap.add_subparsers()

    bi = sp.add_parser("build-images")
    bi.set_defaults(fn=_build_images)
    bi.add_argument("--clean", action="store_true")
    bi.add_argument("--notify", action="store_true")
    bi.add_argument("--images", nargs="*")
    bi.add_argument("--projects", nargs="*")
    bi.add_argument("--push", action="store_true")

    rp = sp.add_parser("run-pipeline")
    rp.set_defaults(fn=_run_pipeline)
    rp.add_argument("--clean", action="store_true")
    rp.add_argument("--notify", action="store_true")
    rp.add_argument("--trigger", action="store_true")
    if local:
        rp.add_argument("--build", action="store_true")
        rp.add_argument("--images", nargs="*")

    args = ap.parse_args()
    args.local = local
    return args


def _build_images(ci, args):
    for proj in iterdir(ci / "projects", args.projects):
        for img in iterdir(proj / "dockerfiles", args.images):
            info("{}: {}: building", proj.name, img.name)
            image.build(proj, img, args)
            if args.push:
                info("{}: {}: pushing", proj.name, img.name)
                image.push(proj, img, args)


def _run_pipeline(ci, args):
    proj = Path.cwd()
    if args.local:
        images = ci / "projects" / proj.name / "dockerfiles"
        for img in iterdir(images, args.images):
            if args.build:
                info("{}: {}: building", proj.name, img.name)
                image.build(proj, img, args)
            info("{}: {}: running", proj.name, img.name)
            image.run(proj, img, args)
    else:
        info("{}: {}: running", proj.name, get_os())
        image.run(proj, None, args)

    if args.trigger:
        p = pipeline.get()
        p.trigger()
