#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors. Prepared with AI assistance.
set -eu
if [ "$#" -ne 4 ]; then
    echo "Usage: $0 BASELINE_PROTOC PATCHED_PROTOC CPP_CONSUMER NEW_OUTPUT_DIRECTORY" >&2
    exit 2
fi
baseline=$1
patched=$2
consumer=$3
output=$4
probe=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
valgrind=${VALGRIND:-valgrind}
[ -x "$baseline" ] && [ -x "$patched" ] && [ -x "$consumer" ]
[ ! -e "$output" ] || { echo "Use a new output directory" >&2; exit 2; }
mkdir -p "$output/baseline" "$output/patched"
check_memory()
{
    "$valgrind" --tool=memcheck --track-origins=yes --leak-check=full \
        --show-leak-kinds=all --errors-for-leak-kinds=all --num-callers=40 \
        --error-exitcode=99 --suppressions="$probe/native-runtime.supp" "$@"
}
set +e
check_memory "$baseline" --cpp_out="$output/baseline" -I "$probe" \
    "$probe/contract.proto" > "$output/baseline.log" 2>&1
baseline_status=$?
set -e
printf '%s\n' "$baseline_status" > "$output/baseline.status"
[ "$baseline_status" -eq 99 ]
grep -q 'DescriptorPool::' "$output/baseline.log"
check_memory "$patched" --cpp_out="$output/patched" -I "$probe" \
    "$probe/contract.proto" > "$output/patched.log" 2>&1
grep -q 'ERROR SUMMARY: 0 errors' "$output/patched.log"
cmp "$output/baseline/contract.pb.cc" "$output/patched/contract.pb.cc"
cmp "$output/baseline/contract.pb.h" "$output/patched/contract.pb.h"
check_memory "$consumer" > "$output/consumer.log" 2>&1
grep -q 'PASS: protobuf installed C++ contract (14 checks)' "$output/consumer.log"
grep -q 'ERROR SUMMARY: 0 errors' "$output/consumer.log"
echo "PASS: exact process-lifetime exceptions preserve the failing CLI control"
echo "PASS: repaired CLI and installed C++ API have no unsuppressed errors"
