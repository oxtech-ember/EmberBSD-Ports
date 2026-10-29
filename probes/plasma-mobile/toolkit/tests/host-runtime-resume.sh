#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Reject removal of an input from a previously recorded native runtime view.
set -eu
[ "$#" = 1 ] || { echo 'Usage: host-runtime-resume.sh DISTFILES' >&2; exit 2; }
: "${HOST_MACOSX_DEPLOYMENT_TARGET:?Set the selected Darwin deployment target}"
: "${HOST_SDK_SOURCE:?Set the SDK source}"
cross=$(CDPATH= cd -- "$(dirname -- "$0")/../cross" && pwd)
tmp=$(mktemp -d "${TMPDIR:-/tmp}/ember-qt-view-test.XXXXXXXX")
trap 'rm -rf "$tmp"' EXIT HUP INT TERM
mkdir "$tmp/view" "$tmp/work"
printf a > "$tmp/view/a.dylib"
printf b > "$tmp/view/b.dylib"
identity=$(shasum -a 256 "$tmp/view"/* | shasum -a 256 | cut -d ' ' -f 1)
{
    printf '%s  %s\n' 2987bc8a260733ebcec67eeda99d1da40488a40fb4493fda76e37a3a28ebd329 "$cross/build-host-tools.sh"
    shasum -a 256 "$tmp/view"/*
    printf 'profile=%s\nhost_package_prefix=%s\nhost_deployment_target=%s\nhost_runtime_view=%s\nhost_runtime_view_identity=%s\n' "${QT_HOST_TOOLS_PROFILE:-full}" "$HOST_PACKAGE_PREFIX" "$HOST_MACOSX_DEPLOYMENT_TARGET" "$tmp/view" "$identity"
} > "$tmp/work/inputs.txt"
rm "$tmp/view/b.dylib"
output=$(HOST_RUNTIME_VIEW="$tmp/view" RESUME=1 QT_HOST_TOOLS_PLAN_ONLY=1 "${HOST_SH:-/bin/sh}" "$cross/build-host-tools.sh" "$1" "$tmp/work" 2>&1) && { echo 'Changed runtime view accepted' >&2; exit 1; }
printf '%s\n' "$output" | grep -F -x 'Qt host resume: previous runtime entry changed: b.dylib' >/dev/null
echo 'Changed host runtime view rejected: PASS'
