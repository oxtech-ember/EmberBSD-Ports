#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Validate a bounded failed-support checkpoint.
set -eu
here=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd -P)
fixture=$(mktemp -d ${TMPDIR:-/tmp}/ember-support-resume.XXXXXX)
fixture=$(CDPATH= cd -- "$fixture" && pwd -P)
trap 'rm -rf "$fixture"' EXIT HUP INT TERM
mkdir -p "$fixture/helpers" "$fixture/work/src" "$fixture/work/build/gcc" "$fixture/work/stage" "$fixture/seed"
cp "$here/support-resume.sh" "$fixture/helpers/"
helper=$fixture/helpers/support-resume.sh
work=$fixture/work
printf 'old helper\n' > "$fixture/helpers/prior.sh"
printf 'source\n' > "$work/src/source.cc"
printf 'native archive\n' > "$work/build/native.a"
printf 'compiler\n' > "$fixture/compiler"
printf 'support_target=libgcc-support\n' > "$work/external-compiler.txt"
printf 'seed\n' > "$fixture/seed/libc"
printf '2\n' > "$fixture/failure-exit.txt"
for log in support-build.log support-host.log configure.log patch.log; do printf 'parent support failure\n' > "$work/$log"; done
{
 printf 'scope=runtime-only-external-compiler\ntriplet=aarch64--netbsd\nsysroot=%s\n' "$fixture/seed"
 shasum -a 256 "$fixture/helpers/prior.sh" "$fixture/compiler" "$work/external-compiler.txt"
} > "$work/inputs.txt"
for invalid_exit in 0 00; do
    printf '%s\n' "$invalid_exit" > "$fixture/failure-exit.txt"
    if sh "$helper" checkpoint "$work" "$fixture/failure-exit.txt" > "$fixture/rejected.log" 2>&1; then
        echo "FAIL: accepted zero parent exit: $invalid_exit" >&2; exit 1
    fi
    [ ! -e "$work/support-parent" ]
done
printf '2\n' > "$fixture/failure-exit.txt"
sh "$helper" checkpoint "$work" "$fixture/failure-exit.txt"
sh "$helper" check "$work"
reject() {
 if sh "$helper" check "$work" > "$fixture/rejected.log" 2>&1; then echo "FAIL: accepted $1" >&2; exit 1; fi
}
printf 'changed source\n' > "$work/src/source.cc"
reject source
printf 'source\n' > "$work/src/source.cc"
printf 'changed seed\n' > "$fixture/seed/libc"
reject seed
printf 'seed\n' > "$fixture/seed/libc"
printf 'changed object\n' > "$work/build/native.a"
reject support-object
printf 'native archive\n' > "$work/build/native.a"
printf 'changed compiler\n' > "$fixture/compiler"
reject compiler
printf 'compiler\n' > "$fixture/compiler"
printf 'unexpected\n' > "$work/stage/payload"
reject target-stage
rm "$work/stage/payload"
: > "$work/build/gcc/cc1"
reject frontend
rm "$work/build/gcc/cc1"
mkdir "$work/build/aarch64--netbsd"
: > "$work/build/aarch64--netbsd/target.o"
reject target-object
rm -r "$work/build/aarch64--netbsd"
printf 'extra field\n' >> "$work/inputs.txt"
reject original-receipt
cp "$work/support-parent/inputs.txt" "$work/inputs.txt"
cp "$work/support-parent/failure-exit.txt" "$fixture/saved-exit"
printf '0\n' > "$work/support-parent/failure-exit.txt"
reject failure-proof
cp "$fixture/saved-exit" "$work/support-parent/failure-exit.txt"
# A reviewed helper update uses authenticated original helper bytes.
printf 'new helper\n' > "$fixture/helpers/prior.sh"
sh "$helper" check "$work"
original=$(shasum -a 256 "$work/support-parent/inputs.txt" | awk '{print $1}')
sh "$helper" resume "$work"
grep -Fxq "resume_support_prior_inputs_sha256=$original" "$work/inputs.txt"
[ "$(shasum -a 256 "$work/support-parent/inputs.txt" | awk '{print $1}')" = "$original" ]
grep -Fq "$work/support-parent/helpers/prior.sh" "$work/inputs.txt"
reject duplicate-transition
printf 'PASS: support checkpoint, zero/00, nine changed-state controls and explicit immutable-parent receipt\n'
