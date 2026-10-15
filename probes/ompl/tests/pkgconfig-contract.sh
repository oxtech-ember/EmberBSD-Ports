#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Validate the installed headless shared metadata.
set -eu
[ "$#" -ge 1 ] && [ "$#" -le 2 ] || {
    echo 'Usage: pkgconfig-contract.sh STAGED_PREFIX [TARGET_SYSROOT]' >&2; exit 2;
}
prefix=$1
sysroot=${2:-}
case "$prefix" in /*) ;; *) exit 2;; esac
pc=$prefix/lib/pkgconfig/ompl.pc
[ -f "$pc" ]
# Keep discovery inside the selected installation and its target dependencies.
PKG_CONFIG_PATH=
PKG_CONFIG_LIBDIR=$prefix/lib/pkgconfig:$prefix/share/pkgconfig
if [ -n "$sysroot" ]; then
    case "$sysroot" in /*) ;; *) exit 2;; esac
    PKG_CONFIG_LIBDIR=$PKG_CONFIG_LIBDIR:$sysroot/usr/pkg/lib/pkgconfig:$sysroot/usr/pkg/share/pkgconfig
fi
PKG_CONFIG_SYSROOT_DIR=$sysroot
export PKG_CONFIG_PATH PKG_CONFIG_LIBDIR PKG_CONFIG_SYSROOT_DIR
pkg_config=${PKG_CONFIG:-pkg-config}
[ "$("$pkg_config" --modversion ompl)" = 2.0.2 ]
[ "$("$pkg_config" --print-requires ompl)" = eigen3 ]
flags=$("$pkg_config" --cflags --libs ompl)
static=$("$pkg_config" --static --libs ompl)
case " $flags " in *' -lompl '*) ;; *) exit 1;; esac
case " $flags " in *' -lboost_serialization '*) ;; *) exit 1;; esac
case " $static " in *' -lboost_serialization '*) ;; *) exit 1;; esac
case " $flags " in *' -I '*|*' -L '*) echo 'Empty include or library path.' >&2; exit 1;; esac
if grep -E '::|\$<|/workspace/|/tmp/' "$pc"; then
    echo 'Invalid target pkg-config metadata.' >&2; exit 1
fi
include=$("$pkg_config" --variable=includedir ompl)
case "$include" in */include/ompl-2.0) ;; *) echo 'Missing versioned OMPL header directory.' >&2; exit 1;; esac
printf '%s\n' "$flags" "$static"
echo 'Installed headless OMPL pkg-config metadata: PASS'
