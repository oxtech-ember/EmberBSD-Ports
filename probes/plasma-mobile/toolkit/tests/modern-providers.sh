#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Test the production provider policy.
set -eu
[ "$#" = 2 ] || { echo "Usage: $0 TOOLKIT_MK_CONF NEW_OUTPUT" >&2; exit 2; }
profile=$(CDPATH= cd -- "$(dirname -- "$1")" && pwd)/$(basename -- "$1")
bmake=${BMAKE:-bmake}
command -v "$bmake" >/dev/null
mkdir "$2"
work=$(CDPATH= cd -- "$2" && pwd)
cat > "$work/Makefile" <<'MAKE'
BSD_PKG_MK= yes
EMBERBSD_COMMON_TOOLS= yes
EMBERBSD_COMMON_GRAPHICS= yes
EMBERBSD_COMMON_MEDIA= yes
.include "${PROFILE}"
all:
	@test -z '${PKG_FAIL_REASON:U}' || { printf '%s\n' '${PKG_FAIL_REASON}'; exit 1; }
MAKE
for mode in yes no; do
    for path in x11/gtk2 devel/SDL devel/SDL2; do
        if "$bmake" -r -f "$work/Makefile" PROFILE="$profile" \
            PKGPATH="$path" USE_CROSS_COMPILE="$mode" > "$work/${path##*/}-$mode.log" 2>&1; then
            echo "FAIL: obsolete provider accepted: $path ($mode)" >&2
            exit 1
        fi
        grep -q 'port its consumer to the supported common stack' "$work/${path##*/}-$mode.log"
    done
    for path in devel/SDL3 x11/qt6-qtbase x11/plasma6-plasma-desktop; do
        "$bmake" -r -f "$work/Makefile" PROFILE="$profile" \
            PKGPATH="$path" USE_CROSS_COMPILE="$mode" > "$work/${path##*/}-$mode.log" 2>&1
    done
done
echo 'PASS: obsolete providers rejected and current providers accepted in native/cross policy'
