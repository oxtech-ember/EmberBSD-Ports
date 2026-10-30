#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). The build parses each package once for
# its PKGNAME and WRKDIR, then runs clean and package-install. A package
# recorded as done costs one parse. Clean and package-install are recorded,
# not run; package-install leaves an empty package file. One package at a
# time (CROSS_BULK_JOBS=1): the parallel steps are in cross-bulk-parallel.sh.
# BMAKE, MAKECONF and PKGSRCDIR select a prepared cross tree as for
# scripts/cross-bulk.sh.
set -eu
[ "$#" -ge 2 ] || { echo 'Usage: cross-bulk-build-queries.sh NEW_OUTPUT PKGPATH...' >&2; exit 2; }
out=$1
shift
: "${BMAKE:?}" "${MAKECONF:?}" "${PKGSRCDIR:?}"
case "$out" in /*) ;; *) echo 'NEW_OUTPUT must be absolute' >&2; exit 2;; esac
case "$out" in *[!A-Za-z0-9_./-]*) echo 'Use simple paths.' >&2; exit 2;; esac
[ ! -e "$out" ] || exit 2
ports=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd -P)
mkdir -p "$out/state" "$out/packages/All"
cat > "$out/bmake" <<WRAP
#!/bin/sh
echo "\$*" >> $out/calls
case " \$* " in
    *" clean "*) exit 0 ;;
    *" package-install "*)
        for arg do
            shift
            [ "\$arg" = package-install ] || set -- "\$@" "\$arg"
        done
        name=\$("$BMAKE" PACKAGES=$out/packages "\$@" show-var VARNAME=PKGNAME)
        : > $out/packages/All/\$name.tgz
        exit 0 ;;
esac
exec "$BMAKE" PACKAGES=$out/packages "\$@"
WRAP
chmod +x "$out/bmake"
: > "$out/state/edges"
for path do
    echo "$path" >> "$out/state/order"
    echo "$path $path" >> "$out/state/edges"
done
run()
{
    expected=$1
    shift
    : > "$out/calls"
    BMAKE=$out/bmake CROSS_BULK_JOBS=1 sh "$ports/scripts/cross-bulk.sh" build "$out/state/order" "$out/state" ||
        { echo 'FAIL: build' >&2; exit 1; }
    for path do
        calls=$(($(grep -c -- "-C $PKGSRCDIR/$path " "$out/calls" || :)))
        [ "$calls" -eq "$expected" ] ||
            { echo "FAIL: $calls bmake runs for $path, expected $expected" >&2; exit 1; }
    done
}
run 3 "$@"
[ "$(($(wc -l < "$out/state/done")))" -eq "$#" ] || { echo 'FAIL: packages not recorded as done' >&2; exit 1; }
run 1 "$@"
echo "PASS: 3 bmake runs for each new package, 1 for each done package"
