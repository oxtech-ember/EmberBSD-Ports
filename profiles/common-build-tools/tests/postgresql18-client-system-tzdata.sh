#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
#
# Check that databases/postgresql18-client uses the NetBSD base time-zone
# data. Without it a cross build stopped in configure: "When
# cross-compiling, either use the option --with-system-tzdata to use
# existing time-zone data, or set the environment variable ZIC".
#
# Usage: BMAKE=bmake postgresql18-client-system-tzdata.sh PKGSRC MAKECONF
# MAKECONF is the mk.conf of a NetBSD cross build.

set -eu
[ $# -eq 2 ] || { echo "usage: BMAKE=bmake $0 PKGSRC MAKECONF" >&2; exit 2; }
pkgsrc=$1
makeconf=$2
bmake=${BMAKE:-bmake}

arg=$(MAKECONF=$makeconf "$bmake" -C "$pkgsrc/databases/postgresql18-client" \
    MAKECONF="$makeconf" -V '${CONFIGURE_ARGS:M--with-system-tzdata=*}')
if [ "$arg" != "--with-system-tzdata=/usr/share/zoneinfo" ]; then
	echo "FAIL: the NetBSD build needs a build-machine zic ('$arg')"
	exit 1
fi
echo "PASS: the NetBSD client uses /usr/share/zoneinfo"
