#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
# Build, test and seal the cross LLVM metadata helper for MesaLib.
# Each step calls the existing Ruby script. The manifest hash is recorded
# outside the helper directory directly after the build.
set -eu
umask 022

[ "$#" -eq 6 ] || {
    echo 'Usage: sh scripts/build-llvm-config.sh LLVM_SOURCE TARGET_BUILD NATIVE_BUILD SYSROOT TARGET_PREFIX ABSOLUTE_WORK' >&2
    exit 2
}
for dir in "$@"; do
    case "$dir" in
        /*) ;;
        *) echo "Not an absolute path: $dir" >&2; exit 2 ;;
    esac
done
work=$6
ruby=${HOST_RUBY:-ruby}
cross=$(CDPATH= cd -- "$(dirname -- "$0")/../profiles/common-graphics/cross" && pwd)
mkdir -p "$work"

# 1. Build the helper from the target and native LLVM build trees.
if [ ! -f "$work/manifest.sha256" ]; then
    rm -rf "$work/helper"
    "$ruby" "$cross/build-llvm-config.rb" "$1" "$2" "$3" "$4" "$5" "$work/helper"
    shasum -a 256 "$work/helper/inputs.sha256" | cut -d ' ' -f 1 > "$work/manifest.sha256"
fi

# 2. Run the acceptance test on the unchanged helper.
"$ruby" "$cross/test-llvm-config.rb" "$work/helper"

# 3. Seal the accepted helper with the recorded manifest hash.
if [ ! -d "$work/sealed" ]; then
    "$ruby" "$cross/seal-llvm-config.rb" "$work/helper" \
        "$(cat "$work/manifest.sha256")" "$work/sealed"
fi
echo "Set EMBERBSD_GRAPHICS_LLVM_CONFIG=$work/sealed/bin/llvm-config in the cross MAKECONF."
