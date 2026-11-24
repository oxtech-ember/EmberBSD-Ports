#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Check the scan code mappings of the systemd hwdb for PC keyboards:
# the DMI modalias, the key names, the record and property syntax, the
# file order, and the installed files for the MSI Vector 17 HX AI and
# other systems.  The XT map gives KEY_F24 for scan code 0x76: laptops
# send Control+Super+F24 for the touchpad toggle.
# Usage: sh tests/keyboard-hwdb.sh PATCHED_WRKSRC HWDB_DIR C_COMPILER
set -eu

if [ "$#" -ne 3 ]; then
	echo "usage: $0 WRKSRC HWDB_DIR C_COMPILER" >&2
	exit 2
fi

wrksrc=$1
hwdb=$2
compiler=$3
files=$(CDPATH= cd -- "$(dirname -- "$0")/../files" && pwd)
work=$(mktemp -d "${TMPDIR:-/tmp}/libopeninput-hwdb.XXXXXX")
trap 'rm -rf "$work"' EXIT HUP INT TERM

awk '
/^static uint32_t wsXtMap\[\] = \{$/ { inside = 1; next }
inside && /^\};$/ { exit }
inside && /\/\* 118 \*\/ KEY_F24,/ { found = 1 }
END { if (!found) exit 1 }
' "$wrksrc/src/wskbdmap.c" || {
	echo "XT map entry 118 is not KEY_F24" >&2
	exit 1
}
for name in 60-keyboard.hwdb 70-emberbsd-keyboard.hwdb; do
	test -s "$hwdb/$name" || {
		echo "$hwdb/$name is missing" >&2
		exit 1
	}
done

awk -f "$files/keynames.awk" \
    "$wrksrc/include/linux/freebsd/input-event-codes.h" \
    > "$work/wskbd-keynames.h"

# Records for the syntax: the order of the files, a match line after
# the properties, comments, '!', the AT keyboard name and other devices.
mkdir "$work/fixture"
cat > "$work/fixture/10-first.hwdb" <<'EOF'
# A comment line.
evdev:atkbd:dmi:*:svnTestVendor:pnBoard[12]:*
 KEYBOARD_KEY_81=mute                                   # comment
 KEYBOARD_KEY_82=!volumeup
 KEYBOARD_KEY_83=nosuchkey
 KEYBOARD_KEY_1ff=mute
 KEYBOARD_KEY_8A=btn_left
evdev:atkbd:dmi:*:svnTestVendor:pnBoard2:*
 KEYBOARD_KEY_84=f20

evdev:name:AT Translated Set 2 keyboard:dmi:*:svnTestVendor:*
 KEYBOARD_KEY_85=bluetooth

evdev:input:b0003v1234p5678*
evdev:name:Other keyboard:dmi:*
 KEYBOARD_KEY_86=mute

 KEYBOARD_KEY_87=mute
EOF
cat > "$work/fixture/20-second.hwdb" <<'EOF'
evdev:atkbd:dmi:*:svnTestVendor:*
 KEYBOARD_KEY_81=micmute
EOF
cat > "$work/fixture/30-other.txt" <<'EOF'
evdev:atkbd:*
 KEYBOARD_KEY_88=mute
EOF

cat > "$work/contract.c" <<'EOF'
#include <stdio.h>
#include <string.h>

#include "input-event-codes.h"
#include "wskbd-hwdb.h"

#define SIZE 256

static uint32_t map[SIZE];

static void
reset(void)
{
	size_t i;

	for (i = 0; i < SIZE; i++)
		map[i] = 1000 + i;
}

static int
same(size_t from, size_t to, const size_t *changed, size_t nchanged)
{
	size_t i, j;

	for (i = from; i < to; i++) {
		for (j = 0; j < nchanged; j++)
			if (changed[j] == i)
				break;
		if (j == nchanged && map[i] != 1000 + i)
			return 0;
	}
	return 1;
}

#define CHECK(n, e) do {						\
	if (!(e)) {							\
		fprintf(stderr, "check %d failed: %s\n", n, #e);	\
		return n;						\
	}								\
} while (0)

int
main(int argc, char **argv)
{
	struct wskbd_hwdb_dmi msi = {
		.bvn = "American Megatrends International, LLC.",
		.bvr = "E17S1IMS.10A", .bd = "05/12/2025",
		.svn = "Micro-Star International Co., Ltd.",
		.pn = "Vector 17 HX AI A2XWJG", .pvr = "REV:1.0",
		.rvn = "Micro-Star International Co., Ltd.", .rn = "MS-17S1",
		.rvr = "REV:1.0", .cvn = "Micro-Star International Co., Ltd.",
		.cvr = "N/A",
	};
	struct wskbd_hwdb_dmi dmi = {
		.bvn = "Test BIOS", .svn = "TestVendor", .pn = "Board2",
	};
	const size_t board2[] = { 0x81, 0x82, 0x84, 0x85, 0x8a };
	char modalias[1024], small[24];
	const char *dir = argv[1], *fixture = argv[2];

	CHECK(1, argc == 3);
	CHECK(2, wskbd_hwdb_modalias(&msi, modalias, sizeof(modalias)) == 0);
	CHECK(3, strcmp(modalias, "dmi:"
	    "bvnAmericanMegatrendsInternational,LLC.:bvrE17S1IMS.10A:"
	    "bd05/12/2025:svnMicro-StarInternationalCo.,Ltd.:"
	    "pnVector17HXAIA2XWJG:pvrREV1.0:"
	    "rvnMicro-StarInternationalCo.,Ltd.:rnMS-17S1:rvrREV1.0:"
	    "cvnMicro-StarInternationalCo.,Ltd.:cvrN/A:") == 0);
	CHECK(4, wskbd_hwdb_modalias(&msi, small, sizeof(small)) == -1);

	CHECK(5, wskbd_hwdb_key("micmute") == KEY_MICMUTE);
	CHECK(6, wskbd_hwdb_key("touchpad_toggle") == KEY_TOUCHPAD_TOGGLE);
	CHECK(7, wskbd_hwdb_key("btn_left") == BTN_LEFT);
	CHECK(8, wskbd_hwdb_key("reserved") == KEY_RESERVED);
	CHECK(9, wskbd_hwdb_key("nosuchkey") == -1);
	CHECK(10, wskbd_hwdb_key("key_mute") == -1);

	/* The syntax of the fixture records. */
	CHECK(11, wskbd_hwdb_modalias(&dmi, modalias, sizeof(modalias)) == 0);
	reset();
	CHECK(12, wskbd_hwdb_apply(fixture, modalias, map, SIZE) == 6);
	CHECK(13, map[0x81] == KEY_MICMUTE);	/* the later file */
	CHECK(14, map[0x82] == KEY_VOLUMEUP && map[0x8a] == BTN_LEFT);
	CHECK(15, map[0x84] == KEY_F20 && map[0x85] == KEY_BLUETOOTH);
	CHECK(16, same(0, SIZE, board2, 5));
	dmi.pn = "Board3";
	CHECK(17, wskbd_hwdb_modalias(&dmi, modalias, sizeof(modalias)) == 0);
	reset();
	CHECK(18, wskbd_hwdb_apply(fixture, modalias, map, SIZE) == 2);
	CHECK(19, map[0x81] == KEY_MICMUTE && map[0x85] == KEY_BLUETOOTH);
	CHECK(20, map[0x82] == 1000 + 0x82 && map[0x84] == 1000 + 0x84);
	/* A match line after the properties starts another record. */
	dmi.pn = "Board1";
	CHECK(34, wskbd_hwdb_modalias(&dmi, modalias, sizeof(modalias)) == 0);
	reset();
	CHECK(35, wskbd_hwdb_apply(fixture, modalias, map, SIZE) == 5);
	CHECK(36, map[0x82] == KEY_VOLUMEUP && map[0x84] == 1000 + 0x84);
	reset();
	CHECK(21, wskbd_hwdb_apply("/nonexistent", modalias, map, SIZE) == 0);

	/* The installed files on the MSI Vector 17 HX AI. */
	CHECK(22, wskbd_hwdb_modalias(&msi, modalias, sizeof(modalias)) == 0);
	reset();
	CHECK(23, wskbd_hwdb_apply(dir, modalias, map, SIZE) >= 19);
	CHECK(24, map[0x91] == KEY_CONFIG && map[0xd7] == KEY_BLUETOOTH);
	/* 70-emberbsd-keyboard.hwdb keeps KEY_F20 for Fn+F5. */
	CHECK(25, map[0xf1] == KEY_F20);
	CHECK(26, map[0xe4] == KEY_TOUCHPAD_TOGGLE && map[0xa0] == KEY_MUTE);
	/* The vendor codes are escaped: the plain codes keep the XT map. */
	CHECK(27, same(0, 0x80, NULL, 0));

	/* Only the system vendor and product known (OpenBSD): the other
	 * fields are empty, and the patterns still match. */
	CHECK(37, wskbd_hwdb_modalias(&(struct wskbd_hwdb_dmi){
	    .svn = msi.svn, .pn = msi.pn }, modalias, sizeof(modalias)) == 0);
	CHECK(38, strcmp(modalias, "dmi:bvn:bvr:bd:"
	    "svnMicro-StarInternationalCo.,Ltd.:pnVector17HXAIA2XWJG:"
	    "pvr:rvn:rn:rvr:cvn:cvr:") == 0);
	reset();
	CHECK(39, wskbd_hwdb_apply(dir, modalias, map, SIZE) >= 19);
	CHECK(40, map[0xd7] == KEY_BLUETOOTH && map[0xf1] == KEY_F20);

	/* Another MSI model has no Fn+F6 mapping. */
	msi.pn = "Katana 15 B13V";
	CHECK(28, wskbd_hwdb_modalias(&msi, modalias, sizeof(modalias)) == 0);
	reset();
	CHECK(29, wskbd_hwdb_apply(dir, modalias, map, SIZE) > 0);
	CHECK(30, map[0xd7] == 1000 + 0xd7 && map[0xf1] == KEY_F20);

	/* A system without records keeps the XT map. */
	dmi.svn = "EmberBSD Test Vendor";
	dmi.pn = "Model 1";
	CHECK(31, wskbd_hwdb_modalias(&dmi, modalias, sizeof(modalias)) == 0);
	reset();
	CHECK(32, wskbd_hwdb_apply(dir, modalias, map, SIZE) == 0);
	CHECK(33, same(0, SIZE, NULL, 0));
	return 0;
}
EOF

"$compiler" -std=c11 -D_POSIX_C_SOURCE=200809L -Wall -Wextra -Werror \
    -I"$work" -I"$wrksrc/src" -I"$wrksrc/include/linux/freebsd" \
    -o "$work/keyboard-hwdb" "$work/contract.c" "$wrksrc/src/wskbd-hwdb.c"
"$work/keyboard-hwdb" "$hwdb" "$work/fixture"
echo "keyboard hwdb: ok"
