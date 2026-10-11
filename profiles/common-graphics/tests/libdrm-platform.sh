#!/bin/sh
# Origin: EmberBSD; AI-assisted production libdrm discovery contracts.
# SPDX-License-Identifier: BSD-2-Clause
set -eu
[ "$#" -eq 1 ] || { echo 'Usage: native-identity.sh PATCHED_LIBDRM_SOURCE' >&2; exit 2; }
source=$1
recipe=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
work=$(mktemp -d "${TMPDIR:-/tmp}/libdrm-identity.XXXXXXXX")
trap 'rm -rf "$work"' EXIT HUP INT TERM
sed -e 's/@ATOMIC_OPS_CHECK@/0/g' -e 's/^#if 1$/#if 0/' -e 's/^#if 1 /#if 0 /' "$source/xf86drm.h" > "$work/xf86drm.h"
cp "$recipe/libdrm-platform-fixture.c" "$work/test.c"
extract() {
    awk -v name="$1" -v type="$2" '
        /^[^ \t#]/ && $0 ~ (name "[(]") && $0 !~ /;[[:space:]]*$/ {
            print type; copying=1;
            sub(/^(static |drm_public )?(const char \*|char \*|unsigned |int |void |bool |drmDevicePtr )/, "");
        }
        copying { print }
        copying && /^}/ { exit }
    ' "$source/xf86drm.c" >> "$work/test.c"
}
extract drmGetDeviceName 'static const char *'
extract drmNativeIdentity 'static int'
extract drmNativePlatformIdentity 'static int'
extract drmNativeNodeIdentity 'static int'
extract drmNativeNodeName 'static char *'
extract drmGetMinorType 'static int'
extract drmNodeIsDRM 'static bool'
extract drmGetNodeTypeFromFd 'int'
extract drmGetMinorNameForFD 'static char *'
extract drmGetRenderDeviceNameFromFd 'char *'
extract drmParseSubsystemType 'static int'
extract drmDevicesEqual 'int'
extract drmGetNodeType 'static int'
extract drmGetMaxNodeName 'static int'
extract drmFreePlatformDevice 'static void'
extract drmFreeHost1xDevice 'static void'
extract drmFreeDevice 'void'
extract drmFreeDevices 'void'
extract drmDeviceAlloc 'static drmDevicePtr'
extract drmProcessPciDevice 'static int'
extract drmParseOFBusInfo 'static int'
extract drmParseOFDeviceInfo 'static int'
extract drmProcessPlatformDevice 'static int'
extract process_device 'static int'
extract log2_int 'static unsigned'
extract drmFoldDuplicatedDevices 'static void'
extract drm_device_validate_flags 'static int'
extract drm_device_has_rdev 'static bool'
extract drmGetDeviceFromDevId 'int'
extract drmGetDevice2 'int'
extract drmGetDevices2 'int'
cat "$recipe/libdrm-platform-main.c" >> "$work/test.c"
${CC:-cc} -std=c11 -D_DEFAULT_SOURCE -D_DARWIN_C_SOURCE -Wall -Wextra -Werror \
    -Wno-sign-compare -I"$work" -I"$source" -I"$source/include/drm" \
    ${SANITIZERS:+-fsanitize=address,undefined -fno-sanitize-recover=all} "$work/test.c" -o "$work/test"
"$work/test"
