#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Removing an old WRKDIR is off the critical
# path of a cross bulk build. With a recording bmake whose clean step is a
# slow removal of an existing WRKDIR: build renames each old WRKDIR into
# WRKOBJDIR/.cross-bulk-trash (same file system), so no worker waits for
# a removal and the WRKDIR path is free when the package builds; one
# background deleter removes the trash, including what a crashed run left,
# never follows a symbolic link out of the trash, and stops with the build.
# No clean step runs for a WRKDIR that went to the trash: it would only
# parse the package again.
# Usage: cross-bulk-trash.sh NEW_OUTPUT
set -eu
[ "$#" = 1 ] || { echo 'Usage: cross-bulk-trash.sh NEW_OUTPUT' >&2; exit 2; }
out=$1
case "$out" in /*) ;; *) echo 'NEW_OUTPUT must be absolute' >&2; exit 2 ;; esac
case "$out" in *[!A-Za-z0-9_./-]*) echo 'Use simple paths.' >&2; exit 2 ;; esac
[ ! -e "$out" ] || exit 2
ports=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd -P)
mkdir -p "$out/tree/t/a" "$out/tree/t/b" "$out/tree/t/c" "$out/packages/All" "$out/work" \
    "$out/target-db" "$out/outside" "$out/outside2"
: > "$out/errors"
: > "$out/outside/keep"
: > "$out/outside2/keep"
# Old WRKDIRs, one with a read-only directory and a link out of the tree.
for p in a b c; do
    w=$out/work/t-$p
    mkdir -p "$w/ro"
    : > "$w/old"
    : > "$w/ro/file"
    chmod 555 "$w/ro"
    ln -s "$out/outside" "$w/link"
done
# What a crashed run left in the trash: a tree and a link out of it.
mkdir -p "$out/work/.cross-bulk-trash/19700101000000.1.t_x/sub"
: > "$out/work/.cross-bulk-trash/19700101000000.1.t_x/sub/file"
ln -s "$out/outside2" "$out/work/.cross-bulk-trash/19700101000000.2.link"
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
w=\$out/work/t-\$pkg
case "\$target" in
    show-var)
        case "\$varname" in
            EMBERBSD_NATIVE_TOOLSET_VERIFIED) echo fake ;;
            PACKAGES) echo \$out/packages ;;
            NATIVE_PKG_ADD_CMD) echo \$out/pkg_add ;;
            PKG_INFO) echo "\$out/pkg_info" ;;
            WRKOBJDIR) echo \$out/work ;;
            *) echo ;;
        esac ;;
    show-vars)
        for v in \$varnames; do
            case "\$v" in
                PKGNAME) echo "\$pkg-1.0" ;;
                PKGBASE) echo "\$pkg" ;;
                WRKDIR) echo "\$w" ;;
                *) echo ;;
            esac
        done ;;
    clean)
        # A slow file system: removing a real tree takes seconds.
        if [ -e "\$w" ]; then
            echo "SLOW-RM \$pkg" >> \$out/slow-rm
            sleep 3
            chmod -R u+w "\$w"; rm -rf "\$w"
        fi ;;
    depends) ;;
    package)
        [ ! -e "\$w/old" ] || echo "OLD WRKDIR of \$pkg at build" >> \$out/errors
        mkdir -p "\$w"; : > "\$w/new"; sleep 2 ;;
    package-install)
        \$add -K \$out/target-db \$pkg; : > \$out/packages/All/\$pkg-1.0.tgz ;;
    *) echo "UNKNOWN \$target" >> \$out/errors; exit 1 ;;
esac
WRAP
chmod +x "$out/bmake" "$out/pkg_add" "$out/pkg_info"
fail() { echo "FAIL: $*" >&2; exit 1; }
printf '%s\n' t/a t/b t/c > "$out/list"
mkdir "$out/state"
printf '%s\n' t/a t/b t/c > "$out/state/order"
printf '%s\n' 't/a t/a' 't/b t/b' 't/c t/c' > "$out/state/edges"
BMAKE=$out/bmake MAKECONF=$out/mk.conf PKGSRCDIR=$out/tree CROSS_BULK_CPUS=4 CROSS_BULK_JOBS=2 \
    sh "$ports/scripts/cross-bulk.sh" build "$out/list" "$out/state" > "$out/build.log" 2>&1 ||
    fail "build: $(cat "$out/build.log")"
[ ! -s "$out/errors" ] || fail "$(cat "$out/errors")"
[ ! -s "$out/slow-rm" ] 2> /dev/null || fail "a worker waited for the removal of an old WRKDIR: $(cat "$out/slow-rm" | tr '\n' ' ')"
[ "$(cut -d ' ' -f 1 "$out/state/done" | sort | tr '\n' ' ')" = 't/a t/b t/c ' ] || fail "done: $(cat "$out/state/done")"
for p in a b c; do [ -f "$out/work/t-$p/new" ] || fail "t/$p has no new WRKDIR"; done
grep -q ' clean$' "$out/calls" && fail "a clean step ran for a WRKDIR in the trash: $(grep ' clean$' "$out/calls" | tr '\n' ' ')"
# The build ran its deleter: the trash, also what a crashed run left, is
# gone, nothing outside it is, and no deleter outlives the build.
[ -z "$(ls -A "$out/work/.cross-bulk-trash")" ] || fail "trash not removed: $(ls -A "$out/work/.cross-bulk-trash" | tr '\n' ' ')"
[ -e "$out/outside/keep" ] && [ -e "$out/outside2/keep" ] || fail 'the deleter removed a file outside the trash'
ps -A -o command= | grep -F "$out/list" | grep -v grep > /dev/null && fail 'a deleter outlived the build'
[ ! -d "$out/work/t-x" ] || fail 'unexpected WRKDIR'
echo 'PASS: old WRKDIRs go to a trash on the same file system, no worker waits for a removal, the deleter removes only the trash and also what a crashed run left'
