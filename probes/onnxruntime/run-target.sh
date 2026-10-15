#!/bin/sh
# SPDX-License-Identifier: MIT
# Origin: EmberBSD (AI-assisted). Installed GCC16 CPU inference acceptance.
set -eu
[ "$#" = 3 ] || { echo 'Usage: run-target.sh PACKAGES TESTS NEW_RESULTS' >&2; exit 2; }
packages=$1 tests=$2 out=$3
app_prefix=${ONNX_APP_PREFIX:-/usr/pkg}
case "$app_prefix" in /*) ;; *) exit 2;; esac
for path do case "$path" in /*) ;; *) exit 2;; esac; done
[ ! -e "$out" ] && [ ! -L "$out" ] || exit 2
[ "$(uname -s):$(uname -p)" = NetBSD:aarch64 ] || exit 2
PATH=/usr/pkg/bin:/bin:/usr/bin:/sbin:/usr/sbin; export PATH
identity=$(sysctl -n kern.buildinfo)
case "$identity" in EmberBSD:*) ;; *) echo 'An EmberBSD fork kernel is required.' >&2; exit 1;; esac
if [ -n "${ONNX_EXPECTED_KERNEL_BUILDINFO:-}" ]; then
    [ "$identity" = "$ONNX_EXPECTED_KERNEL_BUILDINFO" ]
fi
LC_ALL=C; export LC_ALL
unset LD_LIBRARY_PATH LD_PRELOAD
if pkg_info -e onnxruntime >/dev/null 2>&1; then echo 'Preserve the installed runtime.' >&2; exit 2; fi
mkdir -p "$out/first" "$out/reinstalled" "$out/controls" "$out/upstream"
pkg_add "$packages/onnxruntime-1.31.0.tgz" > "$out/install.log" 2>&1
pkg_admin check onnxruntime > "$out/integrity.log" 2>&1
pkg_info -B onnxruntime > "$out/build-info.txt"
for program in onnx-cpu-c onnx-cpu-cxx onnx-pkgconfig-c onnx-contract onnx-thread-lifecycle onnx-affinity-contract silero-contract; do
    executable=$tests/$program
    case "$program" in onnx-cpu-c|onnx-cpu-cxx) executable=$app_prefix/bin/$program;; esac
    ldd "$executable" > "$out/$program-linkage.txt"
    grep -E '/usr/pkg/(bin/\.\./)?lib/libonnxruntime\.so\.1([[:space:]]|$)' "$out/$program-linkage.txt" >/dev/null
    grep -F '/usr/pkg/gcc16/lib/libstdc++.so.7' "$out/$program-linkage.txt" >/dev/null
    if grep -E 'not found|/workspace/|libgomp|libpython|libc\+\+' "$out/$program-linkage.txt"; then exit 1; fi
done
ldd "$tests/check-onnx-csv" > "$out/checker-linkage.txt"
if grep -E 'libonnxruntime|not found' "$out/checker-linkage.txt"; then exit 1; fi
inference()
{
    pass=$1
    for language in c cxx; do
        for batch in 1 3 32; do
            case "$batch" in 1) repeats=1;; 3) repeats=100;; 32) repeats=4;; esac
            "$app_prefix/bin/onnx-cpu-$language" "$tests/models/tiny-mlp.onnx" "$batch" "$repeats" \
                "$out/$pass/$language-$batch.csv" > "$out/$pass/$language-$batch.stdout" 2> "$out/$pass/$language-$batch.log"
            "$tests/check-onnx-csv" "$batch" "$repeats" "$out/$pass/$language-$batch.csv" \
                > "$out/$pass/check-$language-$batch.log" 2>&1
        done
    done
    for batch in 1 3 32; do cmp "$out/$pass/c-$batch.csv" "$out/$pass/cxx-$batch.csv"; done
    "$tests/onnx-pkgconfig-c" "$tests/models/tiny-mlp.onnx" 3 100 "$out/$pass/pkgconfig.csv" > "$out/$pass/pkgconfig.stdout" 2> "$out/$pass/pkgconfig.log"
    cmp "$out/$pass/c-3.csv" "$out/$pass/pkgconfig.csv"
    "$tests/onnx-contract" > "$out/$pass/contract.log" 2>&1
    "$tests/onnx-thread-lifecycle" "$tests/models/tiny-mlp.onnx" > "$out/$pass/thread-lifecycle.log" 2>&1
    "$tests/onnx-affinity-contract" > "$out/$pass/affinity.log" 2>&1
}
inference first
for language in c cxx; do
    for fault in wrong-shape missing-input missing-output malformed missing-file; do
        model=$tests/models/tiny-mlp.onnx
        set --
        case "$fault" in
            malformed) model=$tests/models/malformed.onnx;;
            missing-file) model=$tests/models/absent.onnx;;
            *) set -- "--$fault";;
        esac
        printf 'preserve output\n' > "$out/controls/preserved.csv"
        status=0
        "$app_prefix/bin/onnx-cpu-$language" "$model" 3 2 "$out/controls/preserved.csv" "$@" \
            > "$out/controls/$language-$fault.stdout" 2> "$out/controls/$language-$fault.log" || status=$?
        [ "$status" = 65 ]
        case "$fault" in malformed) code=7;; missing-file) code=3;; *) code=2;; esac
        grep -F "ONNX Runtime [$code]:" "$out/controls/$language-$fault.log" >/dev/null
        [ "$(cat "$out/controls/preserved.csv")" = 'preserve output' ]
        printf '%s\n' "$status" > "$out/controls/$language-$fault.status"
    done
done
"$tests/float16-baseline" > "$out/controls/float16.log" 2>&1
"$tests/netbsd-cpu-source-contract" --affinity > "$out/controls/current-cpu.log" 2>&1
for program in onnx-header-reason-c onnx-header-reason-cxx onnx-header-reason-cxx-baseline; do
    "$tests/$program" > "$out/controls/$program.log" 2>&1
    grep -F 'value=-2147483648' "$out/controls/$program.log" >/dev/null
    grep -F 'mask=80000000' "$out/controls/$program.log" >/dev/null
done
cmp "$out/controls/onnx-header-reason-cxx.log" "$out/controls/onnx-header-reason-cxx-baseline.log"
"$tests/posix-thread-patched" > "$out/controls/posix-thread-patched.log" 2>&1
status=0
"$tests/posix-thread-baseline" > "$out/controls/posix-thread-baseline.log" 2>&1 || status=$?
[ "$status" = 3 ]
printf '%s\n' "$status" > "$out/controls/posix-thread-baseline.status"
for expected in \
    'FAIL default initialized=1 destroyed=0 threw=0 diagnostics_ok=1' \
    'FAIL explicit-stack initialized=1 destroyed=0 threw=0 diagnostics_ok=1' \
    'FAIL init-failure initialized=0 destroyed=0 threw=1 diagnostics_ok=0' \
    'FAIL stack-failure initialized=1 destroyed=0 threw=1 diagnostics_ok=0' \
    'FAIL create-failure initialized=1 destroyed=0 threw=1 diagnostics_ok=0'; do
    grep -qx "$expected" "$out/controls/posix-thread-baseline.log"
done
for mode in default explicit-stack init-failure stack-failure create-failure; do
    grep -q "^PASS $mode " "$out/controls/posix-thread-patched.log"
done
for mode in real fail-map; do
    status=0
    "$tests/mlas-guard-baseline" "--$mode" > "$out/controls/mlas-baseline-$mode.log" 2>&1 || status=$?
    case "$mode" in real) expected=4;; fail-map) expected=3;; esac
    [ "$status" = "$expected" ]
    printf '%s\n' "$status" > "$out/controls/mlas-baseline-$mode.status"
done
grep -F 'FAIL real guard mapping aborted' "$out/controls/mlas-baseline-real.log" >/dev/null
grep -F 'result=mapped errno=0' "$out/controls/mlas-baseline-real.log" >/dev/null
grep -F 'mprotect: protection=0x3 result=-1 errno=13 ' "$out/controls/mlas-baseline-real.log" >/dev/null
grep -F 'FAIL mapping failure reached mprotect' "$out/controls/mlas-baseline-fail-map.log" >/dev/null
for mode in real fail-map guard; do
    "$tests/mlas-guard-patched" "--$mode" > "$out/controls/mlas-patched-$mode.log" 2>&1
    grep -F 'PASS' "$out/controls/mlas-patched-$mode.log" >/dev/null
done
grep -Fx 'PASS real mapping: writable data, released reservation' "$out/controls/mlas-patched-real.log" >/dev/null
grep -Fx 'PASS mapping failure stopped before mprotect' "$out/controls/mlas-patched-fail-map.log" >/dev/null
grep -Fx 'PASS upper guard remains inaccessible (child SIGSEGV)' "$out/controls/mlas-patched-guard.log" >/dev/null
"$tests/onnx-upstream-controls" --gtest_output="xml:$out/upstream/tests.xml" > "$out/upstream/tests.log" 2>&1
"$tests/silero-contract" "$tests/silero/silero_vad.onnx" "$tests/silero/test.wav" > "$out/first/silero.log" 2>&1
for fault in model wave; do
    model=$tests/silero/silero_vad.onnx wave=$tests/silero/test.wav
    case "$fault" in model) model=$tests/models/malformed.onnx;; wave) wave=$tests/models/malformed.onnx;; esac
    status=0
    "$tests/silero-contract" "$model" "$wave" > "$out/controls/silero-$fault.log" 2>&1 || status=$?
    [ "$status" = 1 ]
    printf '%s\n' "$status" > "$out/controls/silero-$fault.status"
done
pkg_delete onnxruntime > "$out/remove.log" 2>&1
if pkg_info -e onnxruntime >/dev/null 2>&1; then exit 1; fi
for path in lib/libonnxruntime.so lib/libonnxruntime.so.1 include/onnxruntime/onnxruntime_c_api.h; do
    [ ! -e "/usr/pkg/$path" ] && [ ! -L "/usr/pkg/$path" ]
done
pkg_add "$packages/onnxruntime-1.31.0.tgz" > "$out/reinstall.log" 2>&1
inference reinstalled
for language in c cxx; do
    for batch in 1 3 32; do cmp "$out/first/$language-$batch.csv" "$out/reinstalled/$language-$batch.csv"; done
done
"$tests/silero-contract" "$tests/silero/silero_vad.onnx" "$tests/silero/test.wav" > "$out/reinstalled/silero.log" 2>&1
cmp "$out/first/silero.log" "$out/reinstalled/silero.log"
pkg_admin check onnxruntime > "$out/reinstalled-integrity.log" 2>&1
echo 'PASS: installed C/C++ CPU inference, independent MLP answers, Silero, upstream tests and package lifecycle'
