#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), host interpreter and installed-path regression.
set -eu
[ "$#" = 5 ] || { echo "Usage: $0 PKGSRC CROSS_MAKECONF NATIVE_MAKECONF PYTHON_SOURCE NEW_WORK" >&2; exit 2; }
pkgsrc=$1 crossconf=$2 nativeconf=$3 source=$4 work=$5
bmake=${BMAKE:-bmake}
mkdir "$work"
for interpreter in python3.15 /nonexistent/ember-python; do
    "$bmake" -C "$pkgsrc/lang/python314" MAKECONF="$crossconf" \
        EMBERBSD_CROSS_BUILD_PYTHON="$interpreter" -v PKG_FAIL_REASON > "$work/invalid.txt"
    grep -q 'EMBERBSD_CROSS_BUILD_PYTHON must name an existing absolute host interpreter' "$work/invalid.txt"
done
"$bmake" -C "$pkgsrc/lang/python314" MAKECONF="$nativeconf" \
    -v CONFIGURE_ARGS > "$work/native-args.txt"
if grep -q -- '--with-build-python=' "$work/native-args.txt"; then
    echo 'Native configuration unexpectedly selects a cross build interpreter' >&2; exit 1
fi
cat > "$work/wrong-python" <<'SH'
#!/bin/sh
echo 3.13
SH
chmod +x "$work/wrong-python"
mkdir "$work/configure"
if (cd "$work/configure" && "$source/configure" \
    --build=aarch64-apple-darwin --host=aarch64-unknown-netbsd \
    --with-build-python="$work/wrong-python") > "$work/wrong-version.log" 2>&1; then
    echo 'Wrong build interpreter version unexpectedly accepted' >&2; exit 1
fi
grep -q 'incompatible version 3.13 (expected: 3.14)' "$work/wrong-version.log"
filter=$pkgsrc/lang/python314/files/target-paths.awk
cat > "$work/input" <<'DATA'
LDFLAGS=-L/tmp/root.[a]/usr/pkg/gcc16/lib -L/tmp/root.[a]/usr/lib
CONFIG_ARGS='--with-openssl=/tmp/root.[a]/usr'
other=/tmp/root.[a]-other/usr
DATA
cat > "$work/expected" <<'DATA'
LDFLAGS=-L/usr/pkg/gcc16/lib -L/usr/lib
CONFIG_ARGS='--with-openssl=/tmp/root.[a]/usr'
other=/tmp/root.[a]-other/usr
DATA
awk -v 'sysroot=/tmp/root.[a]' -f "$filter" "$work/input" > "$work/actual"
cmp "$work/expected" "$work/actual"
for invalid in '' /; do
    if awk -v "sysroot=$invalid" -f "$filter" "$work/input" > "$work/invalid-root"; then
        echo 'Invalid sysroot unexpectedly accepted' >&2; exit 1
    fi
done
echo 'PASS: host interpreter guards, upstream version rejection, native selection and literal target paths'
