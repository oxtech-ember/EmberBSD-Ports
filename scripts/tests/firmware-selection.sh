#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; AI-assisted source export and firmware selection regression.
set -eu
[ "$#" -eq 1 ] || { echo "Usage: $0 NEW_WORK" >&2; exit 2; }
root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
mkdir "$1"
work=$(CDPATH= cd -- "$1" && pwd)

if EMBERBSD_FIRMWARE_TOOLCHAIN=maybe sh "$root/scripts/prepare-pkgsrc.sh" \
    "$work/invalid" common-media > "$work/invalid.log" 2>&1; then exit 1; fi
grep -F 'EMBERBSD_FIRMWARE_TOOLCHAIN must be yes or no.' "$work/invalid.log" >/dev/null
[ ! -e "$work/invalid" ]

# An incomplete opt-in must fail before Git archive or destination creation.
fixture=$work/fixture
mkdir -p "$fixture/scripts" "$fixture/profiles/development-toolchain"
cp "$root/scripts/prepare-pkgsrc.sh" "$fixture/scripts/"
cp -R "$root/profiles/development-toolchain/recipes" "$fixture/profiles/development-toolchain/"
rm -f "$fixture/profiles/development-toolchain/recipes/sysutils/dtc/Makefile"
if EMBERBSD_FIRMWARE_TOOLCHAIN=yes sh "$fixture/scripts/prepare-pkgsrc.sh" \
    "$work/incomplete" common-media > "$work/incomplete.log" 2>&1; then exit 1; fi
grep -F 'Incomplete GCC16 firmware toolchain: sysutils/dtc/Makefile.' "$work/incomplete.log" >/dev/null
[ ! -e "$work/incomplete" ]
if EMBERBSD_FIRMWARE_TOOLCHAIN=yes sh "$root/scripts/prepare-pkgsrc.sh" \
    "$work/no-profile" > "$work/no-profile.log" 2>&1; then exit 1; fi
grep -F 'The firmware toolchain requires a development or common profile.' "$work/no-profile.log" >/dev/null
[ ! -e "$work/no-profile" ]

(unset EMBERBSD_FIRMWARE_TOOLCHAIN
 sh "$root/scripts/prepare-pkgsrc.sh" "$work/pkgsrc" common-media) > "$work/export.log" 2>&1
for recipe in devel/gmake sysutils/dtc; do
    diff -qr "$root/upstream/pkgsrc/$recipe" "$work/pkgsrc/$recipe"
done
diff -qr "$root/upstream/pkgsrc/devel/gmake" \
    "$root/profiles/development-toolchain/recipes/devel/gmake"
grep -Fx 'profile=common-media' "$work/pkgsrc/EMBERBSD-PKGSRC-CONFIG" >/dev/null
grep -Fx 'firmware_toolchain=no' "$work/pkgsrc/EMBERBSD-PKGSRC-CONFIG" >/dev/null
grep -Eq '^GCC16_DIST_VERSION:=[[:space:]]*16[.]2[.]0' "$work/pkgsrc/lang/gcc16/version.mk"
echo 'PASS: common-media exports complete canonical providers and GCC16; invalid and incomplete firmware selections create no destination'
