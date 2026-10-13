#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Installed helper acceptance in a private HOME.
set -eu
[ "$#" -eq 1 ] || { echo "Usage: $0 ABSOLUTE_NEW_OUTPUT" >&2; exit 2; }
case "$1" in /*) ;; *) echo 'Use an absolute output path.' >&2; exit 2 ;; esac
[ ! -e "$1" ] && [ ! -L "$1" ] || { echo 'Output already exists.' >&2; exit 2; }
umask 077
mkdir "$1"
work=$(CDPATH= cd -- "$1" && pwd)
mkdir "$work/home" "$work/config" "$work/defaults"
cp /usr/pkg/share/examples/xdg/user-dirs.conf \
    /usr/pkg/share/examples/xdg/user-dirs.defaults "$work/defaults/"
/usr/bin/sha256 /usr/pkg/bin/xdg-user-dir /usr/pkg/bin/xdg-user-dirs-update > "$work/binaries.sha256"
/usr/bin/env -i HOME="$work/home" XDG_CONFIG_HOME="$work/config" \
    XDG_CONFIG_DIRS="$work/defaults" PATH=/usr/pkg/bin:/usr/bin:/bin LC_ALL=C \
    /bin/sh -eu > "$work/runtime.log" 2>&1 <<'TEST'
xdg-user-dirs-update --force
test "$(xdg-user-dir PROJECTS)" = "$HOME/Projects"
test "$(xdg-user-dir DOWNLOAD)" = "$HOME/Downloads"
test -d "$HOME/Projects"
test -d "$HOME/Downloads"
mkdir "$HOME/Project space"
xdg-user-dirs-update --set PROJECTS "$HOME/Project space"
test "$(xdg-user-dir PROJECTS)" = "$HOME/Project space"
xdg-user-dirs-update
test "$(xdg-user-dir PROJECTS)" = "$HOME/Project space"
cp "$XDG_CONFIG_HOME/user-dirs.dirs" "$XDG_CONFIG_HOME/before-invalid"
if xdg-user-dirs-update --set '' "$HOME/invalid"; then exit 1; fi
cmp "$XDG_CONFIG_HOME/before-invalid" "$XDG_CONFIG_HOME/user-dirs.dirs"
if xdg-user-dirs-update --set PROJECTS relative; then exit 1; fi
cmp "$XDG_CONFIG_HOME/before-invalid" "$XDG_CONFIG_HOME/user-dirs.dirs"
echo 'PASS: defaults, spaces, repeat update and invalid-input preservation'
TEST
cat "$work/runtime.log"
echo 'PASS: installed xdg-user-dirs in a private HOME; no allocation-failure or full desktop acceptance'
