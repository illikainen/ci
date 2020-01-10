import json
import re
from pathlib import Path
from shutil import rmtree
from tempfile import TemporaryDirectory

from .exceptions import CIError
from .utils import call, cd
from . import const, pipeline


def build(project, image, args):
    with cd(image.parent):
        tag = _get_local_tag(project, image)
        with TemporaryDirectory() as name:
            tmp = Path(name) / "id"
            call(
                "docker",
                "build",
                "--pull",
                "--iidfile={}".format(tmp),
                "--file={}".format(image),
                "--tag={}".format(tag),
                const.LOCAL_SRC,
            )
            _write_id(tag, tmp.read_text().strip())

    if args.clean:
        call("docker", "system", "prune", "--force")


def push(project, image, _args):
    p = pipeline.get()

    call(
        "docker",
        "login",
        "--username={}".format(p.registry_username),
        "--password-stdin",
        p.registry_url,
        stdin=p.registry_password,
    )

    local_tag = _get_local_tag(project, image)
    registry_tag = _get_registry_tag(project, image, p.registry_namespace_url)
    call("docker", "tag", local_tag, registry_tag)
    call("docker", "push", registry_tag)


def run(project, image, args):
    if args.local:
        return _run_local(project, image, args)
    return _run_ci(project, image, args)


def _run_local(project, image, args):
    tag = _get_local_tag(project, image)
    identifier = _get_id(tag)
    env = ["CI=1"] + _get_env()
    workdir = Path("/tmp") / tag.replace(":", "-")

    if args.clean and workdir.is_dir():
        rmtree(workdir)
    workdir.mkdir(parents=True, exist_ok=True)

    call(
        "rsync",
        "--archive",
        "--filter=:- {}".format(project / ".gitignore"),
        "--delete" if args.clean else None,
        "{}/".format(project),
        workdir,
    )
    call(
        "docker",
        "run",
        *["--env={}".format(x) for x in env],
        "--interactive",
        "--rm",
        "--tty",
        "--volume={}:/src/{}".format(workdir, project.name),
        "--workdir=/src/{}".format(project.name),
        identifier,
        const.CONTAINER_SRC / "ci",
        "run-pipeline",
        "--notify" if args.notify else None,
    )


def _run_ci(project, _image, _args):
    call(const.CONTAINER_SRC / "projects" / project.name / "ci.sh")


def _get_local_tag(project, image):
    return "{}/{}:{}".format(const.LOCAL_SRC.name, project.name, image.name)


def _get_registry_tag(project, image, registry):
    return "{}/{}:{}".format(registry, project.name, image.name)


def _get_id(tag):
    ids = (
        json.loads(const.DOCKER_IDS.read_text())
        if const.DOCKER_IDS.exists()
        else {}
    )
    rv = ids.get(tag)
    if not rv:
        raise CIError("no id found for {}".format(tag))
    return rv


def _write_id(tag, identifier):
    ids = (
        json.loads(const.DOCKER_IDS.read_text())
        if const.DOCKER_IDS.exists()
        else {}
    )
    ids[tag] = identifier
    const.DOCKER_IDS.parent.mkdir(parents=True, exist_ok=True)
    const.DOCKER_IDS.write_text(json.dumps(ids, indent=4))


def _get_env():
    path = Path(".env")
    rx = re.compile(r"^[\s]*([^#][A-Z_]*)[\s]*=[\s]*(\"|')?([^\"'$]+)")
    env = []
    if path.is_file():
        for line in path.read_text().split("\n"):
            m = rx.search(line)
            if m:
                groups = m.groups()
                env.append("{}={}".format(groups[0], groups[-1]))
    return env
