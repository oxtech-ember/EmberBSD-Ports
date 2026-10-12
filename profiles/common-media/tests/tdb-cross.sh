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
[ "$(get PKGNAME)" = tdb-1.4.15nb1 ]
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
# Exercise the real post-configure hook without changing the accepted build.
"$BMAKE" -C "$recipe" WRKDIR="$work" emberbsd-tdb-query-result > "$work/query-result-pass.log" 2>&1
printf '%s\n' 'Injected transport failure' > "$work/.tdb-query-failure"
if "$BMAKE" -C "$recipe" WRKDIR="$work" emberbsd-tdb-query-result > "$work/query-result-fail.log" 2>&1; then
    echo 'TDB accepted an unverified configure result' >&2
    exit 1
fi
grep -F 'Injected transport failure' "$work/query-result-fail.log" >/dev/null
rm "$work/.tdb-query-failure"
echo 'PASS: target Python flags/ABI, host generators, native mode, complete TDB package and configure failure gate'
