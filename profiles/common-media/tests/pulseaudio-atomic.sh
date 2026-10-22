#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). PulseAudio and its consumers select native
# atomics from the target sysroot, not from the build host.
set -eu
[ "$#" = 2 ] || { echo 'Usage: pulseaudio-atomic.sh PKGSRC NEW_WORK' >&2; exit 2; }
: "${BMAKE:?Set native bmake}" "${MAKECONF:?Set cross MAKECONF}"
tree=$(CDPATH= cd -- "$1" && pwd)
mkdir "$2"
work=$(CDPATH= cd -- "$2" && pwd)
sysroot=$("$BMAKE" -C "$tree/audio/pulseaudio" -V '${CROSS_DESTDIR}')
[ -f "$sysroot/usr/include/sys/atomic.h" ]
# Qt Multimedia includes the PulseAudio buildlink3.mk.
for recipe in audio/pulseaudio multimedia/qt6-qtmultimedia; do
	name=$(echo "$recipe" | tr / _)
	"$BMAKE" -C "$tree/$recipe" -V '${BUILDLINK_TREE}' | tr ' ' '\n' > "$work/$name.tree"
	if grep -x libatomic_ops "$work/$name.tree"; then exit 1; fi
done
grep -qx pulseaudio "$work/multimedia_qt6-qtmultimedia.tree"
echo 'PASS: PulseAudio and Qt Multimedia use the target sysroot atomic header'
