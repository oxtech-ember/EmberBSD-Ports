#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Check full TDB cross output and tool roles.
set -eu
[ "$#" = 2 ] || { echo 'Usage: tdb-cross.sh PKGSRC NEW_WORK' >&2; exit 2; }
: "${BMAKE:?Set native bmake}" "${MAKECONF:?Set cross MAKECONF}"
tree=$(CDPATH= cd -- "$1" && pwd)
mkdir "$2"
work=$(CDPATH= cd -- "$2" && pwd)
recipe=$tree/databases/tdb
get() { "$BMAKE" -C "$recipe" -V "\${$1}"; }
[ "$(get PKGNAME)" = tdb-1.4.15nb8 ]
source=$(get WRKSRC)
stage=$(get DESTDIR)$(get PREFIX)
config=$source/bin/c4che/default_cache.py
host=$(get TOOLBASE)
sysroot=$(get CROSS_DESTDIR)
get CONFIGURE_ENV > "$work/configure-env.txt"
grep -F "PYTHONPATH=$(get WRKDIR)/.pysite:$sysroot$(get LOCALBASE)/$(get PYLIB)" "$work/configure-env.txt" >/dev/null
grep -F "'$host/bin/python$(get PYVERSSUFFIX)', '$sysroot$(get PYTHONBIN)-config'" "$config" >/dev/null
grep -F "XSLTPROC = ['$host/bin/xsltproc']" "$config" >/dev/null
grep -F "XSLTPROC_MANPAGES = '1'" "$config" >/dev/null
grep -F "pyext_PATTERN = '%s.so'" "$config" >/dev/null
grep -E '^(CFLAGS|DEFINES|INCLUDES|LIBPATH|LIB|LINKFLAGS)_PY(EXT|EMBED) =' "$config" > "$work/python-target-flags.txt"
if grep -E 'DARWIN|MacOSX|apple|ldl' "$work/python-target-flags.txt"; then exit 1; fi
if grep -F "$host" "$work/python-target-flags.txt"; then exit 1; fi
native=$("$BMAKE" -C "$recipe" USE_CROSS_COMPILE=no -V '${CONFIGURE_ARGS}')
case "$native" in *--cross-compile*|*--cross-execute*) exit 1 ;; esac
sed -e '/^@/d' -e "s,\${PYSITELIB},$(get PYSITELIB),g" -e "s,\${PKGVERSION},$(get PKGVERSION_NOREV),g" "$recipe/PLIST" > "$work/package-files.txt"
while read -r file; do [ -e "$stage/$file" ]; done < "$work/package-files.txt"
# The default build replays stored answers and never asks a target.
case "$(get CONFIGURE_ARGS)" in *--cross-execute*) exit 1 ;; *--cross-answers=*) ;; *) exit 1 ;; esac
# Exercise the real capture-mode post-configure hook without changing the accepted build.
mkdir "$work/capture"
capture="EMBERBSD_WAF_ANSWERS_MODE=capture EMBERBSD_WAF_ANSWERS_CAPTURE_DIR=$work/capture"
printf '%s\n' 'Checking simple C program: "NetBSD"' > "$work/.cross-answers.txt"
printf '%s\n' 'Injected transport failure' > "$work/.waf-query-failure"
if env $capture "$BMAKE" -C "$recipe" WRKDIR="$work" emberbsd-waf-capture > "$work/query-result-fail.log" 2>&1; then
    echo 'TDB accepted an unverified configure result' >&2
    exit 1
fi
grep -F 'Injected transport failure' "$work/query-result-fail.log" >/dev/null
rm "$work/.waf-query-failure"
env $capture "$BMAKE" -C "$recipe" WRKDIR="$work" emberbsd-waf-capture > "$work/query-result-pass.log" 2>&1
echo 'PASS: target Python flags/ABI, host generators, native mode, complete TDB package and configure failure gate'
