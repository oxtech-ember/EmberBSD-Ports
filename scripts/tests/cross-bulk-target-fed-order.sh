#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
# Planning must use build's target identity even when a native root is seen
# before a later target edge; a native-only root must keep native settings.
set -eu
[ "$#" = 1 ] || { echo 'Usage: cross-bulk-target-fed-order.sh NEW_OUTPUT' >&2; exit 2; }
out=$1
case "$out" in /*) ;; *) exit 2 ;; esac
[ ! -e "$out" ] || exit 2
ports=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd -P)
for p in pkgtools/pkg_install t/app t/mid t/deep cross/cross-libtool-base d/only d/extra; do mkdir -p "$out/tree/$p"; done
mkdir -p "$out/native-db" "$out/sdk/scripts"
: > "$out/mk.conf"
printf 'print(1)\n' > "$out/sdk/scripts/resolve-jobs.py"
: > "$out/native-db/cross-libtool-base-NetBSD-11.0-x86_64-2.6.2nb5"
printf '#!%s\n' "${TEST_SHELL:?}" > "$out/pkg_info"
cat >> "$out/pkg_info" <<'WRAP'
case "$*" in
  *'cross-libtool-base-NetBSD-11.0-x86_64>=2.6.2nb5'*) exit 0 ;;
  *) exit 1 ;;
esac
WRAP
printf '#!%s\n' "${TEST_SHELL:?}" > "$out/bmake"
cat >> "$out/bmake" <<WRAP
out=$out
dir= target= varname= varnames= role=target targetfed=no
printf '%s\n' "\$*" >> "\$out/calls"
while [ "\$#" -gt 0 ]; do
 case "\$1" in
  -C) dir=\$2; shift 2 ;;
  VARNAME=*) varname=\${1#VARNAME=}; shift ;;
  VARNAMES=*) varnames=\${1#VARNAMES=}; shift ;;
  USE_CROSS_COMPILE=no) role=native; shift ;;
  TARGET_MACHINE_ARCH=x86_64) targetfed=yes; shift ;;
  *=*) shift ;;
  *) target=\$1; shift ;;
 esac
done
pkg=\${dir##*/}
value() {
 case "\$pkg:\$role:\$1" in
  app:target:DEPENDS) echo 'mid>=1:../../t/mid' ;;
  mid:target:DEPENDS) echo 'deep>=1:../../t/deep' ;;
  deep:target:TOOL_DEPENDS) echo 'cross-libtool-base-NetBSD-11.0-x86_64>=2.6.2nb5:../../cross/cross-libtool-base' ;;
  cross-libtool-base:native:PKGNAME)
   if [ "\$targetfed" = yes ]; then echo cross-libtool-base-NetBSD-11.0-x86_64-2.6.2nb5; else echo cross-libtool-base----2.6.2nb5; fi ;;
  cross-libtool-base:native:PKGBASE)
   if [ "\$targetfed" = yes ]; then echo cross-libtool-base-NetBSD-11.0-x86_64; else echo cross-libtool-base---; fi ;;
  cross-libtool-base:native:TOOL_DEPENDS) echo 'extra>=1:../../d/extra' ;;
  only:native:PKGNAME) [ "\$targetfed" = no ] || exit 8; echo only-1.0 ;;
  only:native:PKGBASE) echo only ;;
  *:*:PKGNAME) echo "\$pkg-1.0" ;;
  *:*:PKGBASE) echo "\$pkg" ;;
  *:*:.CURDIR) echo "\$dir" ;;
  *) echo ;;
 esac
}
case "\$target" in
 show-var)
  case "\$varname" in
   EMBERBSD_NATIVE_TOOLSET_VERIFIED) echo fake ;;
   PKG_INFO) echo "\$out/pkg_info -K \$out/native-db" ;;
   CROSSTARGETSETTINGS) echo 'TARGET_OPSYS=NetBSD TARGET_OS_VERSION=11.0 TARGET_MACHINE_ARCH=x86_64' ;;
   *) value "\$varname" ;;
  esac ;;
 show-vars) for n in \$varnames; do value "\$n"; done ;;
 *) echo "unexpected bmake target: \$target" >&2; exit 2 ;;
esac
WRAP
chmod +x "$out/bmake" "$out/pkg_info"
printf '%s\n' 'cross/cross-libtool-base@native  ' "d/only@native$(printf '\t')" t/app > "$out/roots"
BMAKE=$ports/scripts/tests/cross-bulk-bmake-proxy.sh CROSS_BULK_TEST_REAL_BMAKE=$out/bmake \
 MAKECONF=$out/mk.conf PKGSRCDIR=$out/tree CROSS_BULK_CPUS=2 CROSS_BULK_JOBS=2 \
 CROSS_BULK_VARS_CACHE=no CROSS_BULK_TEST_HOST_PYTHON="${TEST_PYTHON:?}" CROSS_BULK_TEST_SDK_SOURCE="$out/sdk" \
 sh "$ports/scripts/cross-bulk.sh" order "$out/roots" "$out/state" > "$out/order.log" 2>&1
[ "$(grep -c '^cross/cross-libtool-base@native cross-libtool-base-NetBSD-11.0-x86_64-2.6.2nb5$' "$out/state/packages")" = 1 ]
! grep -q '^d/extra@native ' "$out/state/packages"
grep -q '^d/only@native only-1.0$' "$out/state/packages"
grep -q '^cross/cross-libtool-base@native t/deep$' "$out/state/edges"
echo 'PASS: target-fed native identity, installed leaf, native-only root'
