#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Extract the vendor scan code table of src/wskbdmap.c and check it:
# the Micro-Star codes (vendor in any case) of Fn+F5, Fn+F6 and Fn+F7
# give evdev keys, other vendors keep the plain XT map.  Scan code 0x76
# (wscons key 118) of the XT map is F24 of scan code set 1: laptops send
# Control+Super+F24 for the touchpad toggle.
# Usage: sh tests/vendor-scan-codes.sh PATCHED_WSKBDMAP_C C_COMPILER|-
set -eu

if [ "$#" -ne 2 ]; then
	echo "usage: $0 SOURCE C_COMPILER|-" >&2
	exit 2
fi

source_file=$1
compiler=$2
work=$(mktemp -d "${TMPDIR:-/tmp}/libopeninput-scancodes.XXXXXX")
trap 'rm -rf "$work"' EXIT HUP INT TERM

awk '
/^static uint32_t wsXtMap\[\] = \{$/ { inside = 1; next }
inside && /^\};$/ { exit }
inside && /\/\* 118 \*\/ KEY_F24,/ { found = 1 }
END { if (!found) exit 1 }
' "$source_file" || {
	echo "XT map entry 118 is not KEY_F24" >&2
	exit 1
}

cat > "$work/contract.c" <<'EOF'
#include <stddef.h>
#include <stdint.h>
#include <string.h>
#include <strings.h>

#define KEY_RESERVED	0
#define KEY_CONFIG	171
#define KEY_F20		190
#define KEY_BLUETOOTH	237
#define KEY_UNKNOWN	240

struct TransMapRec {
	int begin;
	int end;
	uint32_t *map;
};

/* XT map stub: the real map has 238 entries. */
#define WS_XT_MAP_SIZE 238
static uint32_t wsXtMap[WS_XT_MAP_SIZE];
EOF

awk '
/^struct wskbd_xt_quirk \{$/ { inside = 1 }
inside { print }
inside && /^wskbd_xt_quirk_map\(/ { infunc = 1 }
infunc && $0 == "}" { found = 1; exit }
END { if (!found) exit 1 }
' "$source_file" >> "$work/contract.c" || {
	echo "could not extract wskbd_xt_quirk_map" >&2
	exit 1
}

cat >> "$work/contract.c" <<'EOF'

int
main(void)
{
	uint32_t map[WS_XT_QUIRK_MAP_SIZE];
	size_t i;

	(void)wsXtQuirk;
	for (i = 0; i < WS_XT_MAP_SIZE; i++)
		wsXtMap[i] = (uint32_t)(1000 + i);

	if (wskbd_xt_quirk_map("Micro-Star International Co., Ltd.",
	    map, WS_XT_QUIRK_MAP_SIZE) != 3)
		return 1;
	if (map[0x91] != KEY_CONFIG || map[0xd7] != KEY_BLUETOOTH ||
	    map[0xf1] != KEY_F20)
		return 2;
	/* Other codes keep the XT map; codes past it stay unknown. */
	if (map[0xa0] != 1000 + 0xa0 || map[237] != 1000 + 237 ||
	    map[238] != KEY_UNKNOWN || map[255] != KEY_UNKNOWN)
		return 3;

	if (wskbd_xt_quirk_map("MICRO-STAR INTERNATIONAL CO., LTD",
	    map, WS_XT_QUIRK_MAP_SIZE) != 3 || map[0xf1] != KEY_F20)
		return 7;
	if (wskbd_xt_quirk_map("Notebook", map, WS_XT_QUIRK_MAP_SIZE) != 0)
		return 4;
	if (map[0x91] != 1000 + 0x91 || map[0xd7] != 1000 + 0xd7 ||
	    map[0xf1] != KEY_UNKNOWN)
		return 5;
	if (wskbd_xt_quirk_map(NULL, map, WS_XT_QUIRK_MAP_SIZE) != 0)
		return 6;
	return 0;
}
EOF

if [ "$compiler" != "-" ]; then
	"$compiler" -std=c11 -Wall -Wextra -Werror \
		-o "$work/vendor-scan-codes" "$work/contract.c"
fi
if [ -n "${CPPCHECK:-}" ]; then
	"$CPPCHECK" --enable=warning --error-exitcode=1 --std=c11 \
		"$work/contract.c"
fi
if [ "$compiler" != "-" ]; then
	"$work/vendor-scan-codes"
else
	[ -n "${CPPCHECK:-}" ] || {
		echo "provide a compiler or CPPCHECK" >&2
		exit 2
	}
fi
echo "vendor scan codes: ok"
