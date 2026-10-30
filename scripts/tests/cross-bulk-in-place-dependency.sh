#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). scripts/cross-bulk.sh build never lets
# pkgsrc's depends step build a dependency in place. Dependency a is built
# and installed as a-1.0, but its dependents b and c require a-1.0nb1 (a
# stale buildlink pin), so pkgsrc's depends step finds no match and runs
# DEPENDS_TARGET in a's directory. The recording bmake does what pkgsrc does
# there: the default DEPENDS_TARGET (reinstall) rebuilds a in a's WRKDIR,
# and a barrier holds each such build until the other dependent arrives, so
# the shared WRKDIR shows up deterministically. The build must instead fail
# b and c at once, naming the refused dependency, and never touch a's
# WRKDIR from a dependent.
# Usage: cross-bulk-in-place-dependency.sh NEW_OUTPUT
set -eu
[ "$#" = 1 ] || { echo 'Usage: cross-bulk-in-place-dependency.sh NEW_OUTPUT' >&2; exit 2; }
out=$1
case "$out" in /*) ;; *) echo 'NEW_OUTPUT must be absolute' >&2; exit 2 ;; esac
case "$out" in *[!A-Za-z0-9_./-]*) echo 'Use simple paths.' >&2; exit 2 ;; esac
[ ! -e "$out" ] || exit 2
ports=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd -P)
mkdir -p "$out/tree/t/a" "$out/tree/t/b" "$out/tree/t/c" "$out/packages/All" "$out/work" "$out/target-db"
: > "$out/errors"
: > "$out/inplace"
echo a > "$out/tree/t/b/deps"
echo a > "$out/tree/t/c/deps"
printf '%s\n' 't/a t/a' 't/b t/b' 't/c t/c' 't/a t/b' 't/a t/c' > "$out/edges"
cat > "$out/pkg_add" <<WRAP
#!/bin/sh
: > "\$2/\$3-1.0"
WRAP
cat > "$out/bmake" <<WRAP
#!/bin/sh
out=$out
self=\$0
echo "\$*" >> \$out/calls
dir= target= varname= add= dtarget=reinstall
while [ "\$#" -gt 0 ]; do
    case "\$1" in
        -C) dir=\$2; shift 2 ;;
        VARNAME=*) varname=\${1#VARNAME=}; shift ;;
        NATIVE_PKG_ADD_CMD=*) add=\${1#NATIVE_PKG_ADD_CMD=}; shift ;;
        DEPENDS_TARGET=*) dtarget=\${1#DEPENDS_TARGET=}; shift ;;
        *=*) shift ;;
        *) target=\$1; shift ;;
    esac
done
pkg=\${dir##*/}
# pkgsrc's depends step: the dependents want a-1.0nb1, a-1.0 is installed.
depends()
{
    for dep in \$(cat \$dir/deps 2> /dev/null); do
        [ ! -f \$out/target-db/\$dep-1.0nb1 ] || continue
        echo "=> Build dependency \$dep-1.0nb1: NOT found"
        echo "=> Verifying \$dtarget for ../../t/\$dep"
        "\$self" -C \$out/tree/t/\$dep DEPENDS_TARGET=\$dtarget INPLACE_FOR=\$pkg \$dtarget || return 1
    done
}
# An in-place build of a in its own WRKDIR, as a dependent's depends step runs it.
inplace()
{
    echo "\$pkg" >> \$out/inplace
    mkdir \$out/work/\$pkg.wrkdir-busy 2> /dev/null || echo "SHARED WRKDIR \$pkg" >> \$out/errors
    n=0
    while [ "\$(wc -l < \$out/inplace)" -lt 2 ] && [ "\$n" -lt 50 ]; do sleep 0.1; n=\$((n + 1)); done
    sleep 0.2
    rmdir \$out/work/\$pkg.wrkdir-busy 2> /dev/null || :
    exit 1
}
case "\$target" in
    show-var)
        case "\$varname" in
            EMBERBSD_NATIVE_TOOLSET_VERIFIED) echo fake ;;
            PACKAGES) echo \$out/packages ;;
            PKG_INFO) echo false ;;
            NATIVE_PKG_ADD_CMD) echo \$out/pkg_add ;;
            *) echo ;;
        esac ;;
    show-vars) echo "\$pkg-1.0"; echo "\$out/work/\$pkg"; echo ;;
    clean) ;;
    package-install)
        depends || exit 1
        \$add -K \$out/target-db \$pkg || exit 1
        : > \$out/packages/All/\$pkg-1.0.tgz ;;
    reinstall) inplace ;;
    *) echo "bmake: don't know how to make \$target. Stop"; exit 2 ;;
esac
WRAP
chmod +x "$out/bmake" "$out/pkg_add"
fail() { echo "FAIL: $*" >&2; exit 1; }
mkdir "$out/state"
cp "$out/edges" "$out/state/edges"
tsort "$out/edges" > "$out/state/order"
: > "$out/calls"
rc=0
BMAKE=$out/bmake MAKECONF=$out/mk.conf PKGSRCDIR=$out/tree CROSS_BULK_CPUS=2 CROSS_BULK_JOBS=2 \
    sh "$ports/scripts/cross-bulk.sh" build "$out/state/order" "$out/state" > "$out/bulk.log" 2>&1 || rc=$?
[ ! -s "$out/errors" ] || fail "$(cat "$out/errors")"
[ ! -s "$out/inplace" ] || fail "dependents built a in place: $(tr '\n' ' ' < "$out/inplace")"
[ "$(cut -d ' ' -f 1 "$out/state/done")" = t/a ] || fail "done: $(cat "$out/state/done")"
[ "$(sort "$out/state/failed" | tr '\n' ' ')" = 't/b build t/c build ' ] ||
    fail "failed: $(cat "$out/state/failed")"
for key in t_b t_c; do
    grep -q 'Verifying emberbsd-refuse-unpreflighted-dependency for ../../t/a' "$out/state/logs/$key.log" ||
        fail "$key log does not name the refused dependency: $(cat "$out/state/logs/$key.log")"
done
grep -q 'DEPENDS_TARGET=emberbsd-refuse-unpreflighted-dependency .*-C '"$out"'/tree/t/a show-vars' "$out/calls" ||
    fail 'show-vars of a ran without the refusing DEPENDS_TARGET'
echo 'PASS: a dependent never builds a dependency in place; it fails naming the dependency'
