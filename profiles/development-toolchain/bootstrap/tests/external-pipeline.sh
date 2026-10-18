#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Exercise the actual external build dispatcher.
set -eu
here=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd -P)
fixture=$(mktemp -d ${TMPDIR:-/tmp}/ember-runtime-external.XXXXXX)
trap 'rm -rf "$fixture"' EXIT HUP INT TERM
work=$fixture/work
mkdir -p "$work/src/libgcc" "$work/src/libstdc++-v3" "$work/build/gcc" "$work/stage" "$fixture/native" "$fixture/target"
cat > "$fixture/native/tool" <<'EOF_TOOL'
#!/bin/sh
[ "$(cat "$1")" = native-object ] || exit 97
EOF_TOOL
cat > "$fixture/target/nm" <<'EOF_TOOL'
#!/bin/sh
echo 'Target nm cannot inspect a native object' >&2
exit 96
EOF_TOOL
chmod +x "$fixture/native/tool" "$fixture/target/nm"
printf 'native-object\n' > "$fixture/native-object"
cat > "$fixture/make" <<'EOF_MAKE'
#!/bin/sh
set -eu
for argument; do
    case "$argument" in all-gcc|all-target-*|install-gcc|install-target-*) echo 'Forbidden compiler/frontend recursion' >&2; exit 99;; esac
    if [ "$argument" = configure-gcc ]; then
        "${NM:-nm}" "$NATIVE_OBJECT"
        "${AR:-ar}" "$NATIVE_OBJECT"
        "${RANLIB:-ranlib}" "$NATIVE_OBJECT"
    fi
done
case "$PWD" in */libgcc|*/libstdc++-v3)
    [ "$AR" = "$AR_FOR_TARGET" ] && [ "$NM" = "$NM_FOR_TARGET" ] && [ "$RANLIB" = "$RANLIB_FOR_TARGET" ] || exit 95;;
esac
printf 'make %s\n' "$*" >> "$PIPELINE_LOG"
EOF_MAKE
cat > "$work/src/config.guess" <<'EOF_GUESS'
#!/bin/sh
echo aarch64-apple-darwin
EOF_GUESS
for library in libgcc libstdc++-v3; do
    cat > "$work/src/$library/configure" <<'EOF_CONFIGURE'
#!/bin/sh
case "$CC" in "$EXPECTED_CC --sysroot=$EXPECTED_SYSROOT -B$EXPECTED_WORK/build/gcc/") ;; *) exit 98;; esac
[ "$AR" = "$AR_FOR_TARGET" ] && [ "$NM" = "$NM_FOR_TARGET" ] && [ "$RANLIB" = "$RANLIB_FOR_TARGET" ] || exit 95
printf 'configure %s\n' "$0" >> "$PIPELINE_LOG"
printf 'CC = %s\n' "$CC" > Makefile
EOF_CONFIGURE
    chmod +x "$work/src/$library/configure"
done
chmod +x "$fixture/make"
export PIPELINE_LOG=$fixture/commands.log EXPECTED_CC=$fixture/common-gcc
export EXPECTED_SYSROOT=$fixture/seed EXPECTED_WORK=$work NATIVE_OBJECT=$fixture/native-object
make=$fixture/make jobs=2 cc=$EXPECTED_CC sysroot=$EXPECTED_SYSROOT
triplet=aarch64--netbsd target_flags=-O2
AR_FOR_TARGET=$fixture/target/aarch64--netbsd-ar
NM_FOR_TARGET=$fixture/target/aarch64--netbsd-nm
RANLIB_FOR_TARGET=$fixture/target/aarch64--netbsd-ranlib
export AR_FOR_TARGET NM_FOR_TARGET RANLIB_FOR_TARGET
AS_FOR_TARGET=as LD_FOR_TARGET=ld OBJCOPY_FOR_TARGET=objcopy OBJDUMP_FOR_TARGET=objdump
READELF_FOR_TARGET=readelf STRIP_FOR_TARGET=strip
fail() { echo "$*" >&2; exit 2; }
. "$here/external-compiler.sh"
# A generic target alias first in PATH must not inspect native metadata.
if (unset AR NM RANLIB; PATH=$fixture/target:$PATH "$make" configure-gcc) > "$fixture/native-reject.log" 2>&1; then
    echo 'FAIL: target nm accepted a native metadata object' >&2; exit 1
fi
grep -Fxq 'Target nm cannot inspect a native object' "$fixture/native-reject.log"
# Standard native tool variables must survive host metadata calls. The
# direct target configure and make must then override them independently.
export AR=$fixture/native/tool NM=$fixture/native/tool RANLIB=$fixture/native/tool
build_external_runtime
[ "$(grep -c '^configure ' "$PIPELINE_LOG")" -eq 2 ]
grep -Fq 'libgcc-support' "$PIPELINE_LOG"
grep -Fxq 'target_objects=external-compiler' "$work/external-runtime-plan.txt"
: > "$work/build/gcc/cc1"
if build_external_runtime > "$fixture/reject.log" 2>&1; then
    echo 'FAIL: unexpected frontend build accepted' >&2; exit 1
fi
grep -Fxq 'External runtime mode unexpectedly built a frontend.' "$fixture/reject.log"
echo 'PASS: native metadata tools, explicit target override and forbidden frontend controls'
