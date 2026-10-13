#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted). Run only the installed ICD.
set -eu
[ "$#" = 2 ] || { echo 'Usage: run-powervr-enumeration.sh RENDER_NODE NEW_LOG_DIRECTORY' >&2; exit 2; }
[ "$(uname -s)" = NetBSD ] && [ "$(uname -p)" = aarch64 ] || {
    echo 'Run on EmberBSD/AArch64 with the native PowerVR render node.' >&2; exit 2;
}
[ "${PVR_I_WANT_A_BROKEN_VULKAN_DRIVER:-}" = 1 ] || {
    echo 'Set the upstream experimental PowerVR opt-in explicitly for this diagnostic.' >&2; exit 2;
}
pkg_info=$(command -v pkg_info) || { echo 'pkg_info is required.' >&2; exit 2; }
[ -x "$pkg_info" ] || exit 2
runner=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
manifest=/usr/pkg/share/vulkan/icd.d/powervr_mesa_icd.json
[ -f "$manifest" ] && [ -x "$runner/powervr-enumerate" ]
mkdir "$2"
logs=$(CDPATH= cd -- "$2" && pwd)
"$pkg_info" -e 'MesaLib-26.2.4nb[56]' > "$logs/mesa-package.txt"
"$pkg_info" -e 'libdrm-2.4.134nb2' > "$logs/libdrm-package.txt"
uname -a > "$logs/kernel.txt"
cp "$manifest" "$logs/icd.json"
unset LD_LIBRARY_PATH LD_PRELOAD VK_ICD_FILENAMES VK_ADD_DRIVER_FILES VK_ADDITIONAL_DRIVER_FILES
ldd "$runner/powervr-enumerate" > "$logs/loader.txt"
ldd /usr/pkg/lib/libvulkan_powervr_mesa.so > "$logs/icd-libraries.txt"
export VK_DRIVER_FILES="$manifest" VK_LOADER_DEBUG=error,warn,driver
/usr/bin/timeout 60 "$runner/powervr-enumerate" "$1" > "$logs/enumeration.stdout" 2> "$logs/enumeration.stderr"
cat "$logs/enumeration.stdout"
