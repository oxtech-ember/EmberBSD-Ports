#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted); fake-cross graph metadata can precede target RT.
# Usage: BMAKE=BMAKE cross-libtool-fortran-metadata.sh NEW_WORK
set -eu
[ "$#" -eq 1 ] || { echo "Usage: BMAKE=BMAKE $0 NEW_WORK" >&2; exit 2; }
case "$1" in /*) ;; *) echo 'NEW_WORK must be absolute' >&2; exit 2;; esac
work=$1
mkdir "$work" "$work/bin" "$work/empty-target"
make=${BMAKE:?set BMAKE to the selected bmake}
ports=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cp "$ports/cross/fortran.mk" "$work/fortran.mk"
cp "$ports/cross/flang-version.mk" "$work/EMBERBSD-CROSS-FLANG-VERSION.MK"
cat > "$work/bin/flang" <<'FLANG'
#!/bin/sh
echo 'flang version 23.1.4'
FLANG
chmod +x "$work/bin/flang"
"$make" -f "$work/fortran.mk" MAKECONF=/dev/null \
	PKGPATH=cross/cross-libtool-fortran USE_LANGUAGES=fortran \
	TOOLS_USE_CROSS_COMPILE=no USE_CROSS_COMPILE=yes \
	EMBERBSD_HOST_COMPILER_FAMILY=clang EMBERBSD_CROSS_COMPILER_FAMILY=clang \
	PKGSRC_COMPILER=clang EMBERBSD_FLANG="$work/bin/flang" \
	TOOLBASE="$work/host" CROSS_DESTDIR="$work/empty-target" \
	CROSS_LOCALBASE=/usr/pkg OPSYS=NetBSD MACHINE_GNU_PLATFORM=aarch64--netbsd \
	_EMBER_CROSS_TRIPLET=aarch64--netbsd \
	CROSS_TARGET_DEPENDS=flang-rt\>=23.1.4nb4:../../lang/flang-rt \
	-V '${PKG_FAIL_REASON}' -V '${FC}' -V '${TOOL_DEPENDS}' \
	-V '${CROSS_TARGET_DEPENDS}' > "$work/vars" || {
	echo 'FAIL: cannot query fake-cross metadata with installed Flang and missing target runtime' >&2; exit 1; }
{
	IFS= read -r fail_reason
	IFS= read -r fc
	IFS= read -r tools
	IFS= read -r target
} < "$work/vars"
[ -z "$fail_reason" ] || { echo "FAIL: absent target runtime rejects graph metadata: $fail_reason" >&2; exit 1; }
[ "$fc" = flang ] || { echo "FAIL: installed host Flang is not selected: $fc" >&2; exit 1; }
case " $tools " in *" flang-"*) ;; *) echo "FAIL: native Flang dependency is missing: $tools" >&2; exit 1;; esac
case " $target " in *" flang-rt>=23.1.4nb4:../../lang/flang-rt "*) ;; *) echo "FAIL: target Flang-RT edge is missing: $target" >&2; exit 1;; esac
echo 'PASS: installed host Flang and declared target Flang-RT are graphable before target runtime installation'
