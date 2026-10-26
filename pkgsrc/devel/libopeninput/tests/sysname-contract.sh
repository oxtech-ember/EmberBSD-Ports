#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Extract and execute the production sysname getter with a minimal device stub.
set -eu

if [ "$#" -ne 2 ]; then
	echo "usage: $0 SOURCE C_COMPILER|-" >&2
	exit 2
fi

source_file=$1
compiler=$2
work=$(mktemp -d "${TMPDIR:-/tmp}/libopeninput-sysname.XXXXXX")
trap 'rm -rf "$work"' EXIT HUP INT TERM

cat > "$work/contract.c" <<'EOF'
#include <string.h>

#define LIBINPUT_EXPORT
struct libinput_device {
	const char *devname;
};
EOF

awk '
/^LIBINPUT_EXPORT const char \*$/ { declaration = $0; next }
/^libinput_device_get_sysname\(struct libinput_device \*device\)$/ {
	if (!declaration)
		exit 1
	print declaration
	print
	inside = 1
	next
}
inside {
	print
	if ($0 == "}") {
		found = 1
		exit
	}
}
END { if (!found) exit 1 }
' "$source_file" >> "$work/contract.c" || {
	echo "could not extract libinput_device_get_sysname" >&2
	exit 1
}

cat >> "$work/contract.c" <<'EOF'

int
main(void)
{
	struct libinput_device path_device = { "/dev/wsmouse1" };
	struct libinput_device plain_device = { "keyboard0" };
	const char *path_name = libinput_device_get_sysname(&path_device);
	const char *plain_name = libinput_device_get_sysname(&plain_device);

	if (strcmp(path_name, "wsmouse1") != 0 ||
	    path_name != path_device.devname + 5)
		return 1;
	if (strcmp(plain_name, "keyboard0") != 0 ||
	    plain_name != plain_device.devname)
		return 2;
	return 0;
}
EOF

if [ "$compiler" != "-" ]; then
	"$compiler" -std=c11 -Wall -Wextra -Werror -fanalyzer \
		-o "$work/sysname-contract" "$work/contract.c"
fi
if [ -n "${CPPCHECK:-}" ]; then
	"$CPPCHECK" --enable=warning --error-exitcode=1 --std=c11 \
		"$work/contract.c"
fi
if [ "$compiler" != "-" ]; then
	"$work/sysname-contract"
else
	[ -n "${CPPCHECK:-}" ] || {
		echo "provide a compiler or CPPCHECK" >&2
		exit 2
	}
fi
if [ "$compiler" != "-" ]; then
	echo "PASS: sysname is the device basename and remains backed by devname storage"
else
	echo "PASS: Cppcheck analyzed the extracted production getter"
fi
