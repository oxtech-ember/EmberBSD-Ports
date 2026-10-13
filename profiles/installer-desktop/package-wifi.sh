#!/bin/sh
# Origin: EmberBSD native GTK3 Wi-Fi package recipe, prepared with AI assistance.
# SPDX-License-Identifier: BSD-2-Clause
set -eu
[ "$#" = 2 ] || { echo 'Usage: package-wifi.sh cross-build-output new-package.tgz' >&2; exit 2; }
build=$1; package=$2
[ "$(uname -s)" = NetBSD ] || { echo 'Run pkg_create on EmberBSD/NetBSD amd64.' >&2; exit 1; }
[ "$(uname -m)" = amd64 ] && [ ! -e "$package" ] || exit 1
[ -x "$build/install/usr/pkg/bin/dhcpcd-gtk" ] || exit 1
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT HUP INT TERM
mkdir -p "$work/usr/pkg"
cp -R "$build/install/usr/pkg/." "$work/usr/pkg/"
mkdir -p "$work/usr/pkg/share/licenses/dhcpcd-gtk3"
# Include every original source license header, including the embedded library.
find "$build/dhcpcd-ui-0.8.0" -type f \( -name '*.c' -o -name '*.h' \) | sort | while IFS= read -r file; do
	printf '\n%s\n' "${file##*/}"
	sed -n '1,/^ \*\//p' "$file"
done > "$work/usr/pkg/share/licenses/dhcpcd-gtk3/COPYRIGHT"
cat > "$work/PLIST" <<'PLIST'
@name dhcpcd-gtk3-0.8.0
@pkgdep gtk3+>=3.24.52nb3
@pkgdep libnotify>=0.8.4nb7
@pkgdep dhcpcd-icons>=0.8.0
bin/dhcpcd-gtk
etc/xdg/autostart/dhcpcd-gtk.desktop
share/licenses/dhcpcd-gtk3/COPYRIGHT
share/man/man8/dhcpcd-gtk.8
PLIST
cat > "$work/BUILD_INFO" <<'INFO'
OPSYS=NetBSD
OS_VERSION=11.0
MACHINE_ARCH=x86_64
PKGPATH=net/dhcpcd-gtk3
LICENSE=modified-bsd
DHCPCD_UI_VERSION=0.8.0
GTK_VERSION=3.24.52nb3
CC_VERSION=gcc-12.5.0
INFO
printf '%s\n' 'GTK3 network and Wi-Fi manager for EmberBSD' > "$work/COMMENT"
printf '%s\n' 'Original dhcpcd-ui 0.8.0 using GTK3 and the base dhcpcd/wpa_supplicant services.' > "$work/DESCR"
pkg_create -u root -g wheel -p "$work/usr/pkg" -I /usr/pkg \
    -B "$work/BUILD_INFO" -c "$work/COMMENT" -d "$work/DESCR" \
    -f "$work/PLIST" "$package"
pkg_info -X "$package"
