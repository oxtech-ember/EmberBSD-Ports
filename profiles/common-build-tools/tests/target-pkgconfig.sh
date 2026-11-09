#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Fixture regression: staged target .pc files
# lose the build sysroot (selected spelling and real path) from -I, -L and
# -isystem flags, and a .pc file that still names a build directory fails.
#
# With PKGSRC and MAKECONF of a cross build, it also checks that the cross
# install runs the step after post-install and a native install does not.
set -eu
[ "$#" = 1 ] || [ "$#" = 3 ] || {
    echo 'Usage: target-pkgconfig.sh NEW_WORK [PKGSRC CROSS_MAKECONF]' >&2
    exit 2
}
root=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)
script=$root/profiles/common-build-tools/cross/target-pkgconfig.sh
mkdir "$1"
work=$(CDPATH= cd -- "$1" && pwd -P)
fail() { echo "FAIL: $*" >&2; exit 1; }
mkdir -p "$work/real-sysroot/usr/pkg/include" "$work/context" "$work/obj/work/.buildlink/lib" "$work/tools"
ln -s "$work/real-sysroot" "$work/context/sysroot"
sysroot=$work/context/sysroot real=$work/real-sysroot
wrk=$work/obj/work tools=$work/tools

stage() {
    rm -rf "$work/stage"
    mkdir -p "$work/stage/usr/pkg/lib/pkgconfig" "$work/stage/usr/pkg/share/pkgconfig" \
        "$work/stage/usr/pkg/share/doc"
    dest=$work/stage
}
stage
cat > "$dest/usr/pkg/lib/pkgconfig/libqalculate.pc" <<PC
prefix=/usr/pkg
includedir=\${prefix}/include
libdir=\${prefix}/lib
Libs.private: -Wl,-R/usr/pkg/lib -L$sysroot/usr/pkg/lib -lcurl -L$real/usr/pkg/lib -licuuc
Libs: -L\${libdir} -lqalculate
Cflags: -I$sysroot/usr/pkg/include -I$real/usr/include -isystem $sysroot/usr/pkg/include/x -I\${includedir}
PC
chmod 444 "$dest/usr/pkg/lib/pkgconfig/libqalculate.pc"
cat > "$dest/usr/pkg/share/pkgconfig/clean.pc" <<'PC'
prefix=/usr/pkg
Cflags: -I${prefix}/include
PC
# Not a pkg-config file: left alone.
printf 'see %s/usr/pkg/include\n' "$sysroot" > "$dest/usr/pkg/share/doc/notes.pc"
cp "$dest/usr/pkg/share/pkgconfig/clean.pc" "$work/clean.expected"
cp "$dest/usr/pkg/share/doc/notes.pc" "$work/notes.expected"

sh "$script" "$dest" "$sysroot" "$wrk" "$tools" > "$work/run1.log" 2>&1 ||
    fail "a rooted .pc file is refused: $(cat "$work/run1.log")"
pc=$dest/usr/pkg/lib/pkgconfig/libqalculate.pc
cat > "$work/qalc.expected" <<'PC'
prefix=/usr/pkg
includedir=${prefix}/include
libdir=${prefix}/lib
Libs.private: -Wl,-R/usr/pkg/lib -L/usr/pkg/lib -lcurl -L/usr/pkg/lib -licuuc
Libs: -L${libdir} -lqalculate
Cflags: -I/usr/pkg/include -I/usr/include -isystem /usr/pkg/include/x -I${includedir}
PC
cmp -s "$pc" "$work/qalc.expected" || { diff "$work/qalc.expected" "$pc" >&2 || :; fail 'sysroot flags were not rewritten to target paths'; }
[ ! -w "$pc" ] || fail 'the staged file mode changed'
cmp -s "$dest/usr/pkg/share/pkgconfig/clean.pc" "$work/clean.expected" || fail 'a clean .pc file changed'
cmp -s "$dest/usr/pkg/share/doc/notes.pc" "$work/notes.expected" || fail 'a file outside pkgconfig changed'
grep -q 'removed the build sysroot from /usr/pkg/lib/pkgconfig/libqalculate.pc' "$work/run1.log" ||
    fail 'the rewrite is not reported'
cp "$pc" "$work/qalc.once"
sh "$script" "$dest" "$sysroot" "$wrk" "$tools" > "$work/run2.log" 2>&1 || fail 'a second run fails'
cmp -s "$pc" "$work/qalc.once" || fail 'the rewrite is not idempotent'
[ ! -s "$work/run2.log" ] || fail 'a second run reports changes'

# Build directories that are not -I/-L/-isystem flags stay and are refused.
for case in buildlink tools sysroot-var; do
    stage
    case $case in
    buildlink) line="Libs.private: $wrk/.buildlink/lib/libpcre2-8.so" ; want=$wrk ;;
    tools) line="host_tool=$tools/bin/aarch64--netbsd-pkg-config" ; want=$tools ;;
    sysroot-var) line="sysroot=$sysroot" ; want=$sysroot ;;
    esac
    printf 'prefix=/usr/pkg\n%s\n' "$line" > "$dest/usr/pkg/lib/pkgconfig/bad.pc"
    if sh "$script" "$dest" "$sysroot" "$wrk" "$tools" > "$work/$case.log" 2>&1; then
        fail "a .pc file naming the $case directory is accepted"
    fi
    grep -Fq "names build directory $want" "$work/$case.log" || fail "the $case rejection does not name $want"
done
! sh "$script" "$dest" relative > /dev/null 2>&1 || fail 'a relative sysroot is accepted'
sh "$script" "$work/missing" "$sysroot" || fail 'a package without a stage fails'

if [ "$#" = 3 ]; then
    : "${BMAKE:?Set the native bmake executable}"
    pkgsrc=$2 conf=$3
    recipe=$pkgsrc/devel/readline
    bm() { "$BMAKE" -C "$recipe" MAKECONF="$conf" WRKOBJDIR="$work/wrk" "$@"; }
    bm -n install-doc-handling > "$work/cross-install.log" 2>&1 || fail 'make -n install-doc-handling failed'
    grep -q 'target-pkgconfig.sh' "$work/cross-install.log" || fail 'a cross install does not check its pkg-config files'
    [ -f "$pkgsrc/target-pkgconfig.sh" ] || fail 'the export does not provide target-pkgconfig.sh'
    bm -n USE_CROSS_COMPILE=no install-doc-handling > "$work/native-install.log" 2>&1 ||
        fail 'native make -n install-doc-handling failed'
    ! grep -q 'target-pkgconfig.sh' "$work/native-install.log" || fail 'a native install runs the target check'
fi
echo 'PASS: staged target .pc files name target paths and refuse build directories'
