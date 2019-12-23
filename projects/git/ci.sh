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
