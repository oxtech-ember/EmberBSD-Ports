#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Qtbase full-stage runtime/devel handoff.
set -eu
case "${TMPDIR:-/tmp}" in /*) ;; *) echo 'TMPDIR must be absolute' >&2; exit 2 ;; esac
base=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd -P)
selector=$base/select-package-stage.pl
testroot=$(mktemp -d "$TMPDIR/qtbase-shared-stage.XXXXXX")
trap 'rm -rf "$testroot"' EXIT HUP INT TERM

# Exercise only the pure path check: never pass root to the selector itself.
perl - "$selector" "$testroot" <<'PERL'
use strict;
use warnings;
use Cwd qw(abs_path);
use File::Basename qw(dirname basename);
use File::Spec;
my ($selector, $directory) = @ARGV;
open my $in, '<', $selector or die $!;
local $/;
my $source = <$in>;
my ($functions) = $source =~ /(sub reject_overlap \{.*?\n\}\n\nsub canonical_target \{.*?\n\})/s
    or die "path checks not found\n";
eval $functions;
die $@ if $@;
for my $root ('/', '/.', '//') {
    eval { reject_overlap($directory, $root) };
    die "root accepted: $root\n" unless $@ =~ /overlap/;
}
eval { reject_overlap("$directory/child", $directory) };
die "ancestor accepted\n" unless $@ =~ /overlap/;
PERL

mkdir -p "$testroot/stage/lib" "$testroot/stage/include/QtCore" "$testroot/stage/share"
printf 'runtime\n' > "$testroot/stage/lib/libQtCore.so.6.12"
ln -s libQtCore.so.6.12 "$testroot/stage/lib/libQtCore.so.6"
printf 'header\n' > "$testroot/stage/include/QtCore/QtCore"
chmod 0755 "$testroot/stage/lib/libQtCore.so.6.12"
printf 'full\n' > "$testroot/full"
printf 'lib/libQtCore.so.6.12\nlib/libQtCore.so.6\ninclude/QtCore/QtCore\n' > "$testroot/full"
printf 'lib/libQtCore.so.6.12\nlib/libQtCore.so.6\n' > "$testroot/runtime"
printf 'include/QtCore/QtCore\n' > "$testroot/devel"
cp "$testroot/runtime" "$testroot/selected-runtime"
cp "$testroot/devel" "$testroot/selected-devel"
mkdir -p "$testroot/wrk"

perl "$selector" handoff-runtime "$testroot/stage" "$testroot/full" \
    "$testroot/runtime" "$testroot/devel" "$testroot/selected-runtime" \
    "$testroot/wrk/.qtbase-shared-full-stage"
[ -f "$testroot/wrk/.qtbase-shared-full-stage/include/QtCore/QtCore" ] || exit 1
[ -f "$testroot/stage/lib/libQtCore.so.6.12" ] || exit 1
[ -L "$testroot/stage/lib/libQtCore.so.6" ] || exit 1
[ "$(perl -e 'printf "%o", (stat shift)[2] & 07777' "$testroot/stage/lib/libQtCore.so.6.12")" = 755 ] || exit 1

mkdir -p "$testroot/devel-dest"
perl "$selector" copy-devel "$testroot/wrk/.qtbase-shared-full-stage" \
    "$testroot/devel-dest" "$testroot/full" "$testroot/runtime" \
    "$testroot/devel" "$testroot/selected-devel"
[ -f "$testroot/devel-dest/include/QtCore/QtCore" ] || exit 1
[ ! -e "$testroot/devel-dest/lib/libQtCore.so.6.12" ] || exit 1
[ -f "$testroot/wrk/.qtbase-shared-full-stage/lib/libQtCore.so.6.12" ] || exit 1

# Reinstall with the same manifest must retain the new bytes.
mkdir -p "$testroot/stage/include/QtCore" "$testroot/stage/lib"
printf 'runtime same manifest\n' > "$testroot/stage/lib/libQtCore.so.6.12"
printf 'header same manifest\n' > "$testroot/stage/include/QtCore/QtCore"
perl "$selector" handoff-runtime "$testroot/stage" "$testroot/full" \
    "$testroot/runtime" "$testroot/devel" "$testroot/selected-runtime" \
    "$testroot/wrk/.qtbase-shared-full-stage"
[ "$(cat "$testroot/stage/lib/libQtCore.so.6.12")" = 'runtime same manifest' ] || exit 1
mkdir -p "$testroot/devel-same"
perl "$selector" copy-devel "$testroot/wrk/.qtbase-shared-full-stage" \
    "$testroot/devel-same" "$testroot/full" "$testroot/runtime" \
    "$testroot/devel" "$testroot/selected-devel"
[ "$(cat "$testroot/devel-same/include/QtCore/QtCore")" = 'header same manifest' ] || exit 1

# Reinstall replaces the retained stage even when the manifest changes.
mkdir -p "$testroot/stage/include/QtCore" "$testroot/stage/lib"
printf 'runtime reinstall\n' > "$testroot/stage/lib/libQtCore.so.6.12"
printf 'header reinstall\n' > "$testroot/stage/include/QtCore/NewHeader"
printf 'lib/libQtCore.so.6.12\nlib/libQtCore.so.6\ninclude/QtCore/NewHeader\n' > "$testroot/full"
printf 'include/QtCore/NewHeader\n' > "$testroot/devel"
cp "$testroot/devel" "$testroot/selected-devel"
perl "$selector" handoff-runtime "$testroot/stage" "$testroot/full" \
    "$testroot/runtime" "$testroot/devel" "$testroot/selected-runtime" \
    "$testroot/wrk/.qtbase-shared-full-stage"
[ "$(cat "$testroot/stage/lib/libQtCore.so.6.12")" = 'runtime reinstall' ] || exit 1
[ -L "$testroot/stage/lib/libQtCore.so.6" ] || exit 1
[ "$(readlink "$testroot/stage/lib/libQtCore.so.6")" = libQtCore.so.6.12 ] || exit 1
[ "$(perl -e 'printf "%o", (stat shift)[2] & 07777' "$testroot/stage/lib/libQtCore.so.6.12")" = 755 ] || exit 1
mkdir -p "$testroot/devel-reinstall"
perl "$selector" copy-devel "$testroot/wrk/.qtbase-shared-full-stage" \
    "$testroot/devel-reinstall" "$testroot/full" "$testroot/runtime" \
    "$testroot/devel" "$testroot/selected-devel"
[ "$(cat "$testroot/devel-reinstall/include/QtCore/NewHeader")" = 'header reinstall' ] || exit 1
[ ! -e "$testroot/devel-reinstall/include/QtCore/QtCore" ] || exit 1
[ ! -e "$testroot/wrk/.qtbase-shared-full-stage/include/QtCore/QtCore" ] || exit 1

printf 'unknown\n' > "$testroot/wrong-selected"
if perl "$selector" copy-devel "$testroot/wrk/.qtbase-shared-full-stage" \
    "$testroot/wrong-dest" "$testroot/full" "$testroot/runtime" \
    "$testroot/devel" "$testroot/wrong-selected" >/dev/null 2>&1; then
    echo 'FAIL: mismatched devel manifest accepted' >&2
    exit 1
fi
echo 'PASS: Qtbase complete stage retained, runtime/devel partitions copied independently, modes and symlinks preserved'
