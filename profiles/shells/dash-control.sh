#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD, AI-assisted single-shell control build.
set -eu
[ "$#" -ge 2 ] && [ "$#" -le 3 ] || { echo 'Usage: dash-control.sh NEW_WORK CURRENT_DEPENDENCY_PREFIX [patched|upstream]' >&2; exit 2; }
work=$1
deps=$2
ncurses=${NCURSES_PREFIX:-$deps}
variant=${3:-patched}
case "$variant" in patched|upstream) ;; *) exit 2 ;; esac
case "$work:$deps:$ncurses" in *[!a-zA-Z0-9_./:-]*) exit 2 ;; esac
case "$work" in /*) ;; *) exit 2 ;; esac
case "$deps" in /*) ;; *) exit 2 ;; esac
[ ! -e "$work" ] && [ ! -L "$work" ] || { echo 'Use a fresh output directory.' >&2; exit 2; }
: "${CC:?Select GCC16 in CC.}"
case "$("$CC" -dumpfullversion)" in 16.*) ;; *) exit 2 ;; esac
profile=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ports=$(CDPATH= cd -- "$profile/../.." && pwd)
case "$work/" in "$ports/"*) echo 'Keep outputs outside the checkout.' >&2; exit 2 ;; esac
[ -f "$deps/include/histedit.h" ]
[ -f "$deps/lib/libedit.so" ]
case "$("$ncurses/bin/ncursesw6-config" --version)" in 6.6|6.6.*) ;; *) exit 2 ;; esac
mkdir -p "$work/downloads" "$work/src" "$work/logs" "$work/records/dash"
archive=dash-0.5.13.6.tar.gz
digest=7cf031480d46e0dd45a42a7c951e482dc850ae63106dc39821350e133d9fe73e
curl --fail --location --proto '=https' --tlsv1.2 \
    "https://git.kernel.org/pub/scm/utils/dash/dash.git/snapshot/$archive" \
    -o "$work/downloads/$archive"
printf '%s  %s\n' "$digest" "$work/downloads/$archive" | sha256sum -c -
tar -xf "$work/downloads/$archive" -C "$work/src"
src=$work/src/dash-0.5.13.6
for name in patch-configure.ac patch-src_histedit.c; do
    patch -p0 -F0 -d "$src" < "$ports/upstream/pkgsrc/shells/dash/patches/$name" \
        >> "$work/logs/patches.log"
done
if [ "$variant" = patched ]; then
    for name in patch-src_parser.c patch-src_trap.c patch-eval-const; do
        patch -p0 -F0 -d "$src" < "$ports/pkgsrc/shells/dash/patches/$name" >> "$work/logs/patches.log"
    done
fi
export SHELL_REAL_CC="$CC" SHELL_CC_RECORDS="$work/records/dash"
export LD_LIBRARY_PATH="$deps/lib:$ncurses/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export PKG_CONFIG_PATH="$deps/lib/pkgconfig:$ncurses/lib/pkgconfig"
cd "$src"
autoreconf -fi > "$work/logs/autoreconf.log" 2>&1
CC="$profile/record-cc.pl" CFLAGS='-O2 -g' \
    CPPFLAGS="-I$deps/include -I$ncurses/include -I$ncurses/include/ncursesw" \
    LDFLAGS="-L$deps/lib -L$ncurses/lib -Wl,-rpath,$deps/lib -Wl,-rpath,$ncurses/lib" \
    ./configure --prefix="$work/prefix" --with-libedit > "$work/logs/configure.log" 2>&1
! grep -q '^#define SMALL ' config.h
grep -q '^LIBS = .* -ledit' src/Makefile
make -j1 > "$work/logs/build.log" 2>&1
make check > "$work/logs/upstream-check.log" 2>&1
make install > "$work/logs/install.log" 2>&1
perl "$profile/compilation-database.pl" "$work"
"$work/prefix/bin/dash" "$profile/backquote-contract.sh" > "$work/logs/backquotes.log"
SHELL_TEST_TMP=$(mktemp -d "$work/posix.XXXXXXXX")
export SHELL_TEST_TMP
"$work/prefix/bin/dash" "$profile/posix-contract.sh" > "$work/logs/posix.log"
{
    "$CC" --version
    autoreconf --version
    perl -V:version
    pkg-config --modversion libedit ncursesw
    ldd "$work/prefix/bin/dash"
} > "$work/logs/providers.txt"
sha256sum "$work/prefix/bin/dash" > "$work/logs/binaries.sha256"
echo 'PASS: dash with current libedit, GCC16 and shell contracts.'
