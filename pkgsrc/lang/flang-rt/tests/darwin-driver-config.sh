#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). On Darwin, plain flang from the installed
# prefix must find the intrinsic modules of lang/flang-rt. The driver's
# default triple names the full kernel version (aarch64-apple-darwin27.0.0);
# the modules are under the major-version triple. The program uses intrinsic
# modules and is compiled, linked and run with no module path and no
# --target. Without the configuration file the same compile must fail, so
# the result comes from that file.
# Usage: darwin-driver-config.sh INSTALLED_PREFIX NEW_WORK
set -eu
[ "$#" -eq 2 ] || { echo "Usage: $0 INSTALLED_PREFIX NEW_WORK" >&2; exit 2; }
fail() { echo "FAIL: $*" >&2; exit 1; }
[ "$(uname -s)" = Darwin ] || { echo "SKIP: not a Darwin host"; exit 0; }
prefix=$(CDPATH= cd -- "$1" && pwd)
mkdir "$2"
work=$(CDPATH= cd -- "$2" && pwd)
flang=$prefix/bin/flang
triple=$("$flang" -print-target-triple)
config=$prefix/bin/${triple%%.*}-flang.cfg
[ -f "$config" ] || fail "no driver configuration $config for $triple"
cat > "$work/modules.f90" <<'PROGRAM'
program modules
  use, intrinsic :: iso_fortran_env, only: int64
  use, intrinsic :: ieee_arithmetic, only: ieee_is_nan, ieee_value, ieee_quiet_nan
  integer(int64) :: n = 42_int64
  if (.not. ieee_is_nan(ieee_value(1.0, ieee_quiet_nan))) stop 1
  print '(a,i0)', 'modules ', n
end program
PROGRAM
cd "$work"
"$flang" --no-default-config -c modules.f90 -o refused.o > refused.log 2>&1 &&
    fail "the driver finds the modules without its configuration file"
grep -q 'iso_fortran_env' refused.log || fail "unexpected failure: $(cat refused.log)"
"$flang" modules.f90 -o modules > build.log 2>&1 || fail "plain flang: $(cat build.log)"
[ "$(env -i PATH=/usr/bin:/bin ./modules)" = "modules 42" ] || fail "the program output differs"
echo "PASS: plain flang ($triple) uses the modules named by $(basename "$config")"
