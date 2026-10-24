#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Parse the actual pkgsrc selection block, not an imitation of its algorithm.
set -eu
[ "$#" -eq 2 ] || { echo "Usage: $0 EXPORTED_PKGSRC NEW_WORK" >&2; exit 2; }
source=$1
mkdir "$2"
work=$(CDPATH= cd -- "$2" && pwd)
# The surrounding includes configure platform/package values; these fixtures
# supply only inputs and extract the real version-selection/publication block.
awk '/^PYTHON_VERSION_DEFAULT\?=/ { take=1 } take { print } \
    /^# Additional CONFLICTS/ { exit }' "$source/lang/python/pyversion.mk" > "$work/selection.mk"
cat > "$work/Makefile" <<EOF_MAKE
BSD_PKG_MK= yes
OPSYS= NetBSD
OS_VERSION= 11.0
MACHINE_ARCH= aarch64
PREFIX= /usr/pkg
LOCALBASE= /usr/pkg
USE_PKGSRC_GCC_RUNTIME= no
.include "$source/EMBERBSD-COMMON-TOOLS-MK.CONF"
.include "$work/selection.mk"
all:
	@printf '%s\\n' '\${_PYTHON_VERSION}' '\${PKG_FAIL_REASON}'
EOF_MAKE
probe()
{
    name=$1 selected=$2 refusal=$3
    shift 3
    "${BMAKE:-bmake}" -f "$work/Makefile" "$@" > "$work/$name.log" 2>&1
    [ "$(sed -n '1p' "$work/$name.log")" = "$selected" ]
    if [ "$refusal" = yes ]; then grep -q 'EmberBSD common tools require Python 3.15' "$work/$name.log"; else
        ! grep -q 'EmberBSD common tools require' "$work/$name.log"
    fi
    echo "PASS: actual pkgsrc selection $name ($selected, refusal=$refusal)"
}
probe default 315 no
probe old-cli 313 yes PYTHON_VERSION_REQD=313
probe unsupported none yes PYTHON_VERSIONS_ACCEPTED=313
probe incompatible none yes PYTHON_VERSIONS_INCOMPATIBLE=315
probe consumer-old none yes PYTHON_VERSIONS_ACCEPTED=313 PYTHON_VERSION_REQD=314
