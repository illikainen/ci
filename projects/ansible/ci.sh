#!/usr/bin/env bash

ci_install() {
    if [[ "$PYTHON" == "2.7" ]]; then
        if ci_is_debian || ci_is_ubuntu; then
            ci_sudo apt-get install --yes python-apt
        fi
        virtualenv -p "python$PYTHON" --system-site-packages venv
    else
        if ci_is_debian || ci_is_ubuntu; then
            ci_sudo apt-get install --yes python3-apt python3-venv python3-dev
        fi
        "python$PYTHON" -m venv --system-site-packages venv
    fi

    # shellcheck disable=SC1091
    source venv/bin/activate
    pip install \
        -r requirements.txt \
        -r docs/docsite/requirements.txt \
        -r test/lib/ansible_test/_data/requirements/coverage.txt \
        -r test/lib/ansible_test/_data/requirements/integration.txt \
        -r test/lib/ansible_test/_data/requirements/network-integration.txt \
        -r test/lib/ansible_test/_data/requirements/units.txt \
        -r test/sanity/requirements.txt \
        -r test/units/requirements.txt
}

ci_build() {
    if [[ -n "${CI_TRIGGER_COMMIT:-}" ]]; then
        git reset --hard "$CI_TRIGGER_COMMIT"
    fi
    ci_info "building $(git rev-parse HEAD)"

    # shellcheck disable=SC1091
    source venv/bin/activate

    if test "$DOCS" = 1; then
        make webdocs
    fi

    make install
}

ci_test() {
    # ansible-test --changed doesn't seem to work reliably, so determine the
    # target to test based on the branch name instead.  Meh...
    local target
    target="$(echo "$APPVEYOR_REPO_BRANCH" \
        |sed -E -e 's/^.*-?[0-9]+-//' -e 's/-/_/g')"

    if [[ -z "$target" ]]; then
        echo "WARNING: unknown target" >&2
        exit 0
    fi

    # shellcheck disable=SC1091
    source venv/bin/activate

    ansible-test units --python "$PYTHON" --coverage "$target"
    ansible-test integration --python "$PYTHON" --coverage \
                 --allow-root --allow-destructive "$target"
    ansible-test coverage report --python "$PYTHON" --include "*$target*"
}
