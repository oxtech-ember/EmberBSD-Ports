#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; AI-assisted cross-recipe argument and prerequisite regressions.
set -eu
usage() { echo 'Usage: build-modes.sh [--target aarch64|amd64] [NETBSD_TOOLDIR]' >&2; exit 2; }
here=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd -P)
. "$here/target-options.sh"
[ "$#" -le 1 ] || usage
bootstrap=${1:-}
unset EMBER_HOST_MATH_PREFIX
work=$(mktemp -d "${TMPDIR:-/tmp}/ember-gcc-modes.XXXXXXXX")
trap 'rm -rf "$work"' EXIT
trap 'exit 130' INT
trap 'exit 143' HUP TERM
if [ -z "$bootstrap" ]; then
    # No build command runs in these early-rejection fixtures.
    bootstrap=$work/bootstrap
    mkdir -p "$bootstrap/bin"
    printf '#!/bin/sh\nexit 99\n' > "$bootstrap/bin/nbgmake"
    chmod +x "$bootstrap/bin/nbgmake"
    for tool in ar as elfedit ld nm objcopy objdump ranlib readelf size strings strip; do
        cp "$bootstrap/bin/nbgmake" "$bootstrap/bin/$triplet-$tool"
    done
fi
[ -x "$bootstrap/bin/nbgmake" ] || { echo 'Provide bootstrap GNU make and target binutils.' >&2; exit 2; }

reject() {
    expected=$1; shift
    status=0
    CROSS_JOBS=${TEST_CROSS_JOBS:-1} sh "$here/build.sh" --target "$target" "$@" > "$work/result.log" 2>&1 || status=$?
    [ "$status" -ne 0 ] && grep -Fq "$expected" "$work/result.log" || {
        cat "$work/result.log" >&2
        echo "Wrong rejection; expected: $expected" >&2
        exit 1
    }
    [ ! -e "$work/new" ] || { echo 'Invalid inputs created NEW_WORK.' >&2; exit 1; }
}

reject 'Target headers missing.' "$work/pkgsrc" "$work/archive" "$work/sysroot" "$work/tools" "$work/new"
reject 'Target headers missing.' "$work/pkgsrc" "$work/archive" "$work/sysroot" "$work/tools" "$work/math" "$work/new"
reject 'Bootstrap GNU make missing.' --kernel "$work/pkgsrc" "$work/archive" "$work/tools" "$work/new"
reject 'Bootstrap GNU make missing.' --kernel "$work/pkgsrc" "$work/archive" "$work/tools" "$work/math" "$work/new"
reject 'Usage:' --kernel "$work/pkgsrc" "$work/archive" "$work/new"
reject 'Usage:' --kernel "$work/pkgsrc" "$work/archive" "$work/sysroot" "$work/tools" "$work/math" "$work/new"
reject 'Unknown build mode.' --unknown "$work/pkgsrc" "$work/archive" "$work/tools" "$work/new"
reject 'Absolute paths required.' --kernel relative "$work/archive" "$work/tools" "$work/new"
(TEST_CROSS_JOBS=0 reject 'CROSS_JOBS must be positive.' --kernel "$work/pkgsrc" "$work/archive" "$work/tools" "$work/new")

# Use the selected bootstrap layout for later prerequisite checks. An empty
# archive must fail checksum validation before any build command runs.
: > "$work/archive"
reject 'GCC archive SHA256 mismatch.' --kernel "$work/pkgsrc" "$work/archive" "$bootstrap" "$work/new"
reject 'Host libgmp.a missing.' --kernel "$work/pkgsrc" "$work/archive" "$bootstrap" "$work/math" "$work/new"
(EMBER_HOST_MATH_PREFIX="$work/math" reject 'Host libgmp.a missing.' --kernel "$work/pkgsrc" "$work/archive" "$bootstrap" "$work/new")

mkdir "$work/new"
printf preserve > "$work/new/sentinel"
if CROSS_JOBS=1 sh "$here/build.sh" --target "$target" --kernel "$work/pkgsrc" "$work/archive" "$work/tools" "$work/new" > "$work/result.log" 2>&1; then
    exit 1
fi
grep -Fq 'NEW_WORK already exists.' "$work/result.log"
[ "$(cat "$work/new/sentinel")" = preserve ]
echo 'PASS: application CLI, kernel CLI, mode/path/math/archive rejection and existing-work preservation'
