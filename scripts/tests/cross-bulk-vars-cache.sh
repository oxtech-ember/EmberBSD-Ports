#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). A pass of scripts/cross-bulk.sh build does
# not parse a done package again while no makefile that its parse read has
# changed, and still sees every version bump. It binds build answers to
# MAKECONF and environment context, and detects new files beside external
# configs and optional include appearance. With a recording bmake
# whose PKGNAME comes from .MAKE.MAKEFILES: a second run parses nothing; an
# included-file edit or new hacks.mk parses the affected package;
# CROSS_BULK_VARS_CACHE=no parses everything.
# Usage: cross-bulk-vars-cache.sh NEW_OUTPUT
set -eu
[ "$#" = 1 ] || { echo 'Usage: cross-bulk-vars-cache.sh NEW_OUTPUT' >&2; exit 2; }
out=$1
case "$out" in /*) ;; *) echo 'NEW_OUTPUT must be absolute' >&2; exit 2 ;; esac
case "$out" in *[!A-Za-z0-9_./-]*) echo 'Use simple paths.' >&2; exit 2 ;; esac
[ ! -e "$out" ] || exit 2
ports=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd -P)
mkdir -p "$out/tree/t/a" "$out/tree/t/b" "$out/tree/inc" \
    "$out/config/main" "$out/config/optional" "$out/config/conditional" \
    "$out/packages/All" "$out/target-db"
: > "$out/tree/Makefile"
: > "$out/errors"
: > "$out/config/main/mk.conf"
echo 'PKGREVISION=5' > "$out/config/main/mk-alt.conf"
echo '.sinclude "local.mk"' > "$out/config/optional/mk.conf"
cat > "$out/config/conditional/mk.conf" <<'EOF'
.if exists \
    (local.mk)
.include "local.mk"
.endif
EOF
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
# What the parse reads: the selected MAKECONF, the Makefile and its includes.
cd "\$dir"
makeconf=\${MAKECONF:-\$out/config/main/mk.conf}
read=\$makeconf\ Makefile
if [ "\${CROSS_BULK_TEST_ROOT_MAKEFILE:-}" = yes ]; then
    read="\$read \$out/tree/Makefile"
fi
name=\$pkg-1.0
conf_rev=\$(sed -n 's/^PKGREVISION=//p' "\$makeconf")
[ -z "\$conf_rev" ] || name=\$name-conf\$conf_rev
if [ "\$pkg" = a ]; then
    read="\$read ../../inc/version.mk"
    rev=\$(sed -n 's/^PKGREVISION=//p' ../../inc/version.mk)
    [ -z "\$rev" ] || name=\$name'nb'\$rev
fi
if [ -f hacks.mk ]; then
    read="\$read hacks.mk"
    name=\$pkg-1.0nb7
fi
conf_dir=\${makeconf%/*}
optional=\$conf_dir/local.mk
case \$(cat "\$makeconf") in
    *'.sinclude "local.mk"'*)
        if [ -f "\$optional" ]; then
            read="\$read \$optional"
            name=\$name-opt
        fi ;;
esac
if grep -q 'exists' "\$makeconf" && [ -f "\$conf_dir/local.mk" ]; then
    read="\$read \$conf_dir/local.mk"
    name=\$name-cond
fi
case \${CROSS_BULK_TEST_ENV:-base} in
    base) ;;
    *) name=\$name-\$CROSS_BULK_TEST_ENV ;;
esac
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
    env BMAKE=$ports/scripts/tests/cross-bulk-bmake-proxy.sh CROSS_BULK_TEST_REAL_BMAKE=$out/bmake \
        MAKECONF=$out/config/main/mk.conf PKGSRCDIR=$out/tree CROSS_BULK_CPUS=4 CROSS_BULK_JOBS=2 \
        CROSS_BULK_TEST_ENV=base "$@" \
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
# Parent directories of external configs remain watched conservatively.
: > "$out/config/main/unrelated.tmp"
bulk
[ "$(parsed)" = 'a b ' ] && [ -z "$(built)" ] ||
    fail "a new external sibling did not requery without rebuilding: $(parsed), built $(built)"
# A different selected MAKECONF must not reuse the first file list or values.
bulk MAKECONF=$out/config/main/mk-alt.conf
[ "$(parsed)" = 'a b ' ] && [ "$(built)" = 'a b ' ] ||
    fail "after selecting a different MAKECONF: parsed $(parsed), built $(built)"
# Returning to an unchanged prior context can reuse its earlier answer.
bulk
[ -z "$(parsed)" ] && [ -z "$(built)" ] ||
    fail "returning to unchanged MAKECONF reparsed: $(parsed), built $(built)"
# A missing optional include is absent from .MAKE.MAKEFILES; its appearance
# must still invalidate the answer using the cached external-directory policy.
bulk MAKECONF=$out/config/optional/mk.conf
[ "$(parsed)" = 'a b ' ] || fail "selecting optional-include MAKECONF did not query: $(parsed)"
: > "$out/config/optional/local.mk"
bulk MAKECONF=$out/config/optional/mk.conf
[ "$(parsed)" = 'a b ' ] && [ "$(built)" = 'a b ' ] ||
    fail "an external optional include did not invalidate the cache: parsed $(parsed), built $(built)"
# A continued conditional include must also retain its external parent watch.
bulk MAKECONF=$out/config/conditional/mk.conf
[ "$(parsed)" = 'a b ' ] || fail "selecting continued conditional MAKECONF did not query: $(parsed)"
: > "$out/config/conditional/local.mk"
bulk MAKECONF=$out/config/conditional/mk.conf
[ "$(parsed)" = 'a b ' ] && [ "$(built)" = 'a b ' ] ||
    fail "a continued conditional include did not invalidate the cache: parsed $(parsed), built $(built)"
# The pkgsrc root itself is a watched parent for a reported makefile.
bulk CROSS_BULK_TEST_ROOT_MAKEFILE=yes
[ "$(parsed)" = 'a b ' ] || fail "selecting pkgsrc-root makefile did not query: $(parsed)"
: > "$out/tree/new-root.mk"
touch -t 203001010000 "$out/tree"
bulk CROSS_BULK_TEST_ROOT_MAKEFILE=yes
[ "$(parsed)" = 'a b ' ] && [ -z "$(built)" ] ||
    fail "a new sibling of a pkgsrc-root makefile did not requery without rebuilding: parsed $(parsed), built $(built)"
# The effective environment participates in the build query context.
bulk CROSS_BULK_TEST_ENV=one
[ "$(parsed)" = 'a b ' ] && [ "$(built)" = 'a b ' ] ||
    fail "after changing the effective environment: parsed $(parsed), built $(built)"
bulk CROSS_BULK_TEST_ENV=one
[ -z "$(parsed)" ] && [ -z "$(built)" ] ||
    fail "unchanged effective environment reparsed: $(parsed), built $(built)"
bulk CROSS_BULK_TEST_ENV=two
[ "$(parsed)" = 'a b ' ] && [ "$(built)" = 'a b ' ] ||
    fail "after a second effective environment change: parsed $(parsed), built $(built)"
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
echo 'PASS: vars cache keys bind MAKECONF and environment; external and pkgsrc parent changes, included files, local new files and disabled caching invalidate as expected'
