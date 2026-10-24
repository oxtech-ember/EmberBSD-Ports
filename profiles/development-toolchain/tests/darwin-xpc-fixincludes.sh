#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; AI-assisted regression for gcc-darwin-xpc-choose.patch.
#
# Build fixincl from a patched lang/gcc16 source tree, run it on the macOS
# SDK <xpc/base.h> and require that GCC compiles <xpc/xpc.h> as C and C++
# with the fixed header and fails with the unfixed one.
set -eu
if [ "$#" -ne 2 ]; then
    echo 'Usage: darwin-xpc-fixincludes.sh PATCHED_GCC_SOURCE NEW_WORK' >&2
    echo 'Environment: GCC_CC, GCC_CXX, OSX_SDK_PATH (absolute paths)' >&2
    exit 2
fi
if [ "$(uname -s)" != Darwin ]; then
    echo 'SKIP: darwin-xpc-fixincludes.sh needs a macOS SDK.'
    exit 0
fi
src=$1
work=$2
: "${GCC_CC:?}" "${GCC_CXX:?}" "${OSX_SDK_PATH:?}"
for path in "$src" "$work" "$GCC_CC" "$GCC_CXX" "$OSX_SDK_PATH"; do
    case "$path" in /*) ;; *) echo "Not absolute: $path" >&2; exit 2 ;; esac
done
[ ! -e "$work" ] && [ ! -L "$work" ] || { echo 'NEW_WORK exists.' >&2; exit 2; }
grep -q 'hackname  = darwin_xpc_choose;' "$src/fixincludes/inclhack.def"
grep -q '"darwin_xpc_choose"' "$src/fixincludes/fixincl.x"
mkdir -p "$work"
"$GCC_CC" -dM -E -x c /dev/null > "$work/macros"
grep -q '^#define __GNUC__ 16$' "$work/macros"
! grep -q '__clang__' "$work/macros"

triple=$("$GCC_CC" -dumpmachine)
mkdir -p "$work/build/libiberty" "$work/build/fixincludes"
(cd "$work/build/libiberty" && CC="$GCC_CC" "$src/libiberty/configure" \
    --build="$triple" --host="$triple" > ../libiberty.log 2>&1 &&
    make > ../libiberty-make.log 2>&1)
(cd "$work/build/fixincludes" && CC="$GCC_CC" "$src/fixincludes/configure" \
    --build="$triple" --host="$triple" --target="$triple" > ../fixincludes.log 2>&1 &&
    make oneprocess fixinc.sh > ../fixincludes-make.log 2>&1)

base=$OSX_SDK_PATH/usr/include/xpc/base.h
grep -q '^#define _XPC_CHOOSE_1(\.\.\.) __VA_ARGS__$' "$base"
mkdir -p "$work/in/xpc" "$work/fixed"
cp "$base" "$work/in/xpc/base.h"
: > "$work/macro_list"
(TARGET_MACHINE=$triple srcdir=$src/fixincludes SHELL=/bin/sh \
    MACRO_LIST=$work/macro_list; export TARGET_MACHINE srcdir SHELL MACRO_LIST &&
    cd "$work/build/fixincludes" &&
    /bin/sh ./fixinc.sh "$work/fixed" "$work/in" > ../fixinc.log 2>&1)
for value in 200809 201309 202311; do
    grep -qx "#define _XPC_CHOOSE_$value(...) __VA_ARGS__" "$work/fixed/xpc/base.h"
done

cat > "$work/probe.c" <<'PROBE'
#include <xpc/xpc.h>
int main(void)
{
    xpc_object_t value = xpc_int64_create(1);
    int status = xpc_get_type(value) == XPC_TYPE_INT64 ? 0 : 1;
    xpc_release(value);
    return status;
}
PROBE
cp "$work/probe.c" "$work/probe.cc"
for std in gnu11 gnu23; do
    "$GCC_CC" -std="$std" -Wall -Wextra -Werror -fanalyzer -I"$work/fixed" -isysroot "$OSX_SDK_PATH" \
        -c "$work/probe.c" -o "$work/probe-$std.o" > "$work/c-$std.log" 2>&1
    if "$GCC_CC" -std="$std" -Wall -Wextra -Werror -I"$work/in" -isysroot "$OSX_SDK_PATH" \
        -c "$work/probe.c" -o "$work/unfixed-$std.o" > "$work/unfixed-$std.log" 2>&1; then
        echo "Unfixed <xpc/base.h> compiled with -std=$std; the regression is not exercised." >&2
        exit 1
    fi
    grep -q '_XPC_CHOOSE_202311' "$work/unfixed-$std.log"
done
"$GCC_CXX" -std=gnu++17 -Wall -Wextra -Werror -I"$work/fixed" -isysroot "$OSX_SDK_PATH" \
    -c "$work/probe.cc" -o "$work/probe-cxx.o" > "$work/cxx.log" 2>&1
if "$GCC_CXX" -std=gnu++17 -Wall -Wextra -Werror -I"$work/in" -isysroot "$OSX_SDK_PATH" \
    -c "$work/probe.cc" -o "$work/unfixed-cxx.o" > "$work/unfixed-cxx.log" 2>&1; then
    echo 'Unfixed <xpc/base.h> compiled as C++; the regression is not exercised.' >&2
    exit 1
fi
grep -q 'XPC_NORETURN' "$work/unfixed-cxx.log"

if command -v autogen > /dev/null 2>&1; then
    (cd "$work/build/fixincludes" && make check > ../check.log 2>&1) || true
    grep -qx 'Fixed:  xpc/base.h' "$work/build/check.log"
    if grep 'xpc/base.h' "$work/build/check.log" | grep -vqx 'Fixed:  xpc/base.h'; then
        echo 'fixincludes make check reports xpc/base.h.' >&2
        exit 1
    fi
fi
echo PASS
