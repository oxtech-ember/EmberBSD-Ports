#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), inspect the actual package generator selection.
set -eu
[ "$#" = 3 ] || { echo 'Usage: libsecret-tools.sh PKGSRC CROSS_MAKECONF NEW_WORK' >&2; exit 2; }
pkgsrc=$1 config=$2 work=$3
: "${BMAKE:=bmake}"
mkdir "$work"
for mode in yes no; do
    for variable in PKGNAME PKG_FAIL_REASON MESON_BINARIES MESON_NATIVE_ARGS BUILD_DEPENDS TOOL_DEPENDS BUILDLINK_API_DEPENDS.vala BUILDLINK_API_DEPENDS.py-gi-docgen MESON_ARGS; do
        MAKECONF="$config" "$BMAKE" -C "$pkgsrc/security/libsecret" USE_CROSS_COMPILE="$mode" -V "\${$variable}" > "$work/$mode-$variable.txt"
    done
    grep -qx libsecret-0.21.8.2 "$work/$mode-PKGNAME.txt"
    [ ! -s "$work/$mode-PKG_FAIL_REASON.txt" ] || [ "$(cat "$work/$mode-PKG_FAIL_REASON.txt")" = '' ]
    ! grep -E -- '-D(introspection|vapi|gtk_doc)=false' "$work/$mode-MESON_ARGS.txt"
done
grep -q g-ir-scanner "$work/yes-MESON_BINARIES.txt"
grep -q vapigen "$work/yes-MESON_BINARIES.txt"
grep -q gi-docgen "$work/yes-MESON_BINARIES.txt"
grep -q glib2-introspection "$work/yes-BUILD_DEPENDS.txt"
grep -q vala "$work/no-BUILDLINK_API_DEPENDS.vala.txt"
grep -q gi-docgen "$work/no-BUILDLINK_API_DEPENDS.py-gi-docgen.txt"
for variable in EMBERBSD_GI_DOCGEN_HOST EMBERBSD_VALA_HOST; do
    MAKECONF="$config" "$BMAKE" -C "$pkgsrc/security/libsecret" USE_CROSS_COMPILE=yes "$variable=/nonexistent-ember-generator" -V '${PKG_FAIL_REASON}' > "$work/missing-$variable.txt"
    grep -q "$variable must name" "$work/missing-$variable.txt"
done
echo 'PASS: actual libsecret cross/native generators, complete options and absent-provider rejection'
