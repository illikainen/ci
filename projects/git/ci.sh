#!/usr/bin/env bash

ci_install() {
    if ci_is_debian || ci_is_ubuntu; then
        ci_sudo cp /etc/apt/sources.list /etc/apt/sources.list.d/src.list
        ci_sudo sed -i 's/^deb[ \s]/deb-src /' /etc/apt/sources.list.d/src.list

        ci_sudo apt-get update
        ci_sudo apt-get --assume-yes build-dep git
        ci_sudo apt-get --assume-yes install autoconf automake gnupg gpgsm
    fi
}

ci_build() {
    make configure
    {
        echo "DEVELOPER = 1"
        echo "DEVOPTS = pedantic"
        echo "CFLAGS += -fno-omit-frame-pointer -fstack-protector-all"
        echo "LDFLAGS += -Wl,-z,relro -Wl,-z,now"
    } > config.mak

    ./configure --prefix="$CI_DESTDIR"
    make -j"$(nproc)"
    make install
}

ci_test() {
    key="Signed-off-by"
    if ! git log -1 --format="%(trailers:key=$key)" |grep -q "^$key"; then
        echo "missing trailer $key" >&2
        exit 1
    fi

    if git diff HEAD^ HEAD |grep -P '^\+ [^*]'; then
        echo "indent with tabs" >&2
        exit 1
    fi

    PATH="${CI_DESTDIR}/bin:${PATH}" make test
}
