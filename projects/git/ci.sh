#!/usr/bin/env bash

ci_install() {
    if ci_is_alpine; then
        ci_sudo apk update
        ci_sudo apk add \
                asciidoc \
                autoconf \
                build-base \
                curl-dev \
                diffutils \
                findutils \
                gettext-dev \
                gnupg \
                grep \
                openssh-client \
                pcre2-dev \
                pkgconf \
                python \
                subversion \
                tcl \
                unzip
    elif ci_is_debian || ci_is_ubuntu; then
        ci_sudo cp /etc/apt/sources.list /etc/apt/sources.list.d/src.list
        ci_sudo sed -i 's/^deb[ \s]/deb-src /' /etc/apt/sources.list.d/src.list

        ci_sudo apt-get update
        ci_sudo apt-get --assume-yes build-dep git
        ci_sudo apt-get --assume-yes install autoconf automake gnupg gpgsm
    elif ci_is_centos || ci_is_fedora; then
        ci_sudo dnf --assumeyes install \
                acl \
                asciidoc \
                autoconf \
                automake \
                diffutils \
                expat-devel \
                findutils \
                gawk \
                gcc \
                gcc-c++ \
                gettext-devel \
                gnupg2 \
                gnupg2-smime \
                libcurl-devel \
                libsecret-devel \
                make \
                openssl-devel \
                pcre2-devel \
                perl-Memoize \
                pkgconfig \
                python2 \
                python3 \
                subversion \
                subversion-perl \
                tcl \
                tk \
                xmlto \
                zlib-devel
        ci_sudo ln -s /usr/bin/python2 /usr/bin/python
    fi
}

ci_build() {
    if [[ -n "${CI_TRIGGER_COMMIT:-}" ]]; then
        git reset --hard "$CI_TRIGGER_COMMIT"
    fi
    ci_info "building $(git rev-parse HEAD)"

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
    export PATH="${CI_DESTDIR}/bin:${PATH}"

    key="Signed-off-by"
    if ! git log -1 --format="%(trailers:key=$key)" |grep "^$key"; then
        echo "missing trailer $key" >&2
        exit 1
    fi

    if git diff HEAD^ HEAD |grep -P '^\+ [^*]'; then
        echo "indent with tabs" >&2
        exit 1
    fi

    # FIXME
    if ci_is_alpine; then
        export GIT_SKIP_TESTS="t4061 t5616 t5703"
    fi

    make test
}
