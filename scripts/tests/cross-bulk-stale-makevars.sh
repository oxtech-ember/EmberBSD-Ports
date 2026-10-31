#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). The dependencies that order and deps read
# do not depend on a WRKDIR left by an earlier build. pkgsrc saves the
# MAKEVARS of each phase (USE_BUILTIN.* among them) in
# WRKDIR/.PHASE_makevars.mk and every later parse includes the latest one
# unless _MAKEVARS_MK is defined. Here t/app prefers the tree's t/ssl
# (as security/heimdal does with PREFER.openssl=pkgsrc), and its WRKDIR
# still has USE_BUILTIN.ssl=yes from a build before that: the order must
# keep the t/ssl -> t/app edge, and deps must list t/ssl. A bmake that
# follows that pkgsrc rule on a two-package tree stands in for pkgsrc.
# Usage: cross-bulk-stale-makevars.sh NEW_OUTPUT
set -eu
[ "$#" = 1 ] || { echo 'Usage: cross-bulk-stale-makevars.sh NEW_OUTPUT' >&2; exit 2; }
out=$1
case "$out" in /*) ;; *) echo 'NEW_OUTPUT must be absolute' >&2; exit 2 ;; esac
case "$out" in *[!A-Za-z0-9_./-]*) echo 'Use simple paths.' >&2; exit 2 ;; esac
[ ! -e "$out" ] || exit 2
ports=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd -P)
mkdir -p "$out/tree/t/app" "$out/tree/t/ssl" "$out/work/app" "$out/native-db" "$out/state" "$out/deps"
printf '_MAKEVARS_MK=\tdefined\nUSE_BUILTIN.ssl=\tyes\n' > "$out/work/app/.configure_makevars.mk"
cat > "$out/pkg_info" <<WRAP
#!/bin/sh
[ "\$1" = -K ] && [ "\$3" = -e ] && [ -e "\$2/\${4%%>=*}" ]
WRAP
cat > "$out/bmake" <<WRAP
#!/bin/sh
out=$out
dir= target= varname= varnames= guarded=
while [ "\$#" -gt 0 ]; do
    case "\$1" in
        -C) dir=\$2; shift 2 ;;
        VARNAME=*) varname=\${1#VARNAME=}; shift ;;
        VARNAMES=*) varnames=\${1#VARNAMES=}; shift ;;
        _MAKEVARS_MK=*) guarded=1; shift ;;
        *=*) shift ;;
        *) target=\$1; shift ;;
    esac
done
pkg=\${dir##*/}
# t/app: PREFER.ssl=pkgsrc gives USE_BUILTIN.ssl=no, unless the saved
# makevars of its WRKDIR are included (bsd.makevars.mk) and replace it.
builtin=no
if [ -z "\$guarded" ] && [ -f "\$out/work/\$pkg/.configure_makevars.mk" ]; then
    builtin=\$(sed -n 's/^USE_BUILTIN.ssl=[[:space:]]*//p' "\$out/work/\$pkg/.configure_makevars.mk")
fi
case "\$target" in
    show-var)
        case "\$varname" in
            EMBERBSD_NATIVE_TOOLSET_VERIFIED) echo fake ;;
            PKG_INFO) echo "\$out/pkg_info -K \$out/native-db" ;;
            .MAKE.MAKEFILES) echo ;;
            *) echo ;;
        esac ;;
    show-vars)
        for v in \$varnames; do
            case "\$v" in
                PKGNAME) echo "\$pkg-1.0" ;;
                PKGBASE) echo "\$pkg" ;;
                DEPENDS)
                    if [ "\$pkg" = app ] && [ "\$builtin" != yes ]; then
                        echo 'ssl>=3:../../t/ssl'
                    else
                        echo
                    fi ;;
                *) echo ;;
            esac
        done ;;
    *) echo "UNKNOWN \$target" >&2; exit 1 ;;
esac
WRAP
chmod +x "$out/bmake" "$out/pkg_info"
fail() { echo "FAIL: $*" >&2; exit 1; }
echo t/app > "$out/list"
BMAKE=$out/bmake MAKECONF=$out/mk.conf PKGSRCDIR=$out/tree \
    sh "$ports/scripts/cross-bulk.sh" order "$out/list" "$out/state" > "$out/order.out" 2> "$out/order.err" ||
    fail "order failed: [$(cat "$out/order.err")]"
grep -qx 't/ssl t/app' "$out/state/edges" ||
    fail "order lost the t/ssl -> t/app edge to the saved makevars: [$(tr '\n' ';' < "$out/state/edges")]"
grep -qx t/ssl "$out/state/order" || fail 'order has no t/ssl node'
[ "$(grep -n . "$out/state/order" | sed -n 's/:t\/ssl$//p')" -lt "$(grep -n . "$out/state/order" | sed -n 's/:t\/app$//p')" ] ||
    fail 'order puts t/app before t/ssl'
BMAKE=$out/bmake MAKECONF=$out/mk.conf PKGSRCDIR=$out/tree CROSS_BULK_NATIVE=fake \
    sh "$ports/scripts/cross-bulk.sh" deps t/app "$out/deps" 2> "$out/deps.err" ||
    fail "deps failed: [$(cat "$out/deps.err")]"
grep -qx t/ssl "$out/deps/t_app.deps" ||
    fail "deps lost t/ssl to the saved makevars: [$(tr '\n' ';' < "$out/deps/t_app.deps")]"
echo 'PASS: order and deps read the dependencies without the makevars of an old WRKDIR'
