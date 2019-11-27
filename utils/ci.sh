#!/usr/bin/env bash

set -o errexit
set -o nounset
set -o pipefail
set -o xtrace

ci_on_start() {
    if test -f /etc/debian_version; then
        sudo apt-get update
        sudo apt-get --yes install python3-irc
    fi

    "${CI}/utils/report-irc.py" --stage start
}

ci_on_success() {
    "${CI}/utils/report-irc.py" --stage success
}

ci_on_failure() {
    "${CI}/utils/report-irc.py" --stage failure
}

ci_on_finish() {
    "${CI}/utils/start-build.py"
}

main() {
    local cmd="ci_${1:-missing}"
    local project="${CI}/projects/${APPVEYOR_PROJECT_NAME:-missing}/ci.sh"

    if ! test -f "$project"; then
        echo "ERROR: invalid project: $project" >&2
        exit 1
    fi

    # shellcheck disable=SC1090
    source "$project"

    if ! command -v "$cmd"; then
        echo "ERROR: invalid command: $cmd" >&2
        exit 1
    fi

    shift
    "$cmd" "$@"
}

main "$@"
