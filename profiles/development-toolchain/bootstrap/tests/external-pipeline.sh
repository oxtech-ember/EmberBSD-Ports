#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Exercise the actual external build dispatcher.
set -eu
here=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd -P)
fixture=$(mktemp -d ${TMPDIR:-/tmp}/ember-runtime-external.XXXXXX)
trap 'rm -rf "$fixture"' EXIT HUP INT TERM
work=$fixture/work
mkdir -p "$work/src/libgcc" "$work/src/libstdc++-v3" "$work/build/gcc" "$work/stage"
cat > "$fixture/make" <<'EOF'
#!/bin/sh
for argument; do
    case "$argument" in all-gcc|all-target-*|install-gcc|install-target-*) echo 'Forbidden compiler/frontend recursion' >&2; exit 99;; esac
done
printf 'make %s\n' "$*" >> "$PIPELINE_LOG"
EOF
cat > "$work/src/config.guess" <<'EOF'
#!/bin/sh
echo aarch64-apple-darwin
EOF
for library in libgcc libstdc++-v3; do
    cat > "$work/src/$library/configure" <<'EOF'
#!/bin/sh
case "$CC" in "$EXPECTED_CC --sysroot=$EXPECTED_SYSROOT -B$EXPECTED_WORK/build/gcc/") ;; *) exit 98;; esac
printf 'configure %s\n' "$0" >> "$PIPELINE_LOG"
printf 'CC = %s\n' "$CC" > Makefile
EOF
    chmod +x "$work/src/$library/configure"
done
chmod +x "$fixture/make"
export PIPELINE_LOG=$fixture/commands.log EXPECTED_CC=$fixture/common-gcc
export EXPECTED_SYSROOT=$fixture/seed EXPECTED_WORK=$work
make=$fixture/make jobs=2 cc=$EXPECTED_CC sysroot=$EXPECTED_SYSROOT
triplet=aarch64--netbsd target_flags=-O2
AR_FOR_TARGET=ar AS_FOR_TARGET=as LD_FOR_TARGET=ld NM_FOR_TARGET=nm
OBJCOPY_FOR_TARGET=objcopy OBJDUMP_FOR_TARGET=objdump RANLIB_FOR_TARGET=ranlib
READELF_FOR_TARGET=readelf STRIP_FOR_TARGET=strip
fail() { echo "$*" >&2; exit 2; }
. "$here/external-compiler.sh"
build_external_runtime
[ "$(grep -c '^configure ' "$PIPELINE_LOG")" -eq 2 ]
grep -Fq 'libgcc-support' "$PIPELINE_LOG"
grep -Fxq 'target_objects=external-compiler' "$work/external-runtime-plan.txt"
# A metadata build that creates a frontend must fail before target configure.
: > "$work/build/gcc/cc1"
if build_external_runtime > "$fixture/reject.log" 2>&1; then
    echo 'FAIL: unexpected frontend build accepted' >&2; exit 1
fi
grep -Fxq 'External runtime mode unexpectedly built a frontend.' "$fixture/reject.log"
echo 'PASS: real external dispatcher uses support metadata and direct runtime targets; forbidden frontend creation fails'
