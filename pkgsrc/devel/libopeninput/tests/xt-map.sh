#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Run wskbd_xt_map() of the patched src/wskbdmap.c with a controlled DMI
# and hwdb directories: the NetBSD and OpenBSD sysctl paths, the BIOS
# date form, the order of the package and local files, the map past the
# XT codes, and the selection once for each process.
# Usage: sh tests/xt-map.sh PATCHED_WRKSRC HWDB_DIR C_COMPILER
set -eu

if [ "$#" -ne 3 ]; then
	echo "usage: $0 WRKSRC HWDB_DIR C_COMPILER" >&2
	exit 2
fi

wrksrc=$1
hwdb=$2
compiler=$3
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
files=$here/../files
work=$(mktemp -d "${TMPDIR:-/tmp}/libopeninput-xt-map.XXXXXX")
trap 'rm -rf "$work"' EXIT HUP INT TERM

# The XT map and the code from WS_XT_HWDB_MAP_SIZE to wskbd_xt_map().
awk '
/^static uint32_t wsXtMap\[\] = \{$/ { copy = 1 }
copy && /^static void$/ { exit }
copy { print }
' "$wrksrc/src/wskbdmap.c" > "$work/xt-map-extract.h"
grep -q '^wskbd_xt_map(struct libinput \*libinput)$' "$work/xt-map-extract.h" || {
	echo "no wskbd_xt_map() in $wrksrc/src/wskbdmap.c" >&2
	exit 1
}
awk -f "$files/keynames.awk" \
    "$wrksrc/include/linux/freebsd/input-event-codes.h" \
    > "$work/wskbd-keynames.h"

mkdir "$work/empty" "$work/etc"
cat > "$work/etc/90-local.hwdb" <<'EOF'
evdev:atkbd:dmi:bvn*:bvr*:bd*:svnMicro-Star*:pnVector17HXAI*:*
 KEYBOARD_KEY_d7=mute
 KEYBOARD_KEY_f0=f13
EOF

for variant in netbsd openbsd; do
	flags=
	[ "$variant" = netbsd ] || flags=-DOPENBSD_SYSCTL
	"$compiler" -std=c11 -D_POSIX_C_SOURCE=200809L -Wall -Wextra -Werror \
	    $flags -I"$work" -I"$wrksrc/src" -I"$wrksrc/include/linux/freebsd" \
	    -o "$work/xt-map-$variant" "$here/xt-map.c" \
	    "$wrksrc/src/wskbd-hwdb.c"
done

run() {
	"$work/xt-map-$1" "$2" "$3" "$4"
}
run netbsd msi "$hwdb" "$work/empty"
run netbsd dated "$hwdb" "$work/empty"
run netbsd override "$hwdb" "$work/etc"
run netbsd etc-only "$work/empty" "$work/etc"
run netbsd other "$hwdb" "$work/etc"
run netbsd none "$hwdb" "$work/etc"
run openbsd openbsd "$hwdb" /nonexistent
echo "xt map: ok"
