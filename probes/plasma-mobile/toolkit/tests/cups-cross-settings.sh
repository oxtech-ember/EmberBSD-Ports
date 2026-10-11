#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Check the actual macOS-to-EmberBSD CUPS build.
set -eu
[ "$#" = 3 ] || { echo "Usage: $0 CONFIGURED_CUPS_SOURCE SYSROOT CROSS_READELF" >&2; exit 2; }
source=$1 sysroot=$2 readelf=$3
# The regression needs a Mac with GSS.framework and the fork's base Heimdal.
[ -d /System/Library/Frameworks/GSS.framework ]
grep -q "^build_os='darwin" "$source/config.log"
grep -q "^host_os='netbsd" "$source/config.log"
grep -Fx "KRB5CONFIG='$sysroot/usr/bin/krb5-config'" "$source/config.log"
grep -qx '#define HAVE_GSSAPI 1' "$source/config.h"
grep -qx '#define HAVE_GSSAPI_GSSAPI_H 1' "$source/config.h"
if grep -q '^#define HAVE_GSS_GSSAPI_H 1' "$source/config.h" ||
    grep -E '^(LIBGSSAPI|LIBS|DSOFLAGS|LDFLAGS).*search_paths_first|^(LIBGSSAPI|LIBS|DSOFLAGS|LDFLAGS).*framework' "$source/Makedefs"; then
    echo 'Host GSS framework selection leaked into the target build' >&2; exit 1
fi
"$readelf" -h "$source/cups/libcups.so.2" | grep 'Machine:.*AArch64'
echo 'PASS: actual CUPS target GSS headers, sysroot provider and ELF shared library'
