#!/bin/sh
# SPDX-License-Identifier: MIT
# Origin: EmberBSD (AI-assisted). Installed ncnn CPU package acceptance.
set -eu
[ "$#" = 3 ] || { echo 'Usage: run-target.sh PACKAGES TESTS NEW_RESULTS' >&2; exit 2; }
packages=$1 tests=$2 out=$3
for path do case "$path" in /*) ;; *) exit 2;; esac; done
[ ! -e "$out" ] && [ ! -L "$out" ] || exit 2
[ "$(uname -s):$(uname -p)" = NetBSD:aarch64 ] || exit 2
identity=$(sysctl -n kern.buildinfo)
case "$identity" in EmberBSD:*) ;; *) echo 'An EmberBSD fork kernel is required.' >&2; exit 1;; esac
if [ -n "${NCNN_EXPECTED_KERNEL_BUILDINFO:-}" ]; then [ "$identity" = "$NCNN_EXPECTED_KERNEL_BUILDINFO" ]; fi
PATH=/usr/pkg/bin:/bin:/usr/bin:/sbin:/usr/sbin; export PATH
LC_ALL=C; export LC_ALL
unset LD_LIBRARY_PATH LD_PRELOAD
ulimit -c 0
if pkg_info -e ncnn >/dev/null 2>&1; then echo 'Preserve the installed ncnn package.' >&2; exit 2; fi
mkdir -p "$out/first" "$out/reinstalled" "$out/controls" "$out/upstream"
pkg_add "$packages/ncnn-20260526.tgz" > "$out/install.log" 2>&1
pkg_admin check ncnn > "$out/integrity.log" 2>&1
pkg_info -B ncnn > "$out/build-info.txt"
for name in ncnn-cpu-c ncnn-cpu-cxx ncnn-pkgconfig-c ncnn-thread-lifecycle ncnn-api-errors; do
    executable=$tests/$name
    case "$name" in ncnn-cpu-c|ncnn-cpu-cxx) executable=/usr/pkg/bin/$name;; esac
    ldd "$executable" > "$out/$name-linkage.txt"
    grep -E '/usr/pkg/(bin/\.\./)?lib/libncnn\.so\.1([[:space:]]|$)' "$out/$name-linkage.txt" >/dev/null
    grep -F '/usr/pkg/gcc16/lib/libstdc++.so.7' "$out/$name-linkage.txt" >/dev/null
    if grep -E 'not found|/workspace/|libgomp|libpython|libc\+\+' "$out/$name-linkage.txt"; then exit 1; fi
done
ldd "$tests/check-ncnn-csv" > "$out/checker-linkage.txt"
if grep -E 'libncnn|not found' "$out/checker-linkage.txt"; then exit 1; fi
inference()
{
    pass=$1
    for language in c cxx; do
        for scenario in small repeated varied; do
            case "$scenario" in
                small) seed=0 count=1 repeats=1;;
                repeated) seed=17 count=3 repeats=100;;
                varied) seed=1023 count=32 repeats=4;;
            esac
            csv=$out/$pass/$language-$scenario.csv
            /usr/pkg/bin/ncnn-cpu-$language "$tests/models/tiny-cnn.param" "$tests/models/tiny-cnn.bin" \
                "$csv" "$seed" "$count" "$repeats" > "$out/$pass/$language-$scenario.stdout" 2> "$out/$pass/$language-$scenario.log"
            "$tests/check-ncnn-csv" "$csv" "$seed" "$count" "$repeats" > "$out/$pass/check-$language-$scenario.log" 2>&1
        done
    done
    for scenario in small repeated varied; do cmp "$out/$pass/c-$scenario.csv" "$out/$pass/cxx-$scenario.csv"; done
    "$tests/ncnn-pkgconfig-c" "$tests/models/tiny-cnn.param" "$tests/models/tiny-cnn.bin" \
        "$out/$pass/pkgconfig.csv" 17 3 100 > "$out/$pass/pkgconfig.stdout" 2> "$out/$pass/pkgconfig.log"
    cmp "$out/$pass/c-repeated.csv" "$out/$pass/pkgconfig.csv"
    "$tests/ncnn-thread-lifecycle" "$tests/models/tiny-cnn.param" "$tests/models/tiny-cnn.bin" > "$out/$pass/thread-lifecycle.log" 2>&1
}
inference first
for language in c cxx; do
    for fault in missing-param malformed-param missing-weights truncated-weights nonfinite-weights unknown-input unknown-output invalid-count; do
        graph=$tests/models/tiny-cnn.param
        weights=$tests/models/tiny-cnn.bin
        count=1
        set --
        expected=65
        case "$fault" in
            missing-param) graph=$tests/models/absent.param;;
            malformed-param) graph=$tests/models/malformed.param;;
            missing-weights) weights=$tests/models/absent.bin;;
            truncated-weights) weights=$tests/models/truncated.bin;;
            nonfinite-weights) weights=$tests/models/nonfinite.bin;;
            unknown-input) set -- absent prob;;
            unknown-output) set -- input absent;;
            invalid-count) count=0; expected=64;;
        esac
        printf 'preserve output\n' > "$out/controls/preserved.csv"
        status=0
        /usr/pkg/bin/ncnn-cpu-$language "$graph" "$weights" "$out/controls/preserved.csv" 0 "$count" 1 "$@" \
            > "$out/controls/$language-$fault.stdout" 2> "$out/controls/$language-$fault.log" || status=$?
        [ "$status" = "$expected" ]
        [ "$(cat "$out/controls/preserved.csv")" = 'preserve output' ]
        printf '%s\n' "$status" > "$out/controls/$language-$fault.status"
    done
done
"$tests/ncnn-api-errors" "$tests/models/malformed.param" "$tests/models/absent.param" \
    "$tests/models/tiny-cnn.param" "$tests/models/absent.bin" "$tests/models/truncated.bin" > "$out/controls/direct-api-errors.log" 2>&1
for name in c_api paramdict expression relu pooling innerproduct softmax convolution; do
    "$tests/ncnn-upstream-$name" > "$out/upstream/$name.log" 2>&1
    printf '%s\n' "$name" >> "$out/upstream/passed.txt"
done
[ "$(wc -l < "$out/upstream/passed.txt" | tr -d ' ')" = 8 ]
status=0
"$tests/ncnn-cpu-source-before" > "$out/controls/cpu-source-before.log" 2>&1 || status=$?
[ "$status" = 2 ]
grep -F 'kernel_online=2 ncnn_logical=1' "$out/controls/cpu-source-before.log" >/dev/null
"$tests/ncnn-cpu-source-after" > "$out/controls/cpu-source-after.log" 2>&1
grep -F 'kernel_online=2 ncnn_logical=2' "$out/controls/cpu-source-after.log" >/dev/null
"$tests/ncnn-cpu-first-use-after" > "$out/controls/cpu-first-use-after.log" 2>&1
"$tests/ncnn-c-api-allocations-before" --baseline > "$out/controls/c-api-allocations-before.log" 2>&1
"$tests/ncnn-c-api-allocations-after" > "$out/controls/c-api-allocations-after.log" 2>&1
"$tests/ncnn-c-api-lifetime-after" > "$out/controls/c-api-lifetime-after.log" 2>&1
"$tests/ncnn-c-api-callbacks-before" --baseline > "$out/controls/c-api-callbacks-before.log" 2>&1
"$tests/ncnn-c-api-callbacks-after" > "$out/controls/c-api-callbacks-after.log" 2>&1
for name in before-cxx after-c after-cxx; do
    "$tests/ncnn-header-$name" > "$out/controls/header-$name.log" 2>&1
done
cmp "$out/controls/header-before-cxx.log" "$out/controls/header-after-cxx.log"
cmp "$out/controls/header-after-c.log" "$out/controls/header-after-cxx.log"
pkg_delete ncnn > "$out/remove.log" 2>&1
if pkg_info -e ncnn >/dev/null 2>&1; then exit 1; fi
for path in lib/libncnn.so lib/libncnn.so.1 include/ncnn/c_api.h lib/cmake/ncnn/ncnnConfig.cmake lib/pkgconfig/ncnn.pc; do
    [ ! -e "/usr/pkg/$path" ] && [ ! -L "/usr/pkg/$path" ]
done
pkg_add "$packages/ncnn-20260526.tgz" > "$out/reinstall.log" 2>&1
pkg_admin check ncnn > "$out/reinstalled-integrity.log" 2>&1
inference reinstalled
for language in c cxx; do
    for scenario in small repeated varied; do cmp "$out/first/$language-$scenario.csv" "$out/reinstalled/$language-$scenario.csv"; done
done
echo 'PASS: installed C/C++ CPU CNN, independent answers, errors, source regressions, eight upstream programs and package lifecycle'
