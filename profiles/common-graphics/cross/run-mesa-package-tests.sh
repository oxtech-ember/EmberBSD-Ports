#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), installed canonical Mesa acceptance.
set -eu
verify_only=no
verify_sysroot=no
if [ "$#" = 2 ] && [ "$1" = --verify-only ]; then
    verify_only=yes
    shift
elif [ "$#" = 3 ] && [ "$1" = --verify-sysroot ]; then
    verify_sysroot=yes
    shift
elif [ "$#" -lt 2 ] || [ "$#" -gt 3 ]; then
    echo 'Usage: run-mesa-package-tests.sh BUNDLE NEW_LOG_DIRECTORY [EXPECTED_RENDERER]' >&2
    echo '       run-mesa-package-tests.sh --verify-only BUNDLE' >&2
    echo '       run-mesa-package-tests.sh --verify-sysroot BUNDLE SYSROOT' >&2
    exit 2
fi
bundle=$(CDPATH= cd -- "$1" && pwd -P)
hash() {
    if command -v sha256 >/dev/null 2>&1; then sha256 -q "$1"
    else shasum -a 256 "$1" | awk '{print $1}'; fi
}
[ -s "$bundle/artifacts.sha256" ]
while read -r expected file; do
    case "$file" in ''|/*|..|../*|*/..|*/../*) echo 'Invalid bundle path' >&2; exit 1;; esac
    [ "${#expected}" = 64 ] && [ -f "$bundle/$file" ] && \
        [ "$(hash "$bundle/$file")" = "$expected" ] || {
        echo "Bundle hash mismatch: $file" >&2; exit 1;
    }
done < "$bundle/artifacts.sha256"
if [ "$verify_only" = yes ]; then
    echo 'PASS: bundle artifact hashes only; no target runtime was executed'
    exit 0
fi
check_installed() {
    root=$1
    for manifest in mesa-package-files.sha256 runtime-libraries.sha256; do
        [ -s "$bundle/$manifest" ]
        while read -r expected file; do
            case "$file" in
                */../*|*/..) echo 'Invalid installed path' >&2; exit 1;;
                /usr/pkg/*) ;;
                *) echo 'Unexpected installed provider' >&2; exit 1;;
            esac
            [ "$(hash "$root$file")" = "$expected" ] || {
                echo "Installed file hash mismatch: $file" >&2; exit 1;
            }
        done < "$bundle/$manifest"
    done
    [ -s "$bundle/mesa-package-links.tsv" ]
    while IFS="$(printf '\t')" read -r file target; do
        case "$file" in
            */../*|*/..) echo 'Invalid link path' >&2; exit 1;;
            /usr/pkg/*) ;;
            *) echo 'Unexpected link provider' >&2; exit 1;;
        esac
        [ -L "$root$file" ] && [ "$(readlink "$root$file")" = "$target" ] || {
            echo "Installed link mismatch: $file" >&2; exit 1;
        }
    done < "$bundle/mesa-package-links.tsv"
}
if [ "$verify_sysroot" = yes ]; then
    sysroot=$(CDPATH= cd -- "$2" && pwd -P)
    check_installed "$sysroot"
    echo 'PASS: sysroot package files, links and libraries only; no target runtime was executed'
    exit 0
fi
arch=$(cat "$bundle/target-arch.txt")
case "$arch" in aarch64|x86_64) ;; *) echo 'Unsupported bundle CPU' >&2; exit 2;; esac
[ "$(uname -s)" = NetBSD ] && [ "$(uname -p)" = "$arch" ] || {
    echo "Run on NetBSD/$arch" >&2; exit 2;
}
for setting in LD_LIBRARY_PATH LD_PRELOAD LIBGL_DRIVERS_PATH GBM_BACKENDS_PATH \
    MESA_LOADER_DRIVER_OVERRIDE LIBGL_ALWAYS_SOFTWARE GALLIUM_DRIVER; do
    eval "value=\${$setting-}"
    [ -z "$value" ] || { echo "Runtime override is not permitted: $setting" >&2; exit 2; }
done
mkdir "$2"
logs=$(CDPATH= cd -- "$2" && pwd -P)
renderer=${3:-llvmpipe}
timeout=${TIMEOUT:-/usr/bin/timeout}
case "$timeout" in /*) ;; *) echo 'TIMEOUT must be absolute' >&2; exit 2;; esac
[ -x "$timeout" ]
check_installed ''
uname -a > "$logs/platform.log"
check_loader() {
    loader_executable=$1
    loader_name=$2
    ldd "$loader_executable" > "$logs/$loader_name.ldd.log" 2>&1
    awk '$2 == "=>" && $3 !~ /^\// { bad=1 } END { exit bad }' "$logs/$loader_name.ldd.log"
    while read -r loader_path; do
        case "$loader_path" in
            /usr/pkg/*)
                loader_path=$(CDPATH= cd -- "$(dirname -- "$loader_path")" && printf '%s/%s' "$(pwd -P)" "$(basename -- "$loader_path")")
                awk -v path="$loader_path" '$2 == path { found=1 } END { exit !found }' \
                    "$bundle/runtime-libraries.sha256" || {
                    echo "Unrecorded installed dependency: $loader_path" >&2; exit 1;
                };;
            /usr/lib/*|/lib/*) ;;
            *) echo "Foreign runtime dependency: $loader_path" >&2; exit 1;;
        esac
    done <<EOF
$(awk '$2 == "=>" { print $3 }' "$logs/$loader_name.ldd.log")
EOF
}
check_loader "$bundle/bin/mesa-render" mesa-render
run_render() {
    if [ "$renderer" = llvmpipe ]; then
        env -i PATH=/bin:/usr/bin:/sbin:/usr/sbin:/usr/pkg/bin MESA_SHADER_CACHE_DISABLE=true \
            LIBGL_ALWAYS_SOFTWARE=1 GALLIUM_DRIVER=llvmpipe "$timeout" 60 \
            "$bundle/bin/mesa-render" surfaceless "$renderer"
    else
        env -i PATH=/bin:/usr/bin:/sbin:/usr/sbin:/usr/pkg/bin MESA_SHADER_CACHE_DISABLE=true "$timeout" 60 \
            "$bundle/bin/mesa-render" surfaceless "$renderer"
    fi
}
run_render > "$logs/mesa-render.log" 2>&1
echo "PASS: installed $renderer shader rejection, triangle and four EGL lifecycles"
failures=0
while IFS="$(printf '\t')" read -r name executable limit; do
    check_loader "$bundle/bin/$executable" "$name"
    result=0
    case "$name" in
        genxml_test)
            env -i PATH=/bin:/usr/bin:/sbin:/usr/sbin:/usr/pkg/bin "$timeout" "$limit" "$bundle/bin/$executable" -quiet \
                > "$logs/$name.log" 2>&1 || result=$?;;
        xmlconfig)
            # Upstream's real fixture home belongs only to this child process.
            env -i PATH=/bin:/usr/bin:/sbin:/usr/sbin:/usr/pkg/bin HOME="$bundle/fixtures/drirc_home" \
                DRIRC_CONFIGDIR="$bundle/fixtures/drirc_configdir" \
                "$timeout" "$limit" "$bundle/bin/$executable" \
                > "$logs/$name.log" 2>&1 || result=$?;;
        process)
            env -i PATH=/bin:/usr/bin:/sbin:/usr/sbin:/usr/pkg/bin BUILD_FULL_PATH="$bundle/bin/$executable" \
                "$timeout" "$limit" "$bundle/bin/$executable" \
                > "$logs/$name.log" 2>&1 || result=$?;;
        process_with_overrides)
            env -i PATH=/bin:/usr/bin:/sbin:/usr/sbin:/usr/pkg/bin BUILD_FULL_PATH="$bundle/bin/$executable" MESA_PROCESS_NAME=hello \
                "$timeout" "$limit" "$bundle/bin/$executable" \
                > "$logs/$name.log" 2>&1 || result=$?;;
        *)
            env -i PATH=/bin:/usr/bin:/sbin:/usr/sbin:/usr/pkg/bin "$timeout" "$limit" "$bundle/bin/$executable" \
                > "$logs/$name.log" 2>&1 || result=$?;;
    esac
    case "$result" in
        0) echo "PASS $name";;
        77) echo "SKIP $name (upstream process exit 77)";;
        *) echo "FAIL $name (exit $result)"; failures=$((failures + 1));;
    esac
    # Distinguish process success from nested upstream skips/disabled cases.
    grep -E '^\[  SKIPPED \]|DISABLED TEST' "$logs/$name.log" || :
done < "$bundle/upstream-tests.tsv"
[ "$failures" = 0 ]
echo 'PASS: installed Mesa test invocations; inspect reported upstream skips/disabled tests separately'
