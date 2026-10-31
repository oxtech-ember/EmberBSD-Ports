#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
# REAL(16) follows the target, not the build machine. On AArch64 ELF
# targets such as NetBSD/aarch64, C long double is IEEE binary128 and
# Flang-RT implements kind 16 with the libm long double functions, so the
# compiler must accept REAL(16) for them. A flang built on macOS, whose long
# double is double, used to reject it for every target ("REAL(KIND=16) is
# not an enabled type for this target"). Darwin targets keep REAL(16) off.
# Usage: real16-target.sh FLANG
set -eu
[ "$#" = 1 ] || { echo 'usage: real16-target.sh FLANG' >&2; exit 2; }
flang=$1
[ -x "$flang" ] || { echo "not executable: $flang" >&2; exit 2; }
work=$(mktemp -d "${TMPDIR:-/tmp}/flang-real16.XXXXXX")
trap 'rm -rf "$work"' EXIT
cat > "$work/k16.f90" <<'F'
subroutine k16(a, b)
  real(kind=16), intent(in) :: a
  real(kind=16), intent(out) :: b
  b = a * 2.0_16
end subroutine k16
F
fail=0
for t in aarch64--netbsd aarch64-unknown-linux-gnu; do
	if ! "$flang" --target=$t -c -o "$work/k16-$t.o" "$work/k16.f90" \
	    > "$work/$t.log" 2>&1; then
		sed -n 1,3p "$work/$t.log"
		echo "FAIL: REAL(16) is rejected for $t"; fail=1
	fi
done
if "$flang" --target=aarch64-apple-darwin -fsyntax-only "$work/k16.f90" \
    > "$work/darwin.log" 2>&1; then
	echo 'FAIL: REAL(16) is accepted for aarch64-apple-darwin'; fail=1
fi
[ "$fail" = 0 ] || exit 1
echo 'PASS: REAL(16) is enabled for AArch64 ELF targets only'
