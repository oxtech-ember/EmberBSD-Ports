#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; ordinary pkgtools with an isolated root and real dependency records.
set -eu
[ "$#" = 3 ] || { echo 'Usage: package.sh BUNDLE NEW_DESTROOT NEW_PACKAGE_OUTPUT' >&2; exit 2; }
: "${PKG_CREATE:?Select absolute native pkg_create}"
: "${PKG_ADD:?Select absolute native pkg_add}"
: "${SHA256:?Select absolute sha256 with -q support}"
: "${PKGTOOLS_VERSION:?Pin the native pkgtools version}"
: "${PKG_CREATE_SHA256:?Pin the native pkg_create SHA256}"
bundle=$1 destroot=$2 packages=$3
for path in "$bundle" "$destroot" "$packages" "$PKG_CREATE" "$PKG_ADD" "$SHA256"; do
  case "$path" in /*) ;; *) echo 'Absolute paths required' >&2; exit 2;; esac
done
[ "$("$PKG_CREATE" -V)" = "$PKGTOOLS_VERSION" ]
[ "$("$PKG_ADD" -V)" = "$PKGTOOLS_VERSION" ]
[ "$("$SHA256" -q "$PKG_CREATE")" = "$PKG_CREATE_SHA256" ]
for path in "$destroot" "$packages"; do
  [ "$path" != / ] && [ ! -e "$path" ] && [ ! -L "$path" ] || { echo "Refusing existing path: $path" >&2; exit 2; }
done
mkdir "$destroot" "$packages"
cp -R "$bundle/base-root/." "$destroot/"
# pkg_add/delete prepend -P to their logical -K path; pkg_create has no -P.
logical_db=/var/db/pkg
physical_db=$destroot$logical_db
mkdir -p "$physical_db"
while IFS= read -r name; do
  case "$name" in ''|*[!A-Za-z0-9+_.-]*) echo 'Invalid package order entry' >&2; exit 2;; esac
  d=$bundle/$name
  [ "$(sed -n 's/^@name //p' "$d/PLIST")" = "$name" ]
  info=$packages/$name.BUILD_INFO
  [ ! -e "$info" ] || { echo 'Duplicate package order entry' >&2; exit 2; }
  [ "$(sed -n 's/^PKGTOOLS_VERSION=//p' "$d/BUILD_INFO")" = "$PKGTOOLS_VERSION" ]
  if grep -q '^EMBERBSD_PKG_CREATE_SHA256=' "$d/BUILD_INFO"; then
    echo 'Build-info already contains packaging tool identity' >&2; exit 2
  fi
  cp "$d/BUILD_INFO" "$info"
  printf 'EMBERBSD_PKG_CREATE_SHA256=%s\n' "$PKG_CREATE_SHA256" >> "$info"
  deps=$(cat "$d/DEPENDENCIES")
  if [ -n "$deps" ]; then
    "$PKG_CREATE" -K "$physical_db" -u root -g wheel -p "$d/stage/usr/pkg" -I /usr/pkg -P "$deps" -c '-Common GCC16 SDR receiver closure' -d "$d/DESCR" -f "$d/PLIST" -B "$info" "$packages/$name.tgz"
  else
    "$PKG_CREATE" -K "$physical_db" -u root -g wheel -p "$d/stage/usr/pkg" -I /usr/pkg -c '-Common GCC16 SDR receiver closure' -d "$d/DESCR" -f "$d/PLIST" -B "$info" "$packages/$name.tgz"
  fi
  [ "$("$SHA256" -q "$PKG_CREATE")" = "$PKG_CREATE_SHA256" ]
  "$PKG_ADD" -P "$destroot" -K "$logical_db" "$packages/$name.tgz"
done < "$bundle/package-order.txt"
printf '%s\n' "Packages installed only in $destroot; physical pkgdb: $physical_db"
