#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), actual pkgsrc host/target selection checks.
set -eu
[ "$#" = 4 ] || { echo "Usage: $0 PKGSRC CROSS_MAKECONF NATIVE_TOOLS NEW_WORK" >&2; exit 2; }
pkgsrc=$1 conf=$2 native=$3 work=$4
bmake=${BMAKE:-bmake}
mkdir "$work"
cat > "$work/default.mk.conf" <<EOF
.include "$conf"
.undef EMBERBSD_LLVM_NATIVE_TOOLS
EOF
"$bmake" -C "$pkgsrc/lang/llvm" MAKECONF="$work/default.mk.conf" \
    -v TOOL_DEPENDS > "$work/default.txt"
grep -Eq 'llvm-23[.]1[.]4.*:[.][.]/[.][.]/lang/llvm' "$work/default.txt"
"$bmake" -C "$pkgsrc/lang/llvm" MAKECONF="$conf" \
    EMBERBSD_LLVM_NATIVE_TOOLS="$native" -v PKG_FAIL_REASON > "$work/failure.txt"
[ ! -s "$work/failure.txt" ] || [ -z "$(cat "$work/failure.txt")" ]
"$bmake" -C "$pkgsrc/lang/llvm" MAKECONF="$conf" \
    EMBERBSD_LLVM_NATIVE_TOOLS="$native" -v TOOL_DEPENDS \
    -v CMAKE_CONFIGURE_ARGS -v EXTRACT_ELEMENTS > "$work/selected.txt"
if grep -Eq 'llvm-23[.]1[.]4.*:[.][.]/[.][.]/lang/llvm' "$work/selected.txt"; then
    echo 'Redundant whole-host LLVM dependency retained.' >&2; exit 1
fi
for expected in 'CMAKE_SYSTEM_NAME:STRING=NetBSD' 'LLVM_HOST_TRIPLE:STRING=aarch64--netbsd' \
    'LLVM_DEFAULT_TARGET_TRIPLE:STRING=aarch64--netbsd' \
    'LLVM_ENABLE_RTTI=ON' 'LLVM_BUILD_LLVM_DYLIB=ON' 'LLVM_LINK_LLVM_DYLIB=ON' \
    'LLVM_INSTALL_TOOLCHAIN_ONLY=OFF' 'LLVM_INCLUDE_TESTS=ON' 'LLVM_INSTALL_GTEST=ON' \
    'llvm-project-23.1.4.src/libc' 'AArch64;AMDGPU;ARM' 'ARC;CSKY;DirectX;M68k;Xtensa'; do
    grep -Fq "$expected" "$work/selected.txt"
done
mkdir "$work/invalid"
for tool in llvm-tblgen llvm-min-tblgen llvm-config; do
    ln -s "$native/$tool" "$work/invalid/$tool"
done
for tool in llvm-tblgen llvm-min-tblgen llvm-config; do
    rm "$work/invalid/$tool"
    for invalid in missing old failed; do
        case "$invalid" in
        missing) ;;
        old) printf '#!/bin/sh\necho "LLVM version 21.1.8"\n' > "$work/invalid/$tool"; chmod +x "$work/invalid/$tool" ;;
        failed) printf '#!/bin/sh\necho "LLVM version 23.1.4"\nexit 1\n' > "$work/invalid/$tool" ;;
        esac
        "$bmake" -C "$pkgsrc/lang/llvm" MAKECONF="$conf" \
            EMBERBSD_LLVM_NATIVE_TOOLS="$work/invalid" \
            -v PKG_FAIL_REASON > "$work/$tool-$invalid.txt"
        grep -Fq "$tool must execute on the build host" "$work/$tool-$invalid.txt"
    done
    rm "$work/invalid/$tool"
    ln -s "$native/$tool" "$work/invalid/$tool"
done
echo 'PASS: actual cross recipe preserves full payload, isolates host generators and rejects unusable tools.'
