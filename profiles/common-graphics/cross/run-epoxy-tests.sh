#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), installed libepoxy/Mesa consumer checks.
set -eu
verify=no
renderer=${3:-llvmpipe}
if [ "$#" = 3 ] && [ "$1" = --verify-sysroot ]; then
    verify=yes
    shift
elif [ "$#" != 2 ] && [ "$#" != 3 ]; then
    echo 'Usage: run-epoxy-tests.sh BUNDLE NEW_LOG_DIRECTORY [EXPECTED_RENDERER]' >&2
    echo '       run-epoxy-tests.sh --verify-sysroot BUNDLE SYSROOT' >&2
    exit 2
fi
bundle=$(CDPATH= cd -- "$1" && pwd -P)
hash() {
    if command -v sha256 >/dev/null 2>&1; then sha256 -q "$1"
    else shasum -a 256 "$1" | awk '{print $1}'; fi
}
[ -s "$bundle/artifacts.sha256" ]
while read -r expected artifact; do
    case "$artifact" in ''|/*|..|../*|*/..|*/../*) exit 1;; esac
    [ "${#expected}" = 64 ] && [ "$(hash "$bundle/$artifact")" = "$expected" ] || {
        echo "Bundle drift: $artifact" >&2; exit 1;
    }
done < "$bundle/artifacts.sha256"
root=
if [ "$verify" = yes ]; then root=$(CDPATH= cd -- "$2" && pwd -P); fi
for manifest in installed-files.sha256 runtime-libraries.sha256; do
    [ -s "$bundle/$manifest" ]
    while read -r expected installed; do
        case "$installed" in */../*|*/..) exit 1;; /usr/pkg/*) ;; *) exit 1;; esac
        [ "$(hash "$root$installed")" = "$expected" ] || { echo "Installed drift: $installed" >&2; exit 1; }
    done < "$bundle/$manifest"
done
[ -s "$bundle/installed-links.tsv" ]
while IFS="$(printf '\t')" read -r installed link; do
    case "$installed" in */../*|*/..) exit 1;; /usr/pkg/*) ;; *) exit 1;; esac
    [ -L "$root$installed" ] && [ "$(readlink "$root$installed")" = "$link" ] || {
        echo "Installed link drift: $installed" >&2; exit 1;
    }
done < "$bundle/installed-links.tsv"
if [ "$verify" = yes ]; then
    echo 'PASS: complete bundle and installed Mesa/libepoxy files, links and runtime hashes; no target execution'
    exit 0
fi
[ "$(uname -s)" = NetBSD ] && [ "$(uname -p)" = aarch64 ]
for setting in LD_LIBRARY_PATH LD_PRELOAD LIBGL_DRIVERS_PATH GBM_BACKENDS_PATH MESA_LOADER_DRIVER_OVERRIDE LIBGL_ALWAYS_SOFTWARE GALLIUM_DRIVER; do
    eval "value=\${$setting-}"
    [ -z "$value" ] || { echo "Runtime override is not permitted: $setting" >&2; exit 2; }
done
mkdir "$2"
logs=$(CDPATH= cd -- "$2" && pwd -P)
timeout=${TIMEOUT:-/usr/bin/timeout}
case "$timeout" in /*) ;; *) exit 2;; esac
[ -x "$timeout" ]
uname -a > "$logs/platform.log"
recorded_library() {
    loaded_path=$1
    case "$loaded_path" in
        /usr/pkg/*)
            loaded_path=$(CDPATH= cd -- "$(dirname -- "$loaded_path")" && printf '%s/%s' "$(pwd -P)" "$(basename -- "$loaded_path")")
            awk -v path="$loaded_path" '$2 == path { found=1 } END { exit !found }' "$bundle/runtime-libraries.sha256" || {
                echo "Unrecorded package library: $loaded_path" >&2; exit 1;
            };;
        /usr/lib/*|/lib/*|/libexec/ld.elf_so|/usr/libexec/ld.elf_so) ;;
        *) echo "Foreign library: $loaded_path" >&2; exit 1;;
    esac
}
for executable in epoxy-render header_guards misc_defines khronos_typedefs gl_version; do
    ldd "$bundle/bin/$executable" > "$logs/$executable.ldd.log" 2>&1
    awk '$2 == "=>" && $3 !~ /^\// {bad=1} END {exit bad}' "$logs/$executable.ldd.log"
    while read -r dependency; do recorded_library "$dependency"; done <<EOF
$(awk '$2 == "=>" {print $3}' "$logs/$executable.ldd.log")
EOF
done
env -i PATH=/bin:/usr/bin:/sbin:/usr/sbin:/usr/pkg/bin MESA_SHADER_CACHE_DISABLE=true "$timeout" -k 5 60 \
    "$bundle/bin/epoxy-render" surfaceless "$renderer" > "$logs/epoxy-render.log" 2>&1
while read -r dependency; do recorded_library "$dependency"; done <<EOF
$(sed -n 's/^LOADED: //p' "$logs/epoxy-render.log")
EOF
for provider in libepoxy libEGL libGLESv2 libgallium libLLVM; do
    grep "^LOADED: /usr/pkg/lib/$provider" "$logs/epoxy-render.log" > /dev/null || {
        echo "Missing live provider: $provider" >&2; exit 1;
    }
done
echo "PASS: real libepoxy dispatch, canonical live providers and four $renderer EGL/GLES lifecycles"
while IFS="$(printf '\t')" read -r executable limit; do
    case "$executable" in header_guards|misc_defines|khronos_typedefs|gl_version) ;; *) exit 1;; esac
    env -i PATH=/bin:/usr/bin:/sbin:/usr/sbin:/usr/pkg/bin "$timeout" -k 5 "$limit" \
        "$bundle/bin/$executable" > "$logs/$executable.log" 2>&1
    echo "PASS: upstream $executable"
done < "$bundle/tests.tsv"
echo 'PASS: installed libepoxy rendering consumer and four pure upstream tests; no display-session claim'
