#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). tools refuses, with a message, an order in
# which the dependencies of a package cannot be read (here a makefile that
# includes a missing buildlink3.mk): it names the package and its make error
# on stderr, exits non-zero and keeps the old order and edges. A recording
# bmake on a two-package tree stands in for pkgsrc.
# Usage: cross-bulk-tools-unreadable.sh NEW_OUTPUT
set -eu
[ "$#" = 1 ] || { echo 'Usage: cross-bulk-tools-unreadable.sh NEW_OUTPUT' >&2; exit 2; }
out=$1
case "$out" in /*) ;; *) echo 'NEW_OUTPUT must be absolute' >&2; exit 2 ;; esac
case "$out" in *[!A-Za-z0-9_./-]*) echo 'Use simple paths.' >&2; exit 2 ;; esac
[ ! -e "$out" ] || exit 2
ports=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd -P)
mkdir -p "$out/tree/t/a" "$out/tree/t/bad" "$out/tree/n/gen" "$out/packages/All" "$out/native-db" "$out/state"
echo gen > "$out/tree/t/a/tools"
cat > "$out/pkg_info" <<WRAP
#!/bin/sh
[ "\$1" = -K ] && [ "\$3" = -e ] && [ -e "\$2/\${4%%>=*}" ]
WRAP
cat > "$out/bmake" <<WRAP
#!/bin/sh
out=$out
dir= target= varname= varnames=
while [ "\$#" -gt 0 ]; do
    case "\$1" in
        -C) dir=\$2; shift 2 ;;
        VARNAME=*) varname=\${1#VARNAME=}; shift ;;
        VARNAMES=*) varnames=\${1#VARNAMES=}; shift ;;
        *=*) shift ;;
        *) target=\$1; shift ;;
    esac
done
pkg=\${dir##*/}
case "\$target" in
    show-var)
        case "\$varname" in
            EMBERBSD_NATIVE_TOOLSET_VERIFIED) echo fake ;;
            PACKAGES) echo \$out/packages ;;
            PKG_INFO) echo "\$out/pkg_info -K \$out/native-db" ;;
            *) echo ;;
        esac ;;
    show-vars)
        if [ "\$pkg" = bad ]; then
            echo "bmake: \$dir/Makefile:7: Could not find ../../x/missing/buildlink3.mk" >&2
            echo 'bmake: Fatal errors encountered -- cannot continue' >&2
            exit 1
        fi
        for v in \$varnames; do
            case "\$v" in
                PKGNAME) echo "\$pkg-1.0" ;;
                PKGBASE) echo "\$pkg" ;;
                TOOL_DEPENDS) for x in \$(cat \$dir/tools 2> /dev/null); do printf '%s ' "\$x>=1:../../n/\$x"; done; echo ;;
                *) echo ;;
            esac
        done ;;
    *) echo "UNKNOWN \$target" >&2; exit 1 ;;
esac
WRAP
chmod +x "$out/bmake" "$out/pkg_info"
fail() { echo "FAIL: $*" >&2; exit 1; }
printf '%s\n' t/a t/bad > "$out/list"
printf '%s\n' 't/a t/a' 't/bad t/bad' > "$out/state/edges"
printf '%s\n' t/a t/bad > "$out/state/order"
cp "$out/state/edges" "$out/edges.before"
cp "$out/state/order" "$out/order.before"
if BMAKE=$out/bmake MAKECONF=$out/mk.conf PKGSRCDIR=$out/tree CROSS_BULK_CPUS=4 CROSS_BULK_JOBS=2 \
    sh "$ports/scripts/cross-bulk.sh" tools "$out/list" "$out/state" > "$out/tools.out" 2> "$out/tools.err"; then
    fail 'tools accepted a package whose dependencies cannot be read'
fi
grep -q '^Refused: the dependencies of these packages could not be read:$' "$out/tools.err" ||
    fail "tools gave no refusal: [$(cat "$out/tools.err")]"
grep -q '^t/bad tools$' "$out/tools.err" || fail "tools did not name t/bad: [$(cat "$out/tools.err")]"
grep -q 'Could not find ../../x/missing/buildlink3.mk' "$out/tools.err" ||
    fail "tools did not show the make error: [$(cat "$out/tools.err")]"
grep -q '^t/a ' "$out/tools.err" && fail 'tools named the readable t/a'
cmp -s "$out/state/order" "$out/order.before" && cmp -s "$out/state/edges" "$out/edges.before" ||
    fail 'tools changed the order or edges'
echo 'PASS: tools refuses an unreadable package with its name and make error and keeps the old order'
