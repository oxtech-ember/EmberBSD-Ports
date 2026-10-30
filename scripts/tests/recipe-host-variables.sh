#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Recipes take build-host programs from native
# TOOL_DEPENDS packages, not from EMBERBSD_*HOST* path settings. The names
# below are the settings that remain; the list may only shrink. Convert a
# user to a native package and delete its name here; never add a name.
# Usage: recipe-host-variables.sh [PKGSRC_OVERLAY]
set -eu
[ "$#" -le 1 ] || { echo 'Usage: recipe-host-variables.sh [PKGSRC_OVERLAY]' >&2; exit 2; }
root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
tree=${1:-$root/pkgsrc}
[ -d "$tree" ] || { echo "No recipe tree: $tree" >&2; exit 2; }
allowed='EMBERBSD_CLANG_HOST_PERL
EMBERBSD_CROSS_HOST_PREFIX
EMBERBSD_HOST_COMPILER_FAMILY
EMBERBSD_HOST_PREFIX
EMBERBSD_HOST_PYTHON
EMBERBSD_LLVM_LIBC_HOST_PREFIX
EMBERBSD_PERL_HOST_GENERATE
EMBERBSD_PERL_HOST_MINIPERL
EMBERBSD_PERL_HOST_PYTHON
EMBERBSD_PERL_TARGET_HOST
EMBERBSD_QT_HOST_LIBEXECS
EMBERBSD_QT_HOST_PATH
EMBERBSD_UNDICI_HOST_PREFIX
EMBERBSD_WASI_HOST_PREFIX'
# Lower this number with every removed name; it guards against additions.
max=14
[ "$(printf '%s\n' "$allowed" | wc -l | tr -d ' ')" -le "$max" ] ||
    { echo 'FAIL: the allowed EMBERBSD_*HOST* list grew' >&2; exit 1; }
found=$(grep -rhoE 'EMBERBSD_[A-Z0-9_]*HOST[A-Z0-9_]*' "$tree" | sort -u)
status=0
for name in $found; do
    printf '%s\n' "$allowed" | grep -Fqx "$name" && continue
    echo "FAIL: new build-host path setting $name; add a native TOOL_DEPENDS package instead:" >&2
    grep -rlF "$name" "$tree" | sed 's/^/  /' >&2
    status=1
done
for name in $allowed; do
    printf '%s\n' "$found" | grep -Fqx "$name" && continue
    echo "FAIL: $name is no longer used; remove it from the allowed list and lower max" >&2
    status=1
done
[ "$status" = 0 ] || exit 1
echo "PASS: recipes use only the $max remaining EMBERBSD_*HOST* settings"
