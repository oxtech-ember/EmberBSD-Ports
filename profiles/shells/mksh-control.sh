#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD, AI-assisted single-shell control build.
set -eu
umask 022
[ "$#" -ge 1 ] && [ "$#" -le 2 ] || {
    echo 'Usage: mksh-control.sh ABSOLUTE_NEW_WORK [patched|upstream]' >&2
    exit 2
}
work=$1
variant=${2:-patched}
case "$variant" in patched|upstream) ;; *) exit 2 ;; esac
case "$work" in /*) ;; *) echo 'Use an absolute work directory.' >&2; exit 2 ;; esac
case "$work" in *[!a-zA-Z0-9_./-]*) echo 'Use a path without shell metacharacters.' >&2; exit 2 ;; esac
work=$(realpath -m "$work")
[ ! -e "$work" ] && [ ! -L "$work" ] || { echo 'Use a fresh work directory.' >&2; exit 2; }
profile=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ports=$(CDPATH= cd -- "$profile/../.." && pwd)
case "$work/" in "$ports/"*) echo 'Keep outputs outside the checkout.' >&2; exit 2 ;; esac
[ "$(uname -s)" = Linux ] || { echo 'This control requires the Linux script PTY interface.' >&2; exit 2; }
: "${CC:?Select GCC16 in CC.}"
case "$("$CC" -dumpfullversion)" in 16.*) ;; *) echo 'GCC 16 is required.' >&2; exit 2 ;; esac
PERL=$(command -v "${PERL:-perl}")
FCEDIT=$(command -v "${FCEDIT:-ed}")
export PERL FCEDIT
[ "$("$PERL" -e 'print $^V')" = v5.44.0 ] || { echo 'Perl 5.44.0 is required.' >&2; exit 2; }
case "$("$FCEDIT" --version)" in 'GNU ed 1.22.6'*) ;; *) echo 'GNU ed 1.22.6 is required.' >&2; exit 2 ;; esac
for tool in curl sha256sum tar patch script install valgrind pkg-config tail; do command -v "$tool" >/dev/null; done
[ "$(pkg-config --modversion valgrind)" = 3.27.1 ] || { echo 'Valgrind 3.27.1 headers are required.' >&2; exit 2; }
case "$(tail --version)" in 'tail (GNU coreutils) 9.12'*) ;; *) echo 'GNU tail 9.12 is required.' >&2; exit 2 ;; esac
mkdir -p "$work/downloads" "$work/src" "$work/logs" "$work/records/mksh" "$work/tmp"
prefix=$work/prefix
stage=$work/stage$prefix
export LC_ALL=C
export TMPDIR="$work/tmp"
{
    uname -a
    "$CC" --version
    "$PERL" -V:version
    "$FCEDIT" --version
    script --version
    valgrind --version
    tail --version
    printf 'tail=%s\n' "$(command -v tail)"
    printf 'Valgrind client header flags: %s\n' "$(pkg-config --cflags valgrind)"
    printf 'variant=%s\nPERL=%s\nFCEDIT=%s\n' "$variant" "$PERL" "$FCEDIT"
    echo 'Upstream categories: stdout-ed,no-stderr-ed (GNU ed byte counts on stdout)'
} > "$work/logs/providers.txt"
"$PERL" -MText::ParseWords=shellwords - "$CC" <<'PERL' > "$work/logs/valgrind-headers.log" 2>&1
use strict;
use warnings;
open my $pc, '-|', 'pkg-config', '--cflags', 'valgrind' or die $!;
my $flags = do { local $/; <$pc> };
close $pc or die "pkg-config failed\n";
system($ARGV[0], shellwords($flags), '-x', 'c', '-fsyntax-only',
    '-include', 'memcheck.h', '/dev/null') == 0 or die "Valgrind headers failed: $?\n";
PERL

# Prove that script supplies a controlling PTY and preserves command failure.
status=0
SHELL=/bin/sh script -q -e -c 'test -t 0 && test -t 1 && test -t 2 && : </dev/tty && exit 37' \
    "$work/logs/pty-probe.log" > "$work/logs/pty-probe.stdout" 2>&1 || status=$?
printf '%s\n' "$status" > "$work/logs/pty-probe.status"
[ "$status" -eq 37 ] || { echo 'PTY or exit-status propagation failed.' >&2; exit 1; }
printf 'x\n' > "$work/ed-probe.txt"
printf 'w\nq\n' | "$FCEDIT" "$work/ed-probe.txt" \
    > "$work/logs/ed-probe.stdout" 2> "$work/logs/ed-probe.stderr"
printf '2\n2\n' > "$work/logs/ed-probe.expected"
cmp "$work/logs/ed-probe.expected" "$work/logs/ed-probe.stdout"
[ ! -s "$work/logs/ed-probe.stderr" ]

archive=mksh-R59c.tgz
digest=77ae1665a337f1c48c61d6b961db3e52119b38e58884d1c89684af31f87bc506
# This upstream mirror carries the same tarball as the primary MirBSD server.
curl --fail --location --retry 2 --proto '=https' --tlsv1.2 \
    "https://mbsd.evolvis.org/MirOS/dist/mir/mksh/$archive" \
    -o "$work/downloads/$archive"
printf '%s  %s\n' "$digest" "$work/downloads/$archive" | sha256sum -c -
tar -xzf "$work/downloads/$archive" -C "$work/src"
src=$work/src/mksh
if [ "$variant" = patched ]; then
    for patchfile in "$ports"/pkgsrc/local-shells/mksh/patches/*; do
        patch -p0 -F0 -d "$src" < "$patchfile" >> "$work/logs/patches.log"
    done
fi
export SHELL_REAL_CC="$CC" SHELL_CC_RECORDS="$work/records/mksh"
cd "$src"
CC="$profile/record-cc.pl" CFLAGS='-O2 -g' sh Build.sh -r > "$work/logs/build.log" 2>&1
"$PERL" "$profile/compilation-database.pl" "$work"

install_payload() {
    install -d "$1/bin" "$1/man/man1" "$1/share/examples/mksh"
    install -m 755 "$src/mksh" "$1/bin/mksh"
    install -m 644 "$src/mksh.1" "$1/man/man1/mksh.1"
    install -m 644 "$src/dot.mkshrc" "$1/share/examples/mksh/dot.mkshrc"
}
install_payload "$stage"
(cd "$stage" && find . -type f | sed 's|^./||' | LC_ALL=C sort) > "$work/logs/stage-files.txt"
sed '/^@comment /d; /^$/d' "$ports/pkgsrc/local-shells/mksh/PLIST" | LC_ALL=C sort > "$work/logs/plist-files.txt"
cmp "$work/logs/plist-files.txt" "$work/logs/stage-files.txt"
install_payload "$prefix"
for file in bin/mksh man/man1/mksh.1 share/examples/mksh/dot.mkshrc; do
    cmp "$stage/$file" "$prefix/$file"
done
failed=0
check_memcheck_log() {
    awk '/ERROR SUMMARY:/ {
        seen = 1
        if ($0 !~ /ERROR SUMMARY: 0 errors from 0 contexts/) bad = 1
    } END { exit (!seen || bad) }' "$1"
}
status=0
SHELL=/bin/sh script -q -e -c './mksh ./test.sh -v -e FCEDIT -C stdout-ed,no-stderr-ed' \
    "$work/logs/upstream-pty.log" > "$work/logs/upstream-pty.stdout" 2>&1 || status=$?
printf '%s\n' "$status" > "$work/logs/upstream.status"
[ "$status" -eq 0 ] || failed=1
tr -d '\r' < "$work/logs/upstream-pty.log" > "$work/logs/upstream.txt"
awk '/^FAIL / || /^Total / { print }' "$work/logs/upstream.txt" > "$work/logs/upstream-summary.txt"
awk '/^FAIL .*\(ignored\)/ { print }' "$work/logs/upstream.txt" > "$work/logs/upstream-ignored.txt"

for contract in posix backquote; do
    SHELL_TEST_TMP=$(mktemp -d "$work/$contract.XXXXXXXX")
    export SHELL_TEST_TMP
    status=0
    "$prefix/bin/mksh" "$profile/$contract-contract.sh" > "$work/logs/$contract.log" 2>&1 || status=$?
    printf '%s\n' "$status" > "$work/logs/$contract.status"
    [ "$status" -eq 0 ] || failed=1
    SHELL_TEST_TMP=$(mktemp -d "$work/memcheck-$contract.XXXXXXXX")
    export SHELL_TEST_TMP
    status=0
    valgrind --tool=memcheck --trace-children=yes --leak-check=full --show-leak-kinds=all \
        --errors-for-leak-kinds=definite,indirect,possible --track-origins=yes \
        --error-exitcode=97 --log-file="$work/logs/memcheck-$contract.%p.log" \
        "$prefix/bin/mksh" "$profile/$contract-contract.sh" \
        > "$work/logs/memcheck-$contract.stdout" 2>&1 || status=$?
    printf '%s\n' "$status" > "$work/logs/memcheck-$contract.status"
    [ "$status" -eq 0 ] || failed=1
    # Forked shell errors can be consumed by command substitution. Inspect
    # every child summary as well as the top-level process exit status.
    for memory_log in "$work/logs/memcheck-$contract."*.log; do
        [ -f "$memory_log" ] && check_memcheck_log "$memory_log" || failed=1
    done
done

# Link the causal regressions with the actual shell objects and their flags.
"$PERL" -MJSON::PP -MFile::Basename=basename -MText::ParseWords=shellwords - "$work" "$profile" <<'PERL' > "$work/logs/regression-build.log" 2>&1
use strict;
use warnings;
my ($work, $profile) = @ARGV;
open my $input, '<', "$work/records/mksh/compile_commands.json" or die $!;
my $entries = do { local $/; decode_json(<$input>) };
open my $pc, '-|', 'pkg-config', '--cflags', 'valgrind' or die $!;
my $includes = do { local $/; <$pc> };
close $pc or die "pkg-config failed\n";
my @valgrind = shellwords($includes);
my @objects = map { my $name = basename($_->{file}); $name =~ s/\.c$/.o/; $name } @$entries;
for my $name (qw(allocation arithmetic)) {
    my $source = $name eq 'allocation' ? 'lalloc.c' : 'expr.c';
    my ($entry) = grep { basename($_->{file}) eq $source } @$entries;
    die "No production flags for $source\n" unless $entry;
    my (@command, @original);
    @original = @{$entry->{arguments}};
    while (@original) {
        my $arg = shift @original;
        if ($arg eq '-o') { shift @original; next; }
        next if $arg eq '-c' || $arg eq $source || $arg eq $entry->{file};
        push @command, $arg;
    }
    chdir $entry->{directory} or die $!;
    my @links = $name eq 'allocation' ? ('lalloc.o', '-Wl,--wrap=realloc', '-Wl,--wrap=free')
        : (@objects, '-Wl,--wrap=evaluate');
    system(@command, '-I.', @valgrind, "$profile/mksh-$name.c", @links,
        '-o', "$work/mksh-$name") == 0 or die "$name compilation failed: $?\n";
}
PERL
for regression in allocation arithmetic; do
    status=0
    if [ "$regression" = arithmetic ]; then
        set -- -c 'let "("; test $? -eq 2 || exit 1; let "1/0"; test $? -eq 2 || exit 1; let "1+"; test $? -eq 2 || exit 1; let "answer=3+4"; test "$answer" -eq 7 || exit 1; let 0; test $? -eq 1'
    else
        set --
    fi
    valgrind --tool=memcheck --leak-check=full --show-leak-kinds=all \
        --errors-for-leak-kinds=definite,indirect,possible --track-origins=yes \
        --error-exitcode=97 --log-file="$work/logs/$regression-memcheck.log" \
        "$work/mksh-$regression" "$@" > "$work/logs/$regression.log" 2>&1 || status=$?
    printf '%s\n' "$status" > "$work/logs/$regression.status"
    if [ "$variant" = upstream ]; then
        [ "$status" -eq 97 ] || failed=1
    else
        [ "$status" -eq 0 ] && check_memcheck_log "$work/logs/$regression-memcheck.log" || failed=1
        if [ "$regression" = arithmetic ]; then
            [ "$(grep -c '^PASS evaluate preserved the result after an error$' "$work/logs/arithmetic.log")" -eq 3 ] || failed=1
        fi
    fi
done

sha256sum "$prefix/bin/mksh" > "$work/logs/binary-before.sha256"
rm "$prefix/bin/mksh" "$prefix/man/man1/mksh.1" "$prefix/share/examples/mksh/dot.mkshrc"
find "$prefix" \( -type f -o -type l \) > "$work/logs/uninstall-residuals.txt"
[ ! -s "$work/logs/uninstall-residuals.txt" ]
install_payload "$prefix"
sha256sum "$prefix/bin/mksh" > "$work/logs/binary-after.sha256"
cmp "$work/logs/binary-before.sha256" "$work/logs/binary-after.sha256"
"$prefix/bin/mksh" "$profile/backquote-contract.sh" > "$work/logs/reinstalled.log" 2>&1
"$prefix/bin/mksh" -c 'print -r -- "$KSH_VERSION"' > "$work/logs/version.txt"
if [ "$failed" -ne 0 ]; then
    echo "FAIL: mksh control; inspect $work/logs" >&2
    exit 1
fi
if [ "$variant" = upstream ]; then
    echo 'PASS: upstream build/contracts; both causal regressions report the expected Memcheck failure.'
else
    echo 'PASS: patched mksh control build, staged lifecycle, PTY suite and memory regressions.'
fi
cat "$work/logs/upstream-summary.txt"
