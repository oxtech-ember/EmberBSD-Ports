#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Actual target package and speech acceptance.
set -eu
[ "$#" = 4 ] || { echo 'Usage: run-whisper-target.sh PACKAGE MODEL JFK_WAV NEW_OUTPUT' >&2; exit 2; }
package=$1 model=$2 wav=$3 out=$4
[ "$(uname -s)" = NetBSD ] && [ "$(uname -p)" = aarch64 ] || exit 1
for path do case "$path" in /*) ;; *) exit 2;; esac; done
[ ! -e "$out" ] && [ ! -L "$out" ] || exit 2
[ -z "${LD_LIBRARY_PATH:-}${LD_PRELOAD:-}" ] || exit 2
export PATH=/usr/pkg/bin:/bin:/usr/bin:/sbin:/usr/sbin
export LC_ALL=C
recipe=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
if pkg_info -e whisper-cpp; then echo 'An existing Whisper installation must be preserved.' >&2; exit 1; fi
mkdir "$out"
uname -a > "$out/platform.txt"
pkg_add "$package"
pkg_info -e whisper-cpp-1.9.5
pkg_admin check whisper-cpp > "$out/integrity.txt"
for name in whisper-cli whisper-bench whisper-quantize; do
    ldd "/usr/pkg/bin/$name"
done > "$out/linkage.txt"
grep -q '/usr/pkg/gcc16/lib/libstdc++.so.7' "$out/linkage.txt"
grep -q '/usr/pkg/gcc16/lib/libgcc_s.so.1' "$out/linkage.txt"
if grep -E 'not found|/workspace/' "$out/linkage.txt"; then exit 1; fi
sh "$recipe/../tests/whisper-runtime.sh" /usr/pkg/bin/whisper-cli "$model" "$wav" "$out/runtime" > "$out/runtime.log" 2>&1
pkg_delete whisper-cpp-1.9.5
for name in whisper-cli whisper-bench whisper-quantize; do [ ! -e "/usr/pkg/bin/$name" ] || exit 1; done
if pkg_info -e whisper-cpp-1.9.5; then exit 1; fi
pkg_add "$package"
pkg_admin check whisper-cpp > "$out/reinstalled-integrity.txt"
/usr/pkg/bin/whisper-cli -m "$model" -f "$wav" -l en -t 2 -p 1 -bo 1 -bs 1 -nf -ng \
    -otxt -of "$out/reinstalled" > "$out/reinstalled.stdout" 2> "$out/reinstalled.log"
cmp "$out/runtime/transcript.txt" "$out/reinstalled.txt"
echo 'PASS: installed transcription, error contracts, integrity, removal and reinstallation'
