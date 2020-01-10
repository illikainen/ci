import sys
from os import getenv
from pathlib import Path

# If we run outside of a container and start a build with:
#
#     $ docker run ...
#
# then LOCAL_SRC and CONTAINER_SRC will differ.  Otherwise they should
# be the same path, because the local CI source is copied into the image
# when it's built.
LOCAL_SRC = Path(sys.argv[0]).absolute().parent
CONTAINER_SRC = Path(getenv("CI_SRC", "/src/ci"))

# The SHA256 digests for locally built images are stored in this file in
# order to work with DOCKER_CONTENT_TRUST.  Local images built from
# signed images where the end-result is unsigned can be started with:
#
#     $ docker run sha256:<digest of the locally built image>
DOCKER_IDS = Path.home() / ".ci" / "docker-ids.json"
