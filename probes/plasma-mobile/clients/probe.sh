#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors. AI-assisted portability probe.
set -eu
[ "$(id -u)" -ne 0 ] || { echo 'Run as an ordinary user.' >&2; exit 1; }
[ "$#" -le 1 ] || { echo 'Usage: sh probe.sh [archive-directory]' >&2; exit 2; }
: "${PLASMA_PREFIX:?Set PLASMA_PREFIX to the current shared Plasma installation}"
: "${MM_PREFIX:?Set MM_PREFIX to the existing real ModemManager client prefix}"
export PATH=/usr/pkg/qt6/bin:/usr/pkg/bin:/usr/bin:/bin
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
archives=${1:-}
case ${JOBS:-1} in 1|2) ;; *) echo 'JOBS must be 1 or 2.' >&2; exit 2 ;; esac
mkdir -p "$HOME/.cache"
if [ -n "${WORK_DIR:-}" ]; then
    case "$WORK_DIR" in /*) ;; *) echo 'WORK_DIR must be absolute.' >&2; exit 2 ;; esac
    mkdir "$WORK_DIR"
    work=$WORK_DIR
else
    work=$(mktemp -d "$HOME/.cache/emberbsd-plasma-support.XXXXXXXX")
fi
export WORK=$work
mkdir "$work/downloads" "$work/src" "$work/logs"
echo "Build directory: $work"
fetch() {
    name=$1 digest=$2 url=$3
    if [ -n "$archives" ]; then
        cp "$archives/$name" "$work/downloads/$name"
    else
        curl -fL --retry 2 -o "$work/downloads/$name" "$url"
    fi
    actual=$(sha256 -q "$work/downloads/$name")
    [ "$actual" = "$digest" ] || { echo "SHA256 mismatch: $name" >&2; exit 1; }
    tar -xf "$work/downloads/$name" -C "$work/src"
}
fetch modemmanager-qt-6.26.0.tar.xz \
    bef456ac0a5983bcc14a1580cb0d32a001241f380d901cb503613855380af3a5 \
    https://download.kde.org/stable/frameworks/6.26/modemmanager-qt-6.26.0.tar.xz
fetch networkmanager-qt-6.26.0.tar.xz \
    a5cfed06af6156161f7fee56efe1521a6e9e26119327069f1799986f90b432e5 \
    https://download.kde.org/stable/frameworks/6.26/networkmanager-qt-6.26.0.tar.xz
fetch NetworkManager-1.54.3.tar.gz \
    16c1e954a8598a0afc71c9936a7e4f0ad949522438d96fec63aa1abb6f2207fe \
    https://gitlab.freedesktop.org/NetworkManager/NetworkManager/-/archive/1.54.3/NetworkManager-1.54.3.tar.gz
fetch bluez-qt-6.26.0.tar.xz \
    ebeb301eaeb6ec6729b27969556839165ba582ebe242b42cde71c8faa80d63df \
    https://download.kde.org/stable/frameworks/6.26/bluez-qt-6.26.0.tar.xz
fetch qtkeychain-0.17.0.tar.gz \
    3b85c3929034b0a99da777130c34d99f006fcd3a9d56564159399a33fee0e504 \
    https://github.com/frankosterfeld/qtkeychain/archive/refs/tags/0.17.0.tar.gz
fetch mobile-broadband-provider-info-20251101.tar.bz2 \
    6fa60b5e9860a648d7c5b8e4e3f87d6ce6a7622b8a7b5f2d567a9a0d9dddb9f7 \
    https://gitlab.gnome.org/GNOME/mobile-broadband-provider-info/-/archive/20251101/mobile-broadband-provider-info-20251101.tar.bz2
fetch plasma-nm-6.7.5.tar.xz \
    6469ff89e26d44565292c968df595b3a68f353707255ba48725c1bae2a67f3be \
    https://download.kde.org/stable/plasma/6.7.5/plasma-nm-6.7.5.tar.xz
(cd "$work/src/modemmanager-qt-6.26.0" && patch -p1 < "$script_dir/patches/modemmanager-qt-prefix-includes.patch")
(cd "$work/src/networkmanager-qt-6.26.0" && patch -p1 < "$script_dir/patches/networkmanager-qt-headers-only.patch")
(cd "$work/src/networkmanager-qt-6.26.0" && patch -p1 < "$script_dir/patches/networkmanager-qt-clock.patch")
/bin/sh "$script_dir/install-networkmanager-headers.sh" "$work/src/NetworkManager-1.54.3" "$work/prefix"
/bin/sh "$script_dir/build-mmqt.sh"
/bin/sh "$script_dir/build-nmqt.sh"
/bin/sh "$script_dir/build-qtkeychain.sh"
# This pinned diagnostic cohort shares its four affected source files with
# the current Frameworks release. Apply the common recipe's patches.
for patchfile in "$script_dir"/../../../pkgsrc/net/kf6-bluez-qt/patches/patch-*; do
    (cd "$work/src/bluez-qt-6.26.0" && patch -F 0 -p0 < "$patchfile")
done
/bin/sh "$script_dir/build-bluezqt.sh"
(cd "$work/src/plasma-nm-6.7.5" && patch -p1 < "$script_dir/patches/plasma-nm-dbus-client-only.patch")
(cd "$work/src/plasma-nm-6.7.5" && patch -p1 < "$script_dir/patches/plasma-nm-provider-data-20251101.patch")
/bin/sh "$script_dir/build-provider-info.sh"
/bin/sh "$script_dir/build-plasma-nm.sh"
mkdir -p "$work/prefix/share/licenses/modemmanager-qt" "$work/prefix/share/licenses/networkmanager-qt"
cp -R "$work/src/modemmanager-qt-6.26.0/LICENSES/." "$work/prefix/share/licenses/modemmanager-qt/"
cp -R "$work/src/networkmanager-qt-6.26.0/LICENSES/." "$work/prefix/share/licenses/networkmanager-qt/"
for project in bluez-qt-6.26.0 plasma-nm-6.7.5; do
    mkdir -p "$work/prefix/share/licenses/$project"
    cp -R "$work/src/$project/LICENSES/." "$work/prefix/share/licenses/$project/"
done
mkdir -p "$work/prefix/share/licenses/qtkeychain"
cp "$work/src/qtkeychain-0.17.0/COPYING" "$work/prefix/share/licenses/qtkeychain/"
/bin/sh "$script_dir/verify-client.sh"
echo "Installed client libraries: $work/prefix"
