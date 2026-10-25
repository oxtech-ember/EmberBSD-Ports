#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Real pkgsrc metadata of the native GCC16
# recipe on macOS and of the cross recipe. No build runs.
set -eu
[ "$#" = 4 ] || { echo 'Usage: darwin-host.sh PREPARED_PKGSRC DARWIN_MAKECONF CROSS_MAKECONF NEW_WORK' >&2; exit 2; }
: "${BMAKE:?Set the native bmake executable}"
prepared=$(CDPATH= cd -- "$1" && pwd)
native=$2 cross=$3
mkdir "$4"
work=$(CDPATH= cd -- "$4" && pwd)
query() {
    conf=$1; shift
    "$BMAKE" -C "$prepared/lang/gcc16" "MAKECONF=$conf" "$@"
}
commit=4a334d2f90f786c3fc86cbc9cf72b2f13961b078
[ "$(query "$native" -V '${OPSYS}')" = Darwin ]
[ "$(query "$native" -V '${PATCHFILES}')" = gcc-16.2.0.diff ]
[ "$(query "$native" -V '${PATCH_SITES}')" = \
    "https://raw.githubusercontent.com/Homebrew/homebrew-core/$commit/Patches/gcc/" ]
[ "$(query "$native" -V '${PATCH_DIST_STRIP}')" = -p1 ]
grep -q '^SHA512 (gcc-16.2.0.diff) = a8ab81008f5281302b7e5d680f3519b69fac5bdcf0a90c5a523643a65ca3223b83d929e156f086283d3256860f8f2728a1436f334e9866652b8835db85b0ed1d$' \
    "$prepared/lang/gcc16/distinfo"
grep -q '^Size (gcc-16.2.0.diff) = 205825 bytes$' "$prepared/lang/gcc16/distinfo"
# The seed is GCC16. Clang cannot build stage 1.
[ -z "$(query "$native" PKGSRC_COMPILER=gcc -V '${PKG_FAIL_REASON}')" ]
query "$native" PKGSRC_COMPILER=clang -V '${PKG_FAIL_REASON}' |
    grep -q 'Darwin GCC16 bootstrap requires PKGSRC_COMPILER=gcc'
query "$native" EMBERBSD_GCC16_SEED_CC= -V '${PKG_FAIL_REASON}' |
    grep -q 'Set EMBERBSD_GCC16_SEED_CC from the accepted SDK bootstrap producer plan'
if query "$native" PKGSRC_COMPILER=gcc -V '${CONFIGURE_ARGS}' |
    tr ' ' '\n' | grep -qx -- --disable-bootstrap; then exit 1; fi
args=$(query "$native" PKGSRC_COMPILER=gcc -V '${CONFIGURE_ARGS}')
printf '%s\n' "$args" | tr ' ' '\n' | grep -qx -- --with-darwin-assembler=llvm-mc
sdk_version=$(query "$native" PKGSRC_COMPILER=gcc -V '${EMBERBSD_GCC16_DARWIN_SDK_VERSION}')
[ -n "$sdk_version" ]
printf '%s\n' "$args" | tr ' ' '\n' | grep -Fx -- "--with-darwin-sdk-version=$sdk_version" > /dev/null
query "$native" EMBERBSD_GCC16_DARWIN_SDK_VERSION= -V '${PKG_FAIL_REASON}' |
    grep -q 'Set EMBERBSD_GCC16_DARWIN_SDK_VERSION from the accepted SDK ABI metadata'
for pair in 'as EMBERBSD_GCC16_LLVM_MC' 'ld EMBERBSD_GCC16_LD64_LLD' 'dsymutil EMBERBSD_GCC16_DSYMUTIL'; do
    set -- $pair
    selected=$(query "$native" PKGSRC_COMPILER=gcc -V "\${$2}")
    [ -n "$selected" ]
    printf '%s\n' "$args" | tr ' ' '\n' | grep -Fx -- "--with-$1=$selected" > /dev/null
done
[ -f "$prepared/lang/gcc16/patches/patch-gcc_darwin_llvm_mc" ]
grep -q 'with-darwin-assembler=cctools|llvm-mc' \
    "$prepared/lang/gcc16/patches/patch-gcc_darwin_llvm_mc"
grep -q 'hackname  = darwin_xpc_choose;' \
    "$prepared/lang/gcc16/patches/patch-fixincludes_darwin_xpc_choose"
grep -q '^SHA1 (patch-fixincludes_darwin_xpc_choose) = ' "$prepared/lang/gcc16/distinfo"
grep -q '^+	HIDDEN (ASMNAME (NAME (LDNM)))$' \
    "$prepared/lang/gcc16/patches/patch-libgcc_config_aarch64_lse.S"
grep -q '^SHA1 (patch-libgcc_config_aarch64_lse.S) = ' "$prepared/lang/gcc16/distinfo"
# The filter drops only the libgcobol/configure.tgt section.
cat > "$work/gcc-16.2.0.diff" <<'DIFF'
diff --git a/gcc/config.host b/gcc/config.host
+keep-1
diff --git a/libgcobol/configure.tgt b/libgcobol/configure.tgt
+drop
diff --git a/libgcc/config.host b/libgcc/config.host
+keep-2
DIFF
filter=$(query "$native" -V '${PATCH_DIST_CAT.gcc-16.2.0.diff}')
(cd "$work" && sh -c "$filter") > "$work/filtered.diff"
[ "$(grep -c '^diff --git' "$work/filtered.diff")" = 2 ]
grep -qx '+keep-1' "$work/filtered.diff"
grep -qx '+keep-2' "$work/filtered.diff"
if grep -q -e libgcobol -e '^+drop' "$work/filtered.diff"; then exit 1; fi
# Target packages share the prerequisite source diff, but not native tool selection.
[ "$(query "$cross" -V '${OPSYS}')" = NetBSD ]
[ "$(query "$cross" -V '${PATCHFILES}')" = gcc-16.2.0.diff ]
query "$cross" -V '${CONFIGURE_ARGS}' | tr ' ' '\n' | grep -qx -- --disable-bootstrap
echo 'darwin-host: OK'
