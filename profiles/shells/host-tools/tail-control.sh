#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD, AI-assisted host-provider regression and control build.
# This builds only the test host's tail. It is not a coreutils port recipe.
set -eu
umask 022
[ "$#" -eq 1 ] || { echo 'Usage: tail-control.sh ABSOLUTE_NEW_WORK' >&2; exit 2; }
work=$1
case "$work" in /*) ;; *) echo 'Use an absolute work directory.' >&2; exit 2 ;; esac
case "$work" in *[!a-zA-Z0-9_./-]*) echo 'Use a path without shell metacharacters.' >&2; exit 2 ;; esac
work=$(realpath -m "$work")
[ ! -e "$work" ] && [ ! -L "$work" ] || { echo 'Use a fresh work directory.' >&2; exit 2; }
host_tools=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
profile=$(CDPATH= cd -- "$host_tools/.." && pwd)
ports=$(CDPATH= cd -- "$profile/../.." && pwd)
case "$work/" in "$ports/"*) echo 'Keep outputs outside the checkout.' >&2; exit 2 ;; esac
[ "$(uname -s)" = Linux ] || { echo 'This control requires Linux.' >&2; exit 2; }
: "${CC:?Select GCC16 in CC.}"
case "$("$CC" -dumpfullversion)" in 16.*) ;; *) echo 'GCC16 is required.' >&2; exit 2 ;; esac
CLANG=${CLANG:-clang}
export CLANG
for tool in curl sha256sum tar patch make install valgrind cppcheck perl timeout; do command -v "$tool" >/dev/null; done
[ "$(cppcheck --version)" = 'Cppcheck 2.22.0' ]
[ "$(valgrind --version)" = 'valgrind-3.27.1' ]
case "$("$CLANG" --version)" in *'clang version 23.1.3'*) ;; *) echo 'Clang 23.1.3 is required.' >&2; exit 2 ;; esac
export LC_ALL=C
mkdir -p "$work/downloads" "$work/tmp"
export TMPDIR="$work/tmp"
{
    uname -a
    "$CC" --version
    "$CLANG" --version
    cppcheck --version
    valgrind --version
    printf 'CC=%s\nCLANG=%s\n' "$CC" "$CLANG"
} > "$work/providers.txt"
archive=coreutils-9.12.tar.xz
digest=a480198559733e9b3da999e90543ac6f888a2caa544d8d664c5a1f17e528e210
curl --fail --location --retry 2 --proto '=https' --tlsv1.2 \
    "https://ftp.gnu.org/gnu/coreutils/$archive" -o "$work/downloads/$archive"
printf '%s  %s\n' "$digest" "$work/downloads/$archive" | sha256sum -c -
sha256sum "$work/downloads/$archive" "$host_tools/patch-tail-exit.c" > "$work/inputs.sha256"
failed=0
run_tail() {
    if [ "$scenario" = stdin ]; then
        printf 'one\ntwo\n' | "$@"
    else
        "$@" < "$build/input-a"
    fi
}
printf '# variant\tcase\tplain_status\tmemcheck_status\texpected_memcheck_status\n' > "$work/results.tsv"
for variant in upstream patched; do
    build=$work/$variant
    mkdir -p "$build/src" "$build/logs" "$build/records/tail" "$build/prefix/bin"
    tar -xJf "$work/downloads/$archive" -C "$build/src"
    src=$build/src/coreutils-9.12
    if [ "$variant" = patched ]; then
        patch -p0 -F0 -d "$src" < "$host_tools/patch-tail-exit.c" > "$build/logs/patch.log"
    fi
    # Retain default features. Generate all upstream prerequisites before tail.
    (
        set -x
        cd "$src"
        CC="$CC" CFLAGS='-O2 -g' ./configure --prefix="$build/prefix"
        make -j1 -f Makefile -f - current-tail <<'MAKE'
.PHONY: current-tail
current-tail: $(BUILT_SOURCES)
	$(MAKE) src/tail
MAKE
        # Record the actual tail compilation, without unrelated gnulib objects.
        rm src/tail.o
        export SHELL_REAL_CC="$CC" SHELL_CC_RECORDS="$build/records/tail"
        make -j1 V=1 CC="$profile/record-cc.pl" src/tail.o
        make -j1 V=1 src/tail
        install -m 755 src/tail "$build/prefix/bin/tail"
    ) > "$build/logs/build.log" 2>&1
    perl "$profile/compilation-database.pl" "$build"
    "$build/prefix/bin/tail" --version > "$build/logs/version.txt"
    sha256sum "$build/prefix/bin/tail" > "$build/logs/binary.sha256"
    printf 'one\ntwo\n' > "$build/input-a"
    printf 'three\nfour\n' > "$build/input-b"
    for scenario in stdin file multifile zero-lines missing; do
        expected_status=0
        expected_bytes=104
        case "$scenario" in
            stdin) set -- -n 1; printf 'two\n' > "$build/expected" ;;
            file) set -- -n 1 "$build/input-a"; printf 'two\n' > "$build/expected" ;;
            multifile) set -- -q -n 1 "$build/input-a" "$build/input-b"
                printf 'two\nfour\n' > "$build/expected"; expected_bytes=208 ;;
            zero-lines) set -- -n 0; : > "$build/expected"; expected_bytes=0 ;;
            missing) set -- -n 1 "$build/no-such-file"
                : > "$build/expected"; expected_status=1 ;;
        esac
        status=0
        cp "$build/expected" "$build/logs/$scenario.expected"
        run_tail "$build/prefix/bin/tail" "$@" \
            > "$build/logs/$scenario.stdout" 2> "$build/logs/$scenario.stderr" || status=$?
        plain_status=$status
        [ "$status" -eq "$expected_status" ] || failed=1
        cmp "$build/expected" "$build/logs/$scenario.stdout" || failed=1
        if [ "$scenario" = missing ]; then
            grep -F "cannot open '$build/no-such-file' for reading: No such file or directory" \
                "$build/logs/$scenario.stderr" >/dev/null || failed=1
        else
            [ ! -s "$build/logs/$scenario.stderr" ] || failed=1
        fi
        status=0
        run_tail valgrind --tool=memcheck --leak-check=full --show-leak-kinds=all \
            --errors-for-leak-kinds=definite,indirect,possible --track-origins=yes \
            --error-exitcode=97 --log-file="$build/logs/$scenario.memcheck.log" \
            "$build/prefix/bin/tail" "$@" \
            > "$build/logs/$scenario.memcheck.stdout" 2> "$build/logs/$scenario.memcheck.stderr" || status=$?
        cmp "$build/expected" "$build/logs/$scenario.memcheck.stdout" || failed=1
        cmp "$build/logs/$scenario.stderr" "$build/logs/$scenario.memcheck.stderr" || failed=1
        expected_memory=$expected_status
        if [ "$variant" = upstream ] && [ "$expected_bytes" -ne 0 ]; then
            expected_memory=97
            grep -F "$expected_bytes bytes in 1 blocks are definitely lost" \
                "$build/logs/$scenario.memcheck.log" >/dev/null || failed=1
            grep -F 'ERROR SUMMARY: 1 errors from 1 contexts' \
                "$build/logs/$scenario.memcheck.log" >/dev/null || failed=1
        else
            awk '/ERROR SUMMARY:/ { seen=1; if ($0 !~ /ERROR SUMMARY: 0 errors from 0 contexts/) bad=1 }
                END { exit (!seen || bad) }' "$build/logs/$scenario.memcheck.log" || failed=1
        fi
        [ "$status" -eq "$expected_memory" ] || failed=1
        printf '%s\t%s\t%s\t%s\t%s\n' "$variant" "$scenario" "$plain_status" "$status" "$expected_memory" >> "$work/results.tsv"
    done
    # Preserve findings and status. Findings are reviewed, not suppressed.
    status=0
    sh "$profile/analyze.sh" "$build" tail > "$build/logs/analysis.log" 2>&1 || status=$?
    printf '%s\n' "$status" > "$build/logs/analysis.status"
    [ -s "$build/analysis/tail/cppcheck.xml" ] && \
        [ "$(cat "$build/analysis/tail/cppcheck.status")" -le 1 ] || failed=1
    if grep -E 'id="(syntaxError|internalError|unknownMacro)"' "$build/analysis/tail/cppcheck.xml"; then
        failed=1
    fi
    for analyzer in gcc clang; do
        awk 'NR > 1 { seen=1; if ($2 != 0) bad=1 } END { exit (!seen || bad) }' \
            "$build/analysis/tail/$analyzer/status.tsv" || failed=1
    done
done
cat "$work/results.tsv"
if [ "$failed" -ne 0 ]; then
    echo "FAIL: inspect $work for raw diagnostics." >&2
    exit 1
fi
printf 'PASS: original exit-allocation failures and patched normal-exit checks.\nProvider: %s\n' "$work/patched/prefix/bin/tail"
