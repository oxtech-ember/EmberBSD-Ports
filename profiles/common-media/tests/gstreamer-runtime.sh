#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), installed GStreamer core acceptance.
set -eu
[ "$#" = 2 ] || { echo 'Usage: gstreamer-runtime.sh BUNDLE NEW_WORK' >&2; exit 2; }
[ "$(uname -s)" = NetBSD ] && [ "$(uname -p)" = aarch64 ]
[ -z "${LD_LIBRARY_PATH:-}" ] && [ -z "${LD_PRELOAD:-}" ]
bundle=$(CDPATH= cd -- "$1" && pwd)
umask 077
mkdir "$2"
work=$(CDPATH= cd -- "$2" && pwd)
PATH=/usr/pkg/bin:/usr/pkg/sbin:/usr/bin:/usr/sbin:/bin:/sbin; export PATH
while read expected name; do [ "$(sha256 -q "$bundle/$name")" = "$expected" ]; done < "$bundle/files.sha256"
while read expected name; do [ "$(sha256 -q "$name")" = "$expected" ]; done < "$bundle/runtime.sha256"
pkg_info -e 'gstreamer1>=1.28.8' > "$work/package.txt"
sysctl kern.boottime > "$work/boot.before"
mkdir "$work/home"
for test_name in gstbuffer gstcaps gstevent gstquery gstsegment gststructure; do
    ldd "$bundle/bin/gst_$test_name" > "$work/$test_name.ldd"
    ! grep -q 'not found' "$work/$test_name.ldd"
    grep -q '=> /usr/pkg/lib/libgstreamer-1.0' "$work/$test_name.ldd"
    timeout -k 5 120 env -i PATH="$PATH" HOME="$work/home" LC_ALL=C.UTF-8 \
        GST_PLUGIN_SYSTEM_PATH_1_0=/usr/pkg/lib/gstreamer-1.0 \
        GST_PLUGIN_PATH_1_0= GST_PLUGIN_SCANNER_1_0=/usr/pkg/libexec/gstreamer-1.0/gst-plugin-scanner \
        GST_STATE_IGNORE_ELEMENTS= GST_PLUGIN_LOADING_WHITELIST=gstreamer \
        GST_REGISTRY="$work/$test_name.registry" CK_DEFAULT_TIMEOUT=20 \
        "$bundle/bin/gst_$test_name" > "$work/$test_name.log" 2>&1
    grep -E '^100%: Checks: [1-9][0-9]*, Failures: 0, Errors: 0' "$work/$test_name.log"
done
timeout -k 5 60 env -i PATH="$PATH" HOME="$work/home" LC_ALL=C.UTF-8 \
    GST_REGISTRY="$work/pipeline.registry" \
    gst-launch-1.0 -m fakesrc num-buffers=64 ! identity ! fakesink > "$work/pipeline.log" 2>&1
grep -q 'Got EOS from element' "$work/pipeline.log"
result=0
timeout -k 5 60 env -i PATH="$PATH" HOME="$work/home" LC_ALL=C.UTF-8 \
    GST_REGISTRY="$work/pipeline.registry" \
    gst-launch-1.0 ember_missing_element ! fakesink > "$work/missing-element.log" 2>&1 || result=$?
[ "$result" = 1 ]
grep -q 'no element.*ember_missing_element' "$work/missing-element.log"
sysctl kern.boottime > "$work/boot.after"
cmp "$work/boot.before" "$work/boot.after"
echo 'PASS: six original core test suites, finite pipeline/EOS and missing-element rejection; installed libraries without loader overrides'
