#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). A pass of scripts/cross-bulk.sh build does
# not parse a done package again while no makefile that its parse read has
# changed, and still sees every version bump. With a recording bmake whose
# PKGNAME comes from the makefiles it reports in .MAKE.MAKEFILES: a second
# run parses nothing; a PKGREVISION in an included .mk parses and rebuilds
# only the package that includes it; a new hacks.mk next to a Makefile
# parses that package again; CROSS_BULK_VARS_CACHE=no parses everything.
# Usage: cross-bulk-vars-cache.sh NEW_OUTPUT
set -eu
[ "$#" = 1 ] || { echo 'Usage: cross-bulk-vars-cache.sh NEW_OUTPUT' >&2; exit 2; }
out=$1
case "$out" in /*) ;; *) echo 'NEW_OUTPUT must be absolute' >&2; exit 2 ;; esac
case "$out" in *[!A-Za-z0-9_./-]*) echo 'Use simple paths.' >&2; exit 2 ;; esac
[ ! -e "$out" ] || exit 2
ports=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd -P)
mkdir -p "$out/tree/t/a" "$out/tree/t/b" "$out/tree/inc" "$out/packages/All" "$out/target-db"
: > "$out/errors"
: > "$out/mk.conf"
echo 'PKGREVISION=' > "$out/tree/inc/version.mk"
echo '.include "../../inc/version.mk"' > "$out/tree/t/a/Makefile"
echo '# b' > "$out/tree/t/b/Makefile"
cat > "$out/pkg_add" <<WRAP
#!/bin/sh
: > "\$2/\$3"
WRAP
cat > "$out/pkg_info" <<WRAP
#!/bin/sh
exit 1
WRAP
cat > "$out/bmake" <<WRAP
#!/bin/sh
out=$out
dir= target= varname= varnames= add=
while [ "\$#" -gt 0 ]; do
    case "\$1" in
        -C) dir=\$2; shift 2 ;;
        VARNAME=*) varname=\${1#VARNAME=}; shift ;;
        VARNAMES=*) varnames=\${1#VARNAMES=}; shift ;;
        NATIVE_PKG_ADD_CMD=*) add=\${1#NATIVE_PKG_ADD_CMD=}; shift ;;
        *=*) shift ;;
        *) target=\$1; shift ;;
    esac
done
pkg=\${dir##*/}
[ "\$target" = show-var ] || echo "\$pkg \$target" >> \$out/calls
# What the parse reads: the MAKECONF, the Makefile and its includes.
cd "\$dir"
read=\$out/mk.conf\ Makefile
name=\$pkg-1.0
if [ "\$pkg" = a ]; then
    read="\$read ../../inc/version.mk"
    rev=\$(sed -n 's/^PKGREVISION=//p' ../../inc/version.mk)
    [ -z "\$rev" ] || name=\$name'nb'\$rev
fi
if [ -f hacks.mk ]; then
    read="\$read hacks.mk"
    name=\$pkg-1.0nb7
fi
case "\$target" in
    show-var)
        case "\$varname" in
            EMBERBSD_NATIVE_TOOLSET_VERIFIED) echo fake ;;
            PACKAGES) echo \$out/packages ;;
            NATIVE_PKG_ADD_CMD) echo \$out/pkg_add ;;
            PKG_INFO) echo "\$out/pkg_info" ;;
            *) echo ;;
        esac ;;
    show-vars)
        for v in \$varnames; do
            case "\$v" in
                PKGNAME) echo "\$name" ;;
                WRKDIR) echo "\$out/work-\$pkg" ;;
                .MAKE.MAKEFILES) echo "\$read" ;;
                .CURDIR) echo "\$dir" ;;
                *) echo ;;
            esac
        done ;;
    clean|depends|package) ;;
    package-install)
        echo "\$name" > \$out/packages/All/\$name.tgz
        \$add -K \$out/target-db \$pkg ;;
    *) echo "UNKNOWN \$target" >> \$out/errors; exit 1 ;;
esac
WRAP
chmod +x "$out/bmake" "$out/pkg_add" "$out/pkg_info"
fail() { echo "FAIL: $*" >&2; exit 1; }
printf '%s\n' t/a t/b > "$out/list"
mkdir "$out/state"
printf '%s\n' t/a t/b > "$out/state/order"
printf '%s\n' 't/a t/a' 't/b t/b' > "$out/state/edges"
bulk()
{
    : > "$out/calls"
    env BMAKE=$out/bmake MAKECONF=$out/mk.conf PKGSRCDIR=$out/tree CROSS_BULK_CPUS=4 CROSS_BULK_JOBS=2 "$@" \
        sh "$ports/scripts/cross-bulk.sh" build "$out/list" "$out/state" > "$out/build.log" 2>&1 ||
        fail "build: $(cat "$out/build.log")"
    [ ! -s "$out/errors" ] || fail "$(cat "$out/errors")"
}
parsed() { grep ' show-vars$' "$out/calls" | cut -d ' ' -f 1 | sort | tr '\n' ' '; }
built() { grep ' package-install$' "$out/calls" | cut -d ' ' -f 1 | sort | tr '\n' ' '; }

bulk
[ "$(parsed)" = 'a b ' ] && [ "$(built)" = 'a b ' ] || fail "first run parsed $(parsed), built $(built)"
bulk
[ -z "$(parsed)" ] || fail "an unchanged done package was parsed again: $(parsed)"
[ -z "$(built)" ] || fail "an unchanged done package was built again: $(built)"
# A version bump in an included .mk, same second and all.
echo 'PKGREVISION=1' > "$out/tree/inc/version.mk"
bulk
[ "$(parsed)" = 'a ' ] && [ "$(built)" = 'a ' ] ||
    fail "after a PKGREVISION in an included .mk: parsed $(parsed), built $(built)"
grep -qx 't/a a-1.0nb1 .*' "$out/state/done" || fail "a-1.0nb1 not done: $(cat "$out/state/done")"
# A new file next to a Makefile that the parse may include.
echo 'PKGREVISION=7' > "$out/tree/t/b/hacks.mk"
bulk
[ "$(parsed)" = 'b ' ] && [ "$(built)" = 'b ' ] || fail "after a new hacks.mk: parsed $(parsed), built $(built)"
bulk CROSS_BULK_VARS_CACHE=no
[ "$(parsed)" = 'a b ' ] && [ -z "$(built)" ] || fail "without the cache: parsed $(parsed), built $(built)"
echo 'PASS: done packages are not parsed again while their makefiles are unchanged; an included PKGREVISION, a new hacks.mk and CROSS_BULK_VARS_CACHE=no parse again'
