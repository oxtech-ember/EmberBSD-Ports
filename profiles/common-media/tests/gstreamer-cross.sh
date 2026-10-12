#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), complete cross-package output checks.
set -eu
[ "$#" = 2 ] || { echo 'Usage: gstreamer-cross.sh PREPARED_PKGSRC NEW_WORK' >&2; exit 2; }
: "${BMAKE:?Set native bmake}" "${MAKECONF:?Set cross MAKECONF}"
tree=$(CDPATH= cd -- "$1" && pwd)
mkdir "$2"
work=$(CDPATH= cd -- "$2" && pwd)
recipe=$tree/multimedia/gstreamer1
get() { "$BMAKE" -C "$recipe" -V "\${$1}"; }
[ "$(get PKGNAME)" = gstreamer1-1.28.8 ]
source=$(get WRKSRC)
host=$(get TOOLBASE)
stage=$(get DESTDIR)
prefix=$(get PREFIX)
[ -s "$source/output/build.ninja" ]
for name in glib-mkenums glib-genmarshal g-ir-scanner g-ir-compiler; do
    [ "$(get "MESON_BINARY.$name")" = "$host/bin/$name" ]
    [ -x "$host/bin/$name" ]
done
[ -z "$("$BMAKE" -C "$recipe" USE_CROSS_COMPILE=no -V '${MESON_BINARIES}')" ]
# The original get_flex_version.py was rewritten to an unexecutable target path.
# Execute the packaged build input, not a replacement of the upstream script.
head -n 1 "$source/gst/parse/get_flex_version.py" > "$work/flex-shebang.txt"
grep -F "$host/bin/" "$work/flex-shebang.txt"
"$source/gst/parse/get_flex_version.py" "$(get WRKDIR)/.tools/bin/flex" > "$work/flex-version.txt"
grep -Eq '^[0-9]+\.[0-9]+' "$work/flex-version.txt"
[ -s "$source/output/gst/gstenumtypes.c" ]
[ -s "$source/output/gst/parse/grammar.tab.c" ]
[ -s "$source/output/gst/parse/lex.priv_gst_parse_yy.c" ]
# Full introspection remains required, including the four support libraries.
for namespace in Gst GstBase GstCheck GstController GstNet; do
    [ -s "$stage$prefix/share/gir-1.0/$namespace-1.0.gir" ]
    [ -s "$stage$prefix/lib/girepository-1.0/$namespace-1.0.typelib" ]
    grep -q '<enumeration\|<class\|<record' "$stage$prefix/share/gir-1.0/$namespace-1.0.gir"
done
for executable in gst-inspect-1.0 gst-launch-1.0 gst-stats-1.0 gst-typefind-1.0; do
    [ -x "$stage$prefix/bin/$executable" ]
done
for plugin in coreelements coretracers; do
    [ -s "$stage$prefix/lib/gstreamer-1.0/libgst$plugin.so" ]
done
[ -s "$stage$prefix/libexec/gstreamer-1.0/gst-plugin-scanner" ]
# Upstream used to skip the whole docs directory in cross mode, losing helpers.
"$(get TOOLDIR)/bin/aarch64--netbsd-readelf" -h "$stage$prefix/libexec/gstreamer-1.0/gst-hotdoc-plugins-scanner" > "$work/hotdoc-elf.txt"
grep -q 'AArch64' "$work/hotdoc-elf.txt"
head -n 1 "$stage$prefix/libexec/gstreamer-1.0/gst-plugins-doc-cache-generator" > "$work/cache-shebang.txt"
grep -Fx "#!$(get PYTHONBIN)" "$work/cache-shebang.txt"
[ -s "$stage$prefix/share/locale/ru/LC_MESSAGES/gstreamer-1.0.mo" ]
echo 'PASS: real native generators/grammar, native selection, all five GIR/typelibs, utilities, plugins, documentation helpers, scanner and translation retained'
