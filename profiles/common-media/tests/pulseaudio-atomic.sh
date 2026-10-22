#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). PulseAudio consumers select native atomics
# from the target sysroot and link libpulse with its private libpulsecommon.
set -eu
[ "$#" = 2 ] || { echo 'Usage: pulseaudio-atomic.sh PKGSRC NEW_WORK' >&2; exit 2; }
: "${BMAKE:?Set native bmake}" "${MAKECONF:?Set cross MAKECONF}"
tree=$(CDPATH= cd -- "$1" && pwd)
mkdir "$2"
work=$(CDPATH= cd -- "$2" && pwd)
consumer=$tree/multimedia/qt6-qtmultimedia
sysroot=$("$BMAKE" -C "$tree/audio/pulseaudio" -V '${CROSS_DESTDIR}')
[ -f "$sysroot/usr/include/sys/atomic.h" ]
# Qt Multimedia includes the PulseAudio buildlink3.mk.
for recipe in audio/pulseaudio multimedia/qt6-qtmultimedia; do
	name=$(echo "$recipe" | tr / _)
	"$BMAKE" -C "$tree/$recipe" -V '${BUILDLINK_TREE}' | tr ' ' '\n' > "$work/$name.tree"
	if grep -x libatomic_ops "$work/$name.tree"; then exit 1; fi
done
grep -qx pulseaudio "$work/multimedia_qt6-qtmultimedia.tree"
# Link a real target program with the consumer's linker flags. libpulse
# needs libpulsecommon, which only lib/pulseaudio provides.
cc=$("$BMAKE" -C "$consumer" -V '${TOOLDIR}/bin/${MACHINE_GNU_PLATFORM}-gcc')
[ -x "$cc" ]
# The compiler wrappers append the base library search; add it explicitly.
ldflags="$("$BMAKE" -C "$consumer" -V '${LDFLAGS}') $("$BMAKE" -C "$consumer" -V '${CWRAPPERS_APPEND.cc}')"
cat > "$work/client.c" <<'C'
#include <pulse/context.h>
#include <pulse/mainloop.h>
int main(void) {
	pa_mainloop *m = pa_mainloop_new();
	pa_context *c = pa_context_new(pa_mainloop_get_api(m), "ember");
	pa_context_unref(c);
	pa_mainloop_free(m);
	return 0;
}
C
# shellcheck disable=SC2086
"$cc" --sysroot="$sysroot" -I"$sysroot/usr/pkg/include" "$work/client.c" \
    -L"$sysroot/usr/pkg/lib" $ldflags -lpulse -o "$work/client" > "$work/link.log" 2>&1 ||
    { cat "$work/link.log" >&2; exit 1; }
if grep -F 'libpulsecommon' "$work/link.log"; then exit 1; fi
echo 'PASS: PulseAudio consumers use target atomics and link libpulse with libpulsecommon'
