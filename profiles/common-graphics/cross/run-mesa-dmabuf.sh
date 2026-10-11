#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), real DRM/PRIME transfer preflight.
set -eu
recorded_library() {
    loaded_path=$1
    case "$loaded_path" in
        /usr/pkg/*)
            if awk -v p="$loaded_path" '$2 == p {found=1} END {exit !found}' "$bundle/runtime-libraries.sha256"; then
                return 0
            fi
            # Mesa may spell a provider as dri/../libgallium-VERSION.so.
            if [ -d "$(dirname -- "$loaded_path")" ]; then
                loaded_path=$(CDPATH= cd -- "$(dirname -- "$loaded_path")" && printf '%s/%s' "$(pwd -P)" "$(basename -- "$loaded_path")") || return 1
            fi
            awk -v p="$loaded_path" '$2 == p {found=1} END {exit !found}' "$bundle/runtime-libraries.sha256" || {
                echo "Unrecorded package library: $loaded_path" >&2; return 1;
            };;
        /usr/lib/*|/lib/*|/libexec/ld.elf_so|/usr/libexec/ld.elf_so) ;;
        *) echo "Foreign runtime library: $loaded_path" >&2; return 1;;
    esac
}
check_live_providers() {
    while IFS= read -r live_library; do
        recorded_library "$live_library" || return 1
    done <<EOF
$(sed -n 's/^LOADED: //p' "$logs/dmabuf.log")
EOF
    for provider in libEGL libGLESv2 libgbm libgallium libLLVM; do
        grep "^LOADED: /usr/pkg/lib/$provider" "$logs/dmabuf.log" > /dev/null || {
            echo "Missing live provider: $provider" >&2; return 1;
        }
    done
    echo 'PASS: all live package providers are in the verified runtime manifest'
}
# End of provider checks; functions are exercised by dmabuf-providers.rb.
[ "$#" = 3 ] || [ "$#" = 4 ] || { echo 'Usage: run-mesa-dmabuf.sh BUNDLE /dev/dri/DEVICE NEW_LOGS [V3D|llvmpipe]' >&2; exit 2; }
bundle=$(CDPATH= cd -- "$1" && pwd -P)
device=$2
renderer=${4:-llvmpipe}
case "$device" in /dev/dri/*) ;; *) exit 2;; esac
# Reuse the accepted complete file/link/runtime verifier, not its render policy.
sh "$bundle/run-mesa-package-tests.sh" --verify-sysroot "$bundle" /
[ "$(uname -s)" = NetBSD ] && [ "$(uname -p)" = aarch64 ]
[ -c "$device" ] || { echo "FAIL: no real DRM character device: $device" >&2; exit 1; }
for setting in LD_LIBRARY_PATH LD_PRELOAD LIBGL_DRIVERS_PATH GBM_BACKENDS_PATH \
    MESA_LOADER_DRIVER_OVERRIDE LIBGL_ALWAYS_SOFTWARE GALLIUM_DRIVER; do
    eval "value=\${$setting-}"
    [ -z "$value" ] || { echo "Unexpected caller override: $setting" >&2; exit 2; }
done
mkdir "$3"
logs=$(CDPATH= cd -- "$3" && pwd -P)
timeout=${TIMEOUT:-/usr/bin/timeout}
case "$timeout" in /*) ;; *) exit 2;; esac
[ -x "$timeout" ]
uname -a > "$logs/platform.log"
ldd "$bundle/bin/mesa-dmabuf" > "$logs/ldd.log" 2>&1
awk '$2 == "=>" && $3 !~ /^\// {bad=1} END {exit bad}' "$logs/ldd.log"
while read -r library; do
    recorded_library "$library"
done <<EOF
$(awk '$2 == "=>" {print $3}' "$logs/ldd.log")
EOF
result=0
case "$renderer" in llvmpipe) set -- LIBGL_ALWAYS_SOFTWARE=1;; V3D) set --;; *) exit 2;; esac
env -i PATH=/bin:/usr/bin:/sbin:/usr/sbin:/usr/pkg/bin MESA_SHADER_CACHE_DISABLE=true \
    "$@" "$timeout" -k 5 60 "$bundle/bin/mesa-dmabuf" "$device" "$renderer" \
    > "$logs/dmabuf.log" 2>&1 || result=$?
cat "$logs/dmabuf.log"
if [ "$result" = 0 ]; then
    check_live_providers > "$logs/live-providers.log" 2>&1 || result=$?
    cat "$logs/live-providers.log"
fi
printf '%s\n' "$result" > "$logs/exit-status"
exit "$result"
