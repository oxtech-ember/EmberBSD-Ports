#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
# Usage: clang-runtime-config.sh NEW_WORK [CLANG]
# The native Clang config selects compiler-rt, libunwind and libc++ and no
# GCC runtime. With CLANG (an LLVM 23 clang), a real NetBSD driver trace
# with the generated config links those runtimes and no -lgcc/-lstdc++.
set -eu
[ "$#" -ge 1 ] || { echo "Usage: $0 NEW_WORK [CLANG]" >&2; exit 2; }
root=$(cd "$(dirname "$0")/../../.." && pwd)
helper=$root/pkgsrc/lang/clang/files/llvm-runtime-config.sh
recipe=$root/pkgsrc/lang/clang/Makefile.common
work=$1 clang=${2:-}
mkdir "$work"
work=$(cd "$work" && pwd)
! grep -q gcc16 "$recipe"
! grep -qi 'gcc-config' "$recipe"
grep -Fq 'DEPENDS+= compiler-rt-${LLVM_VERSION}{,nb*}:../../lang/compiler-rt' "$recipe"
grep -Fq '${FILESDIR}/llvm-runtime-config.sh ${LLVM_CONFIG_PATH:Q}' "$recipe"
for arch in aarch64 x86_64; do
    printf '#!/bin/sh\necho %s-unknown-netbsd11.0\n' "$arch" > "$work/llvm-config-$arch"
    chmod +x "$work/llvm-config-$arch"
    sh "$helper" "$work/llvm-config-$arch" "$work/out-$arch"
    cfg=$work/out-$arch/$arch-unknown-netbsd11.0.cfg
    grep -v '^#' "$cfg" > "$work/options-$arch"
    printf '%s\n' --rtlib=compiler-rt --unwindlib=libunwind -stdlib=libc++ | cmp - "$work/options-$arch"
    ! grep -qi 'gcc' "$work/options-$arch"
    [ "$(cat "$work/out-$arch/PLIST")" = "etc/clang/$arch-unknown-netbsd11.0.cfg" ]
    if sh "$helper" "$work/llvm-config-$arch" "$work/out-$arch" 2>/dev/null; then exit 1; fi
done
printf '#!/bin/sh\necho aarch64-unknown-linux-gnu\n' > "$work/llvm-config-linux"
chmod +x "$work/llvm-config-linux"
if sh "$helper" "$work/llvm-config-linux" "$work/out-linux" 2>/dev/null; then exit 1; fi
if sh "$helper" relative/llvm-config "$work/out-rel" 2>/dev/null; then exit 1; fi
[ -n "$clang" ] || { echo 'PASS: native Clang runtime config (no driver traces)'; exit 0; }
echo 'int main(void) { return 0; }' > "$work/a.c"
mkdir "$work/cfgdir"
cp "$work/out-aarch64/aarch64-unknown-netbsd11.0.cfg" "$work/cfgdir/"
trace() { "$clang"++ "$@" --target=aarch64-unknown-netbsd11.0 -### "$work/a.c" 2>&1; }
after=$(trace --config-system-dir="$work/cfgdir")
case "$after" in *'"-lc++"'*) ;; *) echo 'FAIL: no libc++'; exit 1 ;; esac
case "$after" in *'"-lunwind"'*) ;; *) echo 'FAIL: no libunwind'; exit 1 ;; esac
case "$after" in *clang_rt.builtins*) ;; *) echo 'FAIL: no compiler-rt builtins'; exit 1 ;; esac
case "$after" in *'"-lgcc'*|*'"-lstdc++"'*) echo 'FAIL: GCC runtime still linked'; exit 1 ;; esac
echo 'PASS: native Clang runtime config and driver traces'
