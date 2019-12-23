#!/usr/bin/env bash

set -o errexit
set -o nounset
set -o pipefail

RED="\\033[31m"
GREEN="\\033[32m"
RESET="\\033[0m"

ci_info() {
    echo -e "${GREEN}$*${RESET}"
}

ci_error() {
    echo -e "${RED}ERROR${RESET}: $*" >&2
    exit 1
}

ci_is_debian() {
    command -v lsb_release >/dev/null &&
        [[ "$(lsb_release --id --short)" == "Debian" ]]
}

ci_is_ubuntu() {
    command -v lsb_release >/dev/null &&
        [[ "$(lsb_release --id --short)" == "Ubuntu" ]]
}

ci_is_centos() {
    test -f /etc/centos-release
}

ci_is_fedora() {
    test -f /etc/fedora-release
}

ci_on_start() {
    if ci_is_debian || ci_is_ubuntu; then
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
    local project="${CI}/projects/${CI_PROJECT:-missing}/ci.sh"

    if ! test -f "$project"; then
        ci_error "invalid project: $project"
    fi

    # shellcheck disable=SC1090
    source "$project"

    local cmd
    for cmd in "$@"; do
        if ! command -v "ci_${cmd}"; then
            ci_error "invalid command: $cmd"
        fi
        ci_info "running $cmd"
        "ci_${cmd}"
    done
}

if [[ "$(basename "$0")" == "ci.sh" ]]; then
    main "$@"
fi
