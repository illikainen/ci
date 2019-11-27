#!/usr/bin/env bash

ci_install() {
    sudo apt-get --yes install \
         asciidoc \
         autoconf \
         automake \
         build-essential \
         libcurl4-gnutls-dev \
         libpcre2-dev \
         zlib1g-dev
}

ci_build() {
    make configure
    {
        echo "DEVELOPER = 1"
        echo "DEVOPTS = pedantic"
        echo "CFLAGS += -fno-omit-frame-pointer -fstack-protector-all"
        echo "LDFLAGS += -Wl,-z,relro -Wl,-z,now"
    } > config.mak

    # FIXME: grep.c is not buildable with pedantic if libpcre is enabled.
    ./configure --prefix="$BUILD" --without-libpcre
    make -j"$(nproc)"
    make install
    make install-html

    cp -a "$BUILD/share/doc/git" "$ARTIFACTS"
}

ci_test() {
    key="Signed-off-by"
    if ! git log -1 --format="%(trailers:key=$key)" |grep -q "^$key"; then
        echo "missing trailer $key" >&2
        exit 1
    fi

    if git diff HEAD^ HEAD |grep -P '^\+ '; then
        echo "indent with tabs" >&2
        exit 1
    fi

    PATH="${BUILD}/bin:${PATH}" make test
}
