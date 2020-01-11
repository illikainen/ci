#!/usr/bin/env bash

set -o errexit
set -o nounset
set -o pipefail

export GIT_TEST_OPTS="--immediate --tee --verbose-log --root=t/test-results"
export CI_DESTDIR="${HOME}/build/git"
export PATH="${CI_DESTDIR}/bin:${PATH}"

ci_build() {
    if [[ -n "${CI_TRIGGER_COMMIT:-}" ]]; then
        git reset --hard "$CI_TRIGGER_COMMIT"
    fi
    echo "building $(git rev-parse HEAD)"

    if [[ ! -f "configure" ]]; then
        make configure
        {
            echo "DEVELOPER = 1"
            echo "DEVOPTS = pedantic"
            echo "CFLAGS += -std=c99 -fstack-protector-all"
            echo "LDFLAGS += -Wl,-z,relro -Wl,-z,now"
        } > config.mak
        ./configure --prefix="$CI_DESTDIR"
    fi

    make -j"$(nproc)"
    make install
}

ci_test() {
    key="Signed-off-by"
    if ! git log -1 --format="%(trailers:key=$key)" |grep "^$key"; then
        echo "missing trailer $key" >&2
        exit 1
    fi

    if git diff HEAD^ HEAD |grep -P '^\+ [^*]'; then
        echo "indent with tabs" >&2
        exit 1
    fi

    make test
}

main() {
    ci_build
    ci_test
}

main "$@"
