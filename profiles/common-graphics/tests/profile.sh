#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; AI-assisted early production-profile failure checks.
set -eu
[ "$#" -eq 2 ] || { echo "Usage: $0 EXPORTED_PKGSRC NEW_WORK" >&2; exit 2; }
tree=$(CDPATH= cd -- "$1" && pwd)
mkdir "$2"
work=$(CDPATH= cd -- "$2" && pwd)
cat > "$work/Makefile" <<MK
BSD_PKG_MK=yes
.include "$tree/EMBERBSD-COMMON-TOOLS-MK.CONF"
.include "$tree/EMBERBSD-COMMON-GRAPHICS-MK.CONF"
all:
	@printf '%s\n' '\${PKG_FAIL_REASON:U}'
MK
make=${BMAKE:-bmake}
run() { (cd "$work" && "$make" -r -m / OPSYS=NetBSD OS_VERSION=11.0 MACHINE_ARCH=aarch64 PREFIX=/usr/pkg LOCALBASE=/usr/pkg EMBERBSD_COMMON_TOOLS=yes "$@"); }
[ -z "$(run)" ]
run PKGSRC_COMPILER=clang | grep 'selected pkgsrc GCC 16.2 compiler'
run GCC_REQD=12 | grep 'requires GCC_REQD=16.2'
run USE_CROSS_COMPILE=yes | grep 'requires EMBERBSD_COMMON_GRAPHICS_CROSS=yes'
run MACHINE_ARCH=x86_64 | grep 'NetBSD 11/AArch64 only'
run OS_VERSION=10.1 | grep 'NetBSD 11/AArch64 only'
run EMBERBSD_COMMON_TOOLS=no | grep 'requires common build-tools'
# Presence alone does not prove native tool acceptance; absent owner marker fails.
run PYTHONBIN=/usr/pkg/bin/python3.14 | grep 'canonical Python 3.15'
run LLVM_CONFIG_PATH=/opt/llvm13/bin/llvm-config | grep 'canonical LLVM metadata'
run BUILDLINK_API_DEPENDS.MesaLib='MesaLib>=21.3.9' | grep 'overridden MesaLib dependency'
run BUILDLINK_ABI_DEPENDS.libdrm='libdrm>=2.4.134' | grep 'overridden libdrm dependency'
run MESALIB_SUPPORTS_OSMESA=yes | grep 'does not provide OSMESA'
run MESALIB_SUPPORTS_XA=yes | grep 'does not provide XA'
run PKGPATH=lang/libLLVM | grep 'canonical shared LLVM 23'
# Including an unexported profile lacks the provenance/owner markers.
profile=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
sed "s|$tree/EMBERBSD-COMMON-GRAPHICS-MK.CONF|$profile/mk.conf|" "$work/Makefile" > "$work/unprepared.mk"
run -f unprepared.mk | grep 'must be prepared together'
echo 'PASS: native production profile and explicit cross/platform/tool/provider/feature/marker refusals'
