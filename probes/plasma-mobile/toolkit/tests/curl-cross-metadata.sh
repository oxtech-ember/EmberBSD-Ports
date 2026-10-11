#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Exercise the production post-install rewrite.
set -eu
[ "$#" = 2 ] || { echo "Usage: $0 PREPARED_PKGSRC NEW_WORK" >&2; exit 2; }
pkgsrc=$(CDPATH= cd -- "$1" && pwd)
mkdir "$2"
work=$(CDPATH= cd -- "$2" && pwd)
mkdir -p "$work/stage/usr/pkg/bin" "$work/stage/usr/pkg/lib/pkgconfig"
cat > "$work/stage/usr/pkg/bin/curl-config" <<'CONFIG'
#!/bin/sh
case "$1" in
--cc)
    echo 'aarch64--netbsd-gcc';;
--libs) echo '-L/cross/[root].0/usr/pkg/lib -lcurl';;
--configure) echo '--build=aarch64-apple-darwin CC=aarch64--netbsd-gcc';;
esac
CONFIG
printf '%s\n' 'prefix=/usr/pkg' 'Libs.private: -L/cross/[root].0/usr/pkg/lib -lssl' > "$work/stage/usr/pkg/lib/pkgconfig/libcurl.pc"
awk '/^ember-curl-cross-metadata:/ { copying=1 } copying && /^\.endif/ { exit } copying { print }' \
    "$pkgsrc/www/curl/Makefile" > "$work/Makefile"
[ -s "$work/Makefile" ]
make=${BMAKE:-bmake}
rewrite() {
    "$make" -r -m / -f "$work/Makefile" ember-curl-cross-metadata \
        RUN= CP=cp AWK=awk MV=mv DESTDIR="$work/stage" PREFIX=/usr/pkg \
        CROSS_DESTDIR="$1" MACHINE_GNU_PLATFORM=aarch64--netbsd
}
rewrite '/cross/[root].0'
config=$work/stage/usr/pkg/bin/curl-config
pc=$work/stage/usr/pkg/lib/pkgconfig/libcurl.pc
[ "$(sh "$config" --cc)" = /usr/pkg/gcc16/bin/gcc ]
[ "$(sh "$config" --libs)" = '-L/usr/pkg/lib -lcurl' ]
[ "$(sh "$config" --configure)" = '--build=aarch64-apple-darwin CC=aarch64--netbsd-gcc' ]
grep -qx 'Libs.private: -L/usr/pkg/lib -lssl' "$pc"
cp "$config" "$work/expected-config"
cp "$pc" "$work/expected-pc"
rewrite '/cross/[root].0'
rewrite ''
cmp "$config" "$work/expected-config"
cmp "$pc" "$work/expected-pc"
echo 'PASS: literal sysroot removal, target compiler, historical configure arguments, idempotence and empty-root guard'
