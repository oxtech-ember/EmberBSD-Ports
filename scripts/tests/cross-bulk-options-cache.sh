#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Order asks for the build options of each
# dependency once per run, and its result is the same as without a cache.
# Fetch reuses the cache only while the inputs of the order run are unchanged.
# BMAKE, MAKECONF and PKGSRCDIR select a prepared cross tree as for
# scripts/cross-bulk.sh. The PKGPATHs need dependencies with build options.
set -eu
[ "$#" -ge 2 ] || { echo 'Usage: cross-bulk-options-cache.sh NEW_OUTPUT PKGPATH...' >&2; exit 2; }
out=$1
shift
: "${BMAKE:?}" "${MAKECONF:?}" "${PKGSRCDIR:?}"
case "$out" in /*) ;; *) echo 'NEW_OUTPUT must be absolute' >&2; exit 2;; esac
case "$out" in *[!A-Za-z0-9_./-]*) echo 'Use simple paths.' >&2; exit 2;; esac
[ ! -e "$out" ] || exit 2
ports=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd -P)
mkdir "$out" "$out/distfiles"
printf '%s\n' "$@" > "$out/list"
printf '.include "%s"\n' "$MAKECONF" > "$out/mk.conf"
# The nested build options query runs ${MAKE}; count it per directory.
# A "nocache" file drops the cache from the command line, as before.
# A fetch only parses the package; nothing is downloaded.
cat > "$out/make" <<WRAP
#!/bin/sh
case " \$* " in *" VARNAME=PKG_OPTIONS "*) pwd -P >> "\$(cat $out/current)" ;; esac
exec "$BMAKE" "\$@"
WRAP
cat > "$out/bmake" <<WRAP
#!/bin/sh
for arg do
    shift
    case "\$arg" in
        PBULK_CACHE_DIRECTORY=*) [ -e $out/nocache ] && continue
            echo "\$arg" >> $out/cache-args ;;
        fetch) set -- "\$@" show-var VARNAME=PKGNAME; continue ;;
    esac
    set -- "\$@" "\$arg"
done
exec "$BMAKE" MAKE=$out/make DISTDIR=$out/distfiles "\$@"
WRAP
chmod +x "$out/make" "$out/bmake"
run()
{
    echo "$out/$1.queries" > "$out/current"
    MAKECONF=$out/mk.conf BMAKE=$out/bmake \
        sh "$ports/scripts/cross-bulk.sh" "$2" "$out/list" "$out/$3" > "$out/$1.log" 2>&1 || {
        cat "$out/$1.log" >&2
        echo "FAIL: $1" >&2
        exit 1
    }
    touch "$out/$1.queries"
}
touch "$out/nocache"
run plain order plain
rm "$out/nocache"
run cached order cached
for name in order edges skipped; do
    cmp -s "$out/plain/$name" "$out/cached/$name" || { echo "FAIL: $name differs with the cache" >&2; exit 1; }
done
plain=$(($(wc -l < "$out/plain.queries")))
cached=$(($(wc -l < "$out/cached.queries")))
dirs=$(($(sort -u "$out/cached.queries" | wc -l)))
[ "$plain" -gt "$cached" ] || { echo "FAIL: $plain queries without and $cached with the cache" >&2; exit 1; }
[ "$cached" -eq "$dirs" ] || { echo "FAIL: $cached queries for $dirs packages with the cache" >&2; exit 1; }
# Fetch in the same run reuses the cache and asks for nothing more.
: > "$out/cache-args"
run fetch fetch cached
[ -s "$out/cache-args" ] || { echo 'FAIL: fetch did not reuse the order cache' >&2; exit 1; }
[ ! -s "$out/fetch.queries" ] || { echo 'FAIL: fetch queried build options again' >&2; exit 1; }
# A MAKECONF changed after order makes fetch query without the cache.
echo '# changed' >> "$out/mk.conf"
: > "$out/cache-args"
run changed fetch cached
[ ! -s "$out/cache-args" ] || { echo 'FAIL: fetch reused the cache of an older MAKECONF' >&2; exit 1; }
grep -q 'not from this tree' "$out/changed.log" || { echo 'FAIL: no note about the unused cache' >&2; exit 1; }
echo "PASS: $plain option queries without the cache, $cached with it, same order; fetch reuses it only unchanged"
