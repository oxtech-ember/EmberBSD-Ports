#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Native dependency recursion of a Clang
# build compiles Fortran with the host Flang, never a pkgsrc GCC Fortran.
# Without the native prefix Flang-RT it refuses with a clear reason.
set -eu
[ "$#" = 3 ] || { echo "Usage: $0 EXPORTED_PKGSRC CROSS_MAKECONF NEW_WORK" >&2; exit 2; }
pkgsrc=$1 makeconf=$2 work=$3
bmake=${BMAKE:-bmake}
for path in "$pkgsrc" "$makeconf" "$work"; do
    case "$path" in /*) ;; *) exit 2 ;; esac
    case "$path" in *[!a-zA-Z0-9_./-]*) exit 2 ;; esac
done
mkdir "$work"
fail() { echo "FAIL: $*" >&2; exit 1; }
gcc_fail() {
    grep -Ei 'gcc|gfortran|g95|f2c' "$@" >&2
    fail 'native Clang Fortran resolves to a GCC provider'
}
# math/blas is a plain Fortran recipe.
"$bmake" -C "$pkgsrc/math/blas" MAKECONF="$makeconf" USE_CROSS_COMPILE=no show-vars \
    VARNAMES='EMBERBSD_HOST_COMPILER_FAMILY PKGSRC_FORTRAN FC PKG_FC PKG_FAIL_REASON OPSYS CMAKE_CONFIGURE_ARGS' \
    > "$work/native.txt" 2> "$work/native.err" || {
    ! grep -Eiq 'gcc|gfortran' "$work/native.err" || gcc_fail "$work/native.err"
    fail "native Fortran metadata does not evaluate; see $work/native.err"
}
"$bmake" -C "$pkgsrc/math/blas" MAKECONF="$makeconf" USE_CROSS_COMPILE=no \
    show-depends-pkgpaths > "$work/depends.txt" 2> "$work/depends.err" ||
    fail "native dependencies do not evaluate; see $work/depends.err"
line() { sed -n "$1p" "$work/native.txt"; }
[ "$(line 1)" = clang ] || fail "the native family is '$(line 1)', not clang"
[ -z "$(line 2)" ] || fail "native Fortran selects the pkgsrc module '$(line 2)'"
[ "$(line 3)" = flang ] || fail "native FC is '$(line 3)', not flang"
case "$(line 4)" in */.flang/bin/flang) ;; *)
    fail "native PKG_FC is '$(line 4)', not the host Flang link" ;; esac
# No compiler, Fortran module or dependency may name GCC.
! grep -Eiq 'gcc|gfortran|g95|f2c' "$work/native.txt" "$work/depends.txt" ||
    gcc_fail "$work/native.txt" "$work/depends.txt"
# CMake's Darwin shared-library rule passes -install_name to the Fortran
# driver; Flang accepts it only through the linker.
if [ "$(line 6)" = Darwin ]; then
    case " $(line 7) " in
    # One shell-quoted CMake value: CMake splits it on the link line.
    *' -DCMAKE_SHARED_LIBRARY_SONAME_Fortran_FLAG:STRING=-Xlinker\ -install_name\ -Xlinker '*) ;;
    *) fail 'Darwin CMake hands Flang the C driver -install_name flag' ;;
    esac
fi
if grep -qx 'lang/flang-rt' "$work/depends.txt"; then
    result='links the native prefix Flang-RT'
else
    case "$(line 5)" in *'Install lang/flang-rt into the native prefix before native Fortran'*) ;; *)
        fail 'without the native prefix Flang-RT the recipe neither depends on it nor refuses' ;; esac
    result='refuses until the native prefix has Flang-RT'
fi
echo "PASS: native Clang Fortran selects the host Flang, no GCC; it $result"
