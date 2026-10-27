#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). The bulk helper verifies the native prefix once.
# BMAKE, MAKECONF and PKGSRCDIR select a prepared cross tree as for
# scripts/cross-bulk.sh. PKGPATH is a package with target dependencies.
set -eu
[ "$#" = 3 ] || { echo 'Usage: cross-bulk-native-once.sh HOST_PREFIX PKGPATH NEW_OUTPUT' >&2; exit 2; }
prefix=$1 path=$2 out=$3
: "${BMAKE:?}" "${MAKECONF:?}" "${PKGSRCDIR:?}"
case "$prefix$out" in *[!A-Za-z0-9_./-]*) echo 'Use simple paths.' >&2; exit 2;; esac
[ ! -e "$out" ] || exit 2
ports=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd -P)
mkdir "$out"
# Count verifier runs through a Python wrapper selected on the command line.
cat > "$out/python" <<WRAP
#!/bin/sh
echo verify >> $out/calls
exec $prefix/bin/python3.15 "\$@"
WRAP
cat > "$out/bmake" <<WRAP
#!/bin/sh
exec "$BMAKE" EMBERBSD_HOST_PYTHON=$out/python "\$@"
WRAP
chmod +x "$out/python" "$out/bmake"
echo "$path" > "$out/list"
BMAKE=$out/bmake sh "$ports/scripts/cross-bulk.sh" order "$out/list" "$out/state" > "$out/order.log"
packages=$(($(wc -l < "$out/state/order")))
calls=$(($(wc -l < "$out/calls")))
[ "$packages" -gt 1 ] || { echo "FAIL: $path has no target dependencies" >&2; exit 1; }
[ "$calls" -eq 1 ] || { echo "FAIL: $calls verifier runs for $packages packages" >&2; exit 1; }
# A broken selection still stops the run before any package query.
printf '#!/bin/sh\nexit 1\n' > "$out/python"
if BMAKE=$out/bmake sh "$ports/scripts/cross-bulk.sh" order "$out/list" "$out/bad" 2> "$out/bad.err"; then
    echo 'FAIL: an unverified prefix was accepted' >&2; exit 1
fi
grep -q 'failed verification' "$out/bad.err" || { echo 'FAIL: missing verification error' >&2; exit 1; }
[ ! -e "$out/bad/order" ] || { echo 'FAIL: order written without verification' >&2; exit 1; }
echo "PASS: one verifier run for $packages packages; a failed verification stops the run"
