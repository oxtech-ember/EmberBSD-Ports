#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). EMBERBSD-DEFAULTS-MK.CONF keeps its Darwin
# native block (MACHO_USE_LOAD_COMMANDS, PKG_OPTIONS.graphviz -gd) to
# native builds. The cross profile includes it while OPSYS is still the
# build host's Darwin, and a target build has no USE_CROSS_COMPILE on the
# command line, so the cross profile must select its cross default before
# that include. A native build (USE_CROSS_COMPILE=no) keeps the block.
# The fixture stubs the native inputs and the prepared target tools. It also
# checks cross-bulk's native Rust std node without changing host compilers.
# Usage: cross-darwin-native-defaults.sh BMAKE NEW_DIRECTORY
set -eu
[ "$#" = 2 ] || { echo 'Usage: cross-darwin-native-defaults.sh BMAKE NEW_DIRECTORY' >&2; exit 2; }
bmake=$1 work=$2
case "$bmake$work" in *[!A-Za-z0-9_./+-]*) echo 'Use simple paths.' >&2; exit 2 ;; esac
case "$work" in /*) ;; *) echo 'NEW_DIRECTORY must be absolute' >&2; exit 2 ;; esac
[ ! -e "$work" ] || { echo "$work exists" >&2; exit 2; }
ports=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd -P)
mkdir -p "$work/profile" "$work/tools" "$work/sysroot" "$work/host" \
	"$work/pkgsrc/mk" "$work/pkgsrc/devel/qt6-qttools"
cp "$ports/profiles/common-build-tools/cross/mk.conf" "$work/profile/mk.conf"
cp "$ports/profiles/common-build-tools/cross/host-config.mk" "$work/profile/host-config.mk"
cp "$ports/pkgsrc/defaults.mk.conf" "$work/profile/EMBERBSD-DEFAULTS-MK.CONF"
cp "$ports/pkgsrc/versions.mk" "$work/profile/EMBERBSD-VERSIONS.MK"
cp "$ports/pkgsrc/devel/qt6-qttools/options.mk" "$work/pkgsrc/devel/qt6-qttools/options.mk"
: > "$work/pkgsrc/mk/bsd.fast.prefs.mk"
cat > "$work/pkgsrc/mk/bsd.options.mk" <<'EOF'
PKG_OPTIONS=${${PKG_OPTIONS_VAR}:U}
EOF
: > "$work/profile/native-tools.mk"
# The host profile supplies host-ABI flags. Cross builds must restore their
# incoming target flags/defaults; native dependency builds keep host values.
mkdir -p "$work/host/etc"
cat > "$work/host/etc/mk.conf" <<'EOF'
CPPFLAGS=host-cpp
CFLAGS=host-c
CXXFLAGS=host-cxx
LDFLAGS=host-ld
EOF
: > "$work/mk.conf"
cat > "$work/tools/target.mk" <<'EOF'
_EMBER_TARGET_FAMILY=clang
_EMBER_TARGET_TARGET=aarch64
_EMBER_TARGET_TRIPLET=${_EMBER_CROSS_TRIPLET}
_EMBER_TARGET_SYSROOT=${CROSS_DESTDIR}
_EMBER_TARGET_TOOLS=${TOOLDIR}
PKGSRC_COMPILER=clang
CLANGBASE=${TOOLDIR}
EOF
cat > "$work/Makefile" <<EOF
BSD_PKG_MK=yes
OPSYS=Darwin
EMBERBSD_HOST_PREFIX=$work/host
EMBERBSD_CROSS_TOOLS=$work/tools
EMBERBSD_CROSS_SYSROOT=$work/sysroot
EMBERBSD_CROSS_HOST_PREFIX=$work/host
PREFIX=$work/host
OSX_SDK_PATH=$work/macos.sdk
MACOSX_DEPLOYMENT_TARGET=15.0
CC=/host/cc
CXX=/host/cxx
EMBERBSD_RUST_LOCK_ROOT=$work/locks
EMBERBSD_RUST_LINK_CONTEXT=$work/locks/coordination/heavy-link
CPPFLAGS=target-cpp
CXXFLAGS=target-cxx
.undef LDFLAGS
.include "$work/profile/host-config.mk"
.if defined(LDFLAGS)
_EMBER_TEST_LDFLAGS_AFTER_HOST_DEFINED=yes
.else
_EMBER_TEST_LDFLAGS_AFTER_HOST_DEFINED=no
.endif
.include "$work/profile/mk.conf"
CPPFLAGS+=package-cpp
LDFLAGS+=package-ld
PKGDIR=$ports/pkgsrc/devel/qt6-qttools
.include "$work/pkgsrc/devel/qt6-qttools/options.mk"
EOF
fail() { echo "FAIL: $*" >&2; exit 1; }
read_vars() { "$bmake" -f "$work/Makefile" "$@" -v USE_CROSS_COMPILE -v MACHO_USE_LOAD_COMMANDS -v PKG_OPTIONS.graphviz | tr '\n' ' '; }
getvar() { variable=$1; shift; "$bmake" -f "$work/Makefile" "$@" -v "$variable"; }
target=$(read_vars) || fail "the target parse failed: $target"
[ "$target" = 'yes   ' ] || fail "a target build takes the Darwin native defaults (USE_CROSS_COMPILE MACHO_USE_LOAD_COMMANDS PKG_OPTIONS.graphviz: $target)"
target_qttools=$(getvar PKG_OPTIONS.qt6-qttools) || fail 'the target QtTools option query failed'
[ -z "$target_qttools" ] || fail "the target QtTools package selected host-only tools: $target_qttools"
target_rcd=$("$bmake" -f "$work/Makefile" -v RCD_SCRIPTS_DIR) || fail 'the target rc-directory query failed'
[ "$target_rcd" = /etc/rc.d ] || fail "target rc scripts escaped the target base: $target_rcd"
native=$(read_vars USE_CROSS_COMPILE=no) || fail "the native parse failed: $native"
[ "$native" = 'no yes -gd ' ] || fail "a native build lost the Darwin native defaults: $native"
native_qttools=$(getvar PKG_OPTIONS.qt6-qttools USE_CROSS_COMPILE=no) || fail 'the native QtTools option query failed'
[ "$native_qttools" = host-tools ] || fail "a native dependency did not select QtTools host-tools: $native_qttools"
native_qttools_args=$(getvar CMAKE_CONFIGURE_ARGS USE_CROSS_COMPILE=no) || fail 'the native QtTools CMake feature query failed'
for feature in assistant designer; do
    case " $native_qttools_args " in
    *" -DFEATURE_${feature}=OFF "*) ;;
    *) fail "QtTools host-tools did not disable ${feature}: $native_qttools_args" ;;
    esac
done
case "$native_qttools_args" in *-DFEATURE_linguist=ON*) ;; *) fail "QtTools host-tools lost Linguist: $native_qttools_args" ;; esac
case "$native_qttools_args" in *-DFEATURE_qtattributionsscanner=ON*) ;; *) fail "QtTools host-tools lost qtattributionsscanner: $native_qttools_args" ;; esac
native_rcd=$("$bmake" -f "$work/Makefile" USE_CROSS_COMPILE=no -v RCD_SCRIPTS_DIR) || fail 'the native rc-directory query failed'
[ "$native_rcd" = "$work/host/etc/rc.d" ] || fail "native rc scripts escaped the selected prefix: $native_rcd"
target_cpp=$(getvar CPPFLAGS) || fail 'the cross CPPFLAGS query failed'
target_c=$(getvar CFLAGS) || fail 'the cross CFLAGS query failed'
target_cxx=$(getvar CXXFLAGS) || fail 'the cross CXXFLAGS query failed'
target_ld=$(getvar LDFLAGS) || fail 'the cross LDFLAGS query failed'
target_ld_after_host=$(getvar _EMBER_TEST_LDFLAGS_AFTER_HOST_DEFINED) || fail 'the cross post-host LDFLAGS query failed'
[ "$target_cpp" = 'target-cpp package-cpp' ] || fail "cross CPPFLAGS lost target/package values: $target_cpp"
case "$target_c" in *host-c*) fail "cross CFLAGS inherited host flags over the target default: $target_c" ;; esac
[ "$target_c" = -O2 ] || fail "cross target CFLAGS default changed: $target_c"
[ "$target_cxx" = target-cxx ] || fail "cross CXXFLAGS lost target value: $target_cxx"
case "$target_ld" in *host-ld*) fail "cross LDFLAGS inherited host flags despite originally undefined: $target_ld" ;; esac
case "$target_ld" in *package-ld*) ;; *) fail "cross package LDFLAGS assignment after helper was lost: $target_ld" ;; esac
[ "$target_ld_after_host" = no ] || fail "cross helper did not restore originally undefined LDFLAGS: $target_ld_after_host"
native_flags=$($bmake -f "$work/Makefile" USE_CROSS_COMPILE=no -v CPPFLAGS -v CFLAGS -v CXXFLAGS -v LDFLAGS | tr '\n' '|')
[ "$native_flags" = 'host-cpp package-cpp|host-c|host-cxx|host-ld package-ld|' ] || fail "native build did not retain host flags/package additions: $native_flags"
clang_family=$(getvar EMBERBSD_RUST_TARGET_COMPILER_FAMILY USE_CROSS_COMPILE=no) || fail 'the native Clang family query failed'
clang_prefix=$(getvar EMBERBSD_RUST_COMPILER_PREFIX USE_CROSS_COMPILE=no) || fail 'the native Clang prefix query failed'
clang_sysroot=$(getvar EMBERBSD_RUST_TARGET_SYSROOT USE_CROSS_COMPILE=no) || fail 'the native Clang sysroot query failed'
clang_sdk=$(getvar EMBERBSD_RUST_MACOS_SDK USE_CROSS_COMPILE=no) || fail 'the native Clang SDK query failed'
clang_minimum=$(getvar EMBERBSD_RUST_MACOS_MINIMUM USE_CROSS_COMPILE=no) || fail 'the native Clang minimum query failed'
native_cc=$(getvar CC USE_CROSS_COMPILE=no) || fail 'the native CC query failed'
native_cxx=$(getvar CXX USE_CROSS_COMPILE=no) || fail 'the native CXX query failed'
lock_root=$(getvar EMBERBSD_RUST_LOCK_ROOT USE_CROSS_COMPILE=no) || fail 'the Rust lock-root query failed'
link_context=$(getvar EMBERBSD_RUST_LINK_CONTEXT USE_CROSS_COMPILE=no) || fail 'the Rust link-context query failed'
[ "$clang_family" = clang ] || fail "native Rust target family did not follow Clang: $clang_family"
[ "$clang_prefix" = "$work/host" ] || fail "native Rust compiler prefix mismatch: $clang_prefix"
[ "$clang_sysroot" = "$work/sysroot" ] || fail "native Rust sysroot mismatch: $clang_sysroot"
[ "$clang_sdk" = "$work/macos.sdk" ] || fail "native Rust macOS SDK mismatch: $clang_sdk"
[ "$clang_minimum" = 15.0 ] || fail "native Rust deployment minimum mismatch: $clang_minimum"
[ "$native_cc" = /host/cc ] || fail "cross profile changed native CC: $native_cc"
[ "$native_cxx" = /host/cxx ] || fail "cross profile changed native CXX: $native_cxx"
[ "$lock_root" = "$work/locks" ] || fail "explicit Rust lock root changed: $lock_root"
[ "$link_context" = "$work/locks/coordination/heavy-link" ] || fail "explicit Rust link context changed: $link_context"
gcc_family=$(getvar EMBERBSD_RUST_TARGET_COMPILER_FAMILY USE_CROSS_COMPILE=no EMBERBSD_CROSS_COMPILER_FAMILY=gcc) || fail 'the native GCC family query failed'
gcc_sysroot=$(getvar EMBERBSD_RUST_TARGET_SYSROOT USE_CROSS_COMPILE=no EMBERBSD_CROSS_COMPILER_FAMILY=gcc) || fail 'the native GCC sysroot query failed'
gcc_tools=$(getvar EMBERBSD_RUST_CROSS_TOOLS USE_CROSS_COMPILE=no EMBERBSD_CROSS_COMPILER_FAMILY=gcc) || fail 'the native GCC tools query failed'
gcc_prefix=$(getvar EMBERBSD_RUST_COMPILER_PREFIX USE_CROSS_COMPILE=no EMBERBSD_CROSS_COMPILER_FAMILY=gcc) || fail 'the native GCC prefix query failed'
gcc_sdk=$(getvar EMBERBSD_RUST_MACOS_SDK USE_CROSS_COMPILE=no EMBERBSD_CROSS_COMPILER_FAMILY=gcc) || fail 'the native GCC SDK query failed'
gcc_reason=$(getvar EMBERBSD_RUST_GCC_REASON USE_CROSS_COMPILE=no EMBERBSD_CROSS_COMPILER_FAMILY=gcc) || fail 'the native GCC reason query failed'
[ "$gcc_family" = gcc ] || fail "native Rust target family ignored explicit GCC: $gcc_family"
[ "$gcc_sysroot" = "$work/sysroot" ] || fail "native GCC Rust sysroot mismatch: $gcc_sysroot"
[ "$gcc_tools" = "$work/tools" ] || fail "native GCC Rust tools mismatch: $gcc_tools"
[ -z "$gcc_prefix" ] || fail "GCC route unexpectedly selected a Clang prefix: $gcc_prefix"
[ -z "$gcc_sdk" ] || fail "GCC route unexpectedly selected a Clang SDK: $gcc_sdk"
[ -z "$gcc_reason" ] || fail "GCC route silently supplied its required reason: $gcc_reason"
echo 'PASS: the Darwin native defaults apply to native builds of the cross profile, not to target builds'
echo 'PASS: native Rust std gets selected Clang/GCC target inputs without changing host CC/CXX or inventing lock/GCC policy'
echo 'PASS: host configuration restores cross target flags/defaults and preserves native host flags'
