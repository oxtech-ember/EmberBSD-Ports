#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Check the real native Qt quick profile without building.
set -eu
# These isolated input/PLAN fixtures exercise the lower-level producer.
QT_HOST_LOCKED=1
export QT_HOST_LOCKED

[ "$#" -eq 6 ] || {
    echo "Usage: check-quick-host-tools-profile.sh DISTFILES SDK_PREFIX WAYLAND_SCANNER DBUS_PREFIX NATIVE_TOOLS NEW_WORK" >&2
    exit 2
}
distfiles=$1
prefix=$2
scanner=$3
dbus=$4
native_tools=$5
work=$6
cross_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
recipe=$cross_dir/build-host-tools.sh
manifest=$cross_dir/../sources.tsv
case "$distfiles:$prefix:$scanner:$dbus:$work" in
    /*:/*:/*:/*:/*) ;;
    *) echo "All paths must be absolute" >&2; exit 2 ;;
esac
case "$(uname -s)" in
    Linux) ;;
    *) echo "This profile preflight requires a Linux host" >&2; exit 2 ;;
esac
[ -d "$distfiles" ] && [ -d "$prefix" ] && [ -x "$scanner" ]
[ -f "$manifest" ] && [ -f "$recipe" ]
[ ! -e "$work" ] && [ ! -L "$work" ]
invalid_work=$work.invalid-profile
full_work=$work.default-full
[ ! -e "$invalid_work" ] && [ ! -L "$invalid_work" ]
[ ! -e "$full_work" ] && [ ! -L "$full_work" ]

# Use the published native-tool mapping and real compiler executables from the SDK prefix.
PATH=$native_tools:$prefix/bin:$prefix/sbin
export PATH
CMAKE=$prefix/bin/cmake
NINJA=$prefix/bin/ninja
TAR=$prefix/bin/bsdtar
PATCH=$prefix/bin/nbpatch
HOST_PYTHON=$prefix/bin/python3.15
HOST_CC=$prefix/bin/clang
HOST_CXX=$prefix/bin/clang++
HOST_DBUS_PREFIX=$dbus
WAYLAND_SCANNER=$scanner
export CMAKE NINJA TAR PATCH HOST_PYTHON HOST_CC HOST_CXX HOST_DBUS_PREFIX WAYLAND_SCANNER
for tool in awk grep mktemp rm shasum; do
    command -v "$tool" >/dev/null || { echo "Missing native-tool mapping entry: $tool" >&2; exit 2; }
done
for tool in "$CMAKE" "$NINJA" "$TAR" "$PATCH" "$HOST_PYTHON" "$HOST_CC" "$HOST_CXX" "$prefix/bin/mksh"; do
    [ -x "$tool" ] || { echo "Missing SDK-prefix executable: $tool" >&2; exit 2; }
done
"$HOST_CC" --version | grep -F 'clang version 23.1.4' >/dev/null
"$HOST_CXX" --version | grep -F 'clang version 23.1.4' >/dev/null
[ "$("$scanner" --version 2>&1)" = 'wayland-scanner 1.26.0' ]

# Match the producer's real native D-Bus inputs before invoking it.
dbus_inputs="$dbus/lib/cmake/DBus1/DBus1Config.cmake $dbus/lib/cmake/DBus1/DBus1ConfigVersion.cmake $dbus/lib/pkgconfig/dbus-1.pc $dbus/lib/libdbus-1.so $dbus/include/dbus-1.0/dbus/dbus.h $dbus/lib/dbus-1.0/include/dbus/dbus-arch-deps.h"
for input in $dbus_inputs; do
    [ -s "$input" ] || { echo "Missing native D-Bus input: $input" >&2; exit 2; }
done

# Confirm the exact four real Qt archives from sources.tsv; do not fabricate full-profile inputs.
for module in qtbase qtsvg qtshadertools qtdeclarative; do
    archive=$module-everywhere-src-6.12.0.tar.xz
    expected=$(awk -F '\t' -v a="$archive" '$2 == a { print $3 }' "$manifest")
    [ -n "$expected" ] && [ "$(shasum -a 256 "$distfiles/$archive" | awk '{ print $1 }')" = "$expected" ] || {
        echo "Qt quick-profile archive missing or hash mismatch: $archive" >&2; exit 2;
    }
done

scratch=$(mktemp -d /tmp/ember-qt-quick-profile.XXXXXXXX)
trap 'rm -rf "$scratch"' EXIT HUP INT TERM
: > "$scratch/empty"
if ! (cd "$scratch" && "$CMAKE" -E tar cf probe.tar.zst --zstd empty) > "$scratch/cmake-zstd.log" 2>&1; then
    echo "CMake lacks Zstandard support; producer was not invoked" >&2
    exit 2
fi

# Quick must pass preflight with exactly four modules and leave the work path absent.
quick_status=0
env -u HOST_LLVM_BUILD -u HOST_CLANG_BUILD QT_HOST_TOOLS_PROFILE=quick QT_HOST_TOOLS_PLAN_ONLY=1 \
    "$prefix/bin/mksh" "$recipe" "$distfiles" "$work" > "$scratch/quick.log" 2>&1 || quick_status=$?
if [ "$quick_status" -ne 0 ]; then
    echo "Quick profile preflight failed (baseline RED is expected until producer supports the profile):" >&2
    cat "$scratch/quick.log" >&2
    grep -Eq 'libclang\.dylib|Archive verification failed: qttools|HOST_LLVM_BUILD' "$scratch/quick.log" || {
        echo "Quick profile failed for an unexpected preflight reason" >&2; exit 1;
    }
    [ ! -e "$work" ] || { echo "Producer created work before the plan completed" >&2; exit 1; }
    exit 1
fi
grep -Fx 'PLAN: profile=quick modules=qtbase,qtsvg,qtshadertools,qtdeclarative' "$scratch/quick.log" >/dev/null || {
    echo "Quick plan did not select exactly the four Qt modules" >&2; exit 1;
}
[ ! -e "$work" ] || { echo "PLAN_ONLY created the output work path" >&2; exit 1; }

# Invalid profile must fail before it creates output.
invalid_status=0
env -u HOST_LLVM_BUILD -u HOST_CLANG_BUILD QT_HOST_TOOLS_PROFILE=invalid QT_HOST_TOOLS_PLAN_ONLY=1 \
    "$prefix/bin/mksh" "$recipe" "$distfiles" "$invalid_work" > "$scratch/invalid.log" 2>&1 || invalid_status=$?
[ "$invalid_status" -eq 2 ] || { echo "Invalid profile returned status $invalid_status, expected 2" >&2; exit 1; }
grep -Fx 'Invalid QT_HOST_TOOLS_PROFILE: invalid' "$scratch/invalid.log" >/dev/null
[ ! -e "$invalid_work" ] || { echo "Invalid profile created the output work path" >&2; exit 1; }

# The default remains full. A complete real archive set must also pass its plan.
for input in "$prefix/lib/libclang.so" "$prefix/lib/libclangHandleCXX.a" "$prefix/lib/cmake/clang/ClangConfig.cmake"; do
    [ -s "$input" ] || { echo "Missing SDK-prefix full-profile input: $input" >&2; exit 2; }
done
[ -x "$prefix/bin/llvm-config" ] || { echo "Missing SDK-prefix full-profile executable: $prefix/bin/llvm-config" >&2; exit 2; }
[ "$("$prefix/bin/llvm-config" --version)" = 23.1.4 ] || { echo "Unexpected llvm-config version" >&2; exit 2; }
full_status=0
(
    unset QT_HOST_TOOLS_PROFILE
    HOST_LLVM_BUILD=$prefix HOST_CLANG_BUILD=$prefix QT_HOST_TOOLS_PLAN_ONLY=1 "$prefix/bin/mksh" "$recipe" "$distfiles" "$full_work"
) > "$scratch/full.log" 2>&1 || full_status=$?
missing_module=
for module in qttools qtquicktimeline qtquick3d; do
    if [ ! -f "$distfiles/$module-everywhere-src-6.12.0.tar.xz" ]; then
        missing_module=$module
        break
    fi
done
if [ -n "$missing_module" ]; then
    [ "$full_status" -eq 2 ] || { echo "Incomplete full plan returned $full_status" >&2; exit 1; }
    grep -F "Archive verification failed: $missing_module" "$scratch/full.log" >/dev/null || {
        cat "$scratch/full.log" >&2; exit 1;
    }
else
    [ "$full_status" -eq 0 ] || { cat "$scratch/full.log" >&2; exit 1; }
    grep -Fx 'PLAN: profile=full modules=qtbase,qtsvg,qtshadertools,qtdeclarative,qttools,qtquicktimeline,qtquick3d' "$scratch/full.log" >/dev/null
fi
[ ! -e "$full_work" ] || { echo "Incomplete default-full plan created the output work path" >&2; exit 1; }

printf '%s\n' 'PASS: real Qt 6.12 quick profile preflight, invalid-profile refusal, and seven-archive full default'
