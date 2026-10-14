#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Real dependency and file-codec acceptance.
set -eu
[ "$#" = 5 ] || { echo 'Usage: run-ffmpeg-target.sh FFMPEG_PACKAGE XML_PACKAGE AUDIO VIDEO NEW_OUTPUT' >&2; exit 2; }
package=$1 xml=$2 audio=$3 video=$4 out=$5
[ "$(uname -s)" = NetBSD ] && [ "$(uname -p)" = aarch64 ]
for path do case "$path" in /*) ;; *) echo 'Absolute paths required.' >&2; exit 2;; esac; done
[ ! -e "$out" ] && [ ! -L "$out" ]
[ -z "${LD_LIBRARY_PATH:-}${LD_PRELOAD:-}" ]
PATH=/usr/pkg/bin:/bin:/usr/bin:/sbin:/usr/sbin; export PATH
LC_ALL=C; export LC_ALL
profile=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd -P)
mkdir "$out"
uname -a > "$out/platform.txt"
pkg_add "$xml"
pkg_info -e libxml2-2.15.4
pkg_admin check libxml2 > "$out/xml-integrity.txt"
printf '<root><value>42</value></root>\n' > "$out/valid.xml"
xmllint --noout "$out/valid.xml" > "$out/xml-valid.log" 2>&1
printf '<root><value></root>\n' > "$out/invalid.xml"
if xmllint --noout "$out/invalid.xml" > "$out/xml-invalid.log" 2>&1; then exit 1; fi
pkg_add "$package"
pkg_info -e ffmpeg9-9.0.2
pkg_info -f ffmpeg9 > "$out/contents.txt"
grep -qx '@pkgdep libxml2-2.15.4' "$out/contents.txt"
pkg_admin check ffmpeg9 > "$out/integrity.txt"
ldd /usr/pkg/bin/ffmpeg9 /usr/pkg/bin/ffprobe9 > "$out/linkage.txt"
grep -q '/usr/pkg/lib/ffmpeg9/libavcodec.so.63' "$out/linkage.txt"
grep -q '/usr/pkg/lib/libxml2.so.16' "$out/linkage.txt"
grep -q '/usr/lib/libssl.so.16' "$out/linkage.txt"
if grep -q 'not found' "$out/linkage.txt"; then exit 1; fi
ffmpeg9 -protocols > "$out/protocols.txt" 2>&1
grep -q '^  https$' "$out/protocols.txt"
sh "$profile/tests/ffmpeg-cpu-runtime.sh" "$audio" "$video" "$out/codecs"
if pkg_delete libxml2-2.15.4 > "$out/dependency-removal.log" 2>&1; then
    echo 'Required dependency was removed.' >&2; exit 1
fi
pkg_info -e libxml2-2.15.4
pkg_delete ffmpeg9-9.0.2
[ ! -e /usr/pkg/bin/ffmpeg9 ] && [ ! -e /usr/pkg/lib/ffmpeg9/libavcodec.so.63 ]
if pkg_info -e ffmpeg9-9.0.2; then exit 1; fi
pkg_delete libxml2-2.15.4
[ ! -e /usr/pkg/lib/libxml2.so.16 ]
pkg_add "$xml"
pkg_add "$package"
pkg_admin check ffmpeg9 libxml2 > "$out/reinstalled-integrity.txt"
sh "$profile/tests/ffmpeg-cpu-runtime.sh" "$audio" "$video" "$out/reinstalled-codecs"
echo 'PASS: installed XML dependency, exact media, dependency protection, removal and reinstallation'
