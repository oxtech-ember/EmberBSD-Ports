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
printf 'QT_FEATURE_xdg_desktop_portal_file_transfer:INTERNAL=OFF\n' > "$testroot/cache-off"

perl "$selector" handoff-runtime "$testroot/stage" "$testroot/full" \
    "$testroot/runtime" "$testroot/devel" "$testroot/selected-runtime" \
    "$testroot/wrk/.qtbase-shared-full-stage" "$testroot/cache-off"
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
    "$testroot/wrk/.qtbase-shared-full-stage" "$testroot/cache-off"
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
    "$testroot/wrk/.qtbase-shared-full-stage" "$testroot/cache-off"
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
marker="$testroot/wrk/.qtbase-shared-full-stage.features"
printf 'OFF\nextra\n' > "$marker"
if perl "$selector" copy-devel "$testroot/wrk/.qtbase-shared-full-stage" \
    "$testroot/invalid-marker-dest" "$testroot/full" "$testroot/runtime" \
    "$testroot/devel" "$testroot/selected-devel" >/dev/null 2>&1; then
    echo 'FAIL: trailing shared-stage feature marker data accepted' >&2
    exit 1
fi
printf 'OFF\n' > "$marker"

# The portal transfer header is listed statically under DBus + Wayland, but
# only exists when Qt's generated feature is ON. OFF removes that one row from
# all package partitions; ON requires the real staged header.
mkdir -p "$testroot/portal-off-stage/qt6/lib" "$testroot/portal-on-stage/qt6/lib" \
    "$testroot/portal-on-stage/qt6/include/QtGui/6.12.0/QtGui/private"
printf 'runtime\n' > "$testroot/portal-off-stage/qt6/lib/libQtCore.so.6.12"
printf 'runtime\n' > "$testroot/portal-on-stage/qt6/lib/libQtCore.so.6.12"
printf 'portal header\n' > "$testroot/portal-on-stage/qt6/include/QtGui/6.12.0/QtGui/private/qxdgdesktopportalfiletransfer_p.h"
printf 'qt6/lib/libQtCore.so.6.12\nqt6/include/QtGui/6.12.0/QtGui/private/qxdgdesktopportalfiletransfer_p.h\n' > "$testroot/portal-full"
printf 'qt6/lib/libQtCore.so.6.12\n' > "$testroot/portal-runtime"
printf 'qt6/include/QtGui/6.12.0/QtGui/private/qxdgdesktopportalfiletransfer_p.h\n' > "$testroot/portal-devel"
cp "$testroot/portal-devel" "$testroot/portal-selected"
perl "$selector" devel "$testroot/portal-off-stage" "$testroot/portal-full" \
    "$testroot/portal-runtime" "$testroot/portal-devel" "$testroot/portal-selected" "$testroot/cache-off"
[ ! -e "$testroot/portal-off-stage/qt6/include/QtGui/6.12.0/QtGui/private/qxdgdesktopportalfiletransfer_p.h" ] || exit 1
if grep -q 'qxdgdesktopportalfiletransfer_p.h' "$testroot/portal-selected"; then
    echo 'FAIL: disabled Qt portal feature remained in selected PLIST' >&2
    exit 1
fi
mkdir -p "$testroot/portal-off-bad-stage/qt6/lib" \
    "$testroot/portal-off-bad-stage/qt6/include/QtGui/6.12.0/QtGui/private"
printf 'runtime\n' > "$testroot/portal-off-bad-stage/qt6/lib/libQtCore.so.6.12"
printf 'unexpected portal header\n' > "$testroot/portal-off-bad-stage/qt6/include/QtGui/6.12.0/QtGui/private/qxdgdesktopportalfiletransfer_p.h"
cp "$testroot/portal-devel" "$testroot/portal-selected-bad"
cp "$testroot/portal-selected-bad" "$testroot/portal-selected-before"
if perl "$selector" devel "$testroot/portal-off-bad-stage" "$testroot/portal-full" \
    "$testroot/portal-runtime" "$testroot/portal-devel" "$testroot/portal-selected-bad" "$testroot/cache-off" \
    2>"$testroot/portal-disabled-unexpected"; then
    echo 'FAIL: disabled Qt portal feature accepted an unexpected staged header' >&2
    exit 1
fi
grep -q 'unlisted staged file: qt6/include/QtGui/6.12.0/QtGui/private/qxdgdesktopportalfiletransfer_p.h' \
    "$testroot/portal-disabled-unexpected" || exit 1
cmp "$testroot/portal-selected-before" "$testroot/portal-selected-bad"
printf 'QT_FEATURE_xdg_desktop_portal_file_transfer:INTERNAL=ON\n' > "$testroot/cache-on"
cp "$testroot/portal-devel" "$testroot/portal-selected-on"
perl "$selector" devel "$testroot/portal-on-stage" "$testroot/portal-full" \
    "$testroot/portal-runtime" "$testroot/portal-devel" "$testroot/portal-selected-on" "$testroot/cache-on"
[ -f "$testroot/portal-on-stage/qt6/include/QtGui/6.12.0/QtGui/private/qxdgdesktopportalfiletransfer_p.h" ] || exit 1
grep -q 'qxdgdesktopportalfiletransfer_p.h' "$testroot/portal-selected-on" || exit 1
rm "$testroot/portal-on-stage/qt6/include/QtGui/6.12.0/QtGui/private/qxdgdesktopportalfiletransfer_p.h"
mkdir -p "$testroot/portal-on-stage/qt6/lib"
printf 'runtime\n' > "$testroot/portal-on-stage/qt6/lib/libQtCore.so.6.12"
if perl "$selector" devel "$testroot/portal-on-stage" "$testroot/portal-full" \
    "$testroot/portal-runtime" "$testroot/portal-devel" "$testroot/portal-selected-on" "$testroot/cache-on" \
    2>"$testroot/portal-enabled-missing"; then
    echo 'FAIL: enabled Qt portal feature accepted a missing header' >&2
    exit 1
fi
grep -q 'missing complete-stage file: qt6/include/QtGui/6.12.0/QtGui/private/qxdgdesktopportalfiletransfer_p.h' \
    "$testroot/portal-enabled-missing" || exit 1
echo 'PASS: Qtbase complete stage retained, runtime/devel partitions copied independently, modes and symlinks preserved'
