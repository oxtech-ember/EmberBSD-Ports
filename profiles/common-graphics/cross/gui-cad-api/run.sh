#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; installed GUI/CAD consumer acceptance.
set -eu
if [ "$#" -lt 2 ] || [ "$#" -gt 3 ]; then
    echo 'usage: run.sh BUNDLE NEW_LOG_DIRECTORY [--without-glew]' >&2
    exit 2
fi
bundle=$(cd "$1" && pwd -P)
logs=$2
case "$logs" in /*) ;; *) echo 'require absolute log directory' >&2; exit 2;; esac
test ! -e "$logs"
mkdir "$logs"
cd "$bundle"
while read -r expected path; do
    test "$(sha256 -q "$path")" = "$expected"
done < artifacts.sha256
while read -r expected path; do
    test "$(sha256 -q "$path")" = "$expected"
done < runtime-libraries.sha256
unset LD_LIBRARY_PATH LD_PRELOAD LD_PRELOAD_32 LD_PRELOAD_64
export LIBGL_ALWAYS_SOFTWARE=true GALLIUM_DRIVER=llvmpipe
tests='glu-api cairo-api glm-api glew-egl'
case ${3-} in
    '') ;;
    --without-glew) tests='glu-api cairo-api glm-api';;
    *) echo 'unknown selection' >&2; exit 2;;
esac
for name in $tests; do
    timeout 90 "$bundle/bin/$name" > "$logs/$name.log" 2>&1 || {
        cat "$logs/$name.log"
        exit 1
    }
    awk '/^LOADED: / { print $2 }' "$logs/$name.log" > "$logs/$name.loaded"
    test -s "$logs/$name.loaded"
    while IFS= read -r path; do
        awk -v path="$path" '$2 == path { found=1 } END { exit !found }' \
            runtime-libraries.sha256 || {
            echo "unexpected loaded provider: $path" >&2
            exit 1
        }
    done < "$logs/$name.loaded"
    cat "$logs/$name.log"
done
echo 'PASS: selected installed GUI/CAD consumers and all observed library providers'
