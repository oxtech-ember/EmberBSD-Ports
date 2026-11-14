#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
# A bulk build records the build inputs of a new work directory. When only
# PKGREVISION changes later, the kept objects are repackaged through the
# stage-local metadata path without clean or compilation, for target and
# native nodes. A revision change with changed inputs, or without a record,
# still preserves the work directory and stops.
set -eu
[ "$#" = 1 ] || { echo 'Usage: cross-bulk-revision-metadata.sh NEW_OUTPUT' >&2; exit 2; }
out=$1
case "$out" in /*) ;; *) echo 'NEW_OUTPUT must be absolute' >&2; exit 2 ;; esac
case "$out" in *[!A-Za-z0-9_./-]*) echo 'Use simple paths.' >&2; exit 2 ;; esac
[ ! -e "$out" ] || exit 2
ports=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd -P)
selected_shell=${CROSS_BULK_TEST_SHELL:-$(command -v sh)}
host_python=${CROSS_BULK_TEST_PYTHON:-$(command -v python3)}
: "${CROSS_BULK_TEST_SDK_SOURCE:?Set CROSS_BULK_TEST_SDK_SOURCE to the selected SDK source}"
mkdir -p "$out/tree/pkgtools/pkg_install" "$out/tree/cat/demo/patches" "$out/tree/mk" \
    "$out/packages/All" "$out/packages-native/All" "$out/native-db" "$out/target-db" \
    "$out/state/logs" "$out/sdk/scripts"
ln -s "$CROSS_BULK_TEST_SDK_SOURCE/src" "$out/sdk/src"
printf 'print(2)\n' > "$out/sdk/scripts/resolve-jobs.py"
: > "$out/mk.conf"
: > "$out/tree/pkgtools/pkg_install/Makefile"
printf '%s\n' '# shared infrastructure' > "$out/tree/mk/bsd.pkg.mk"
cat > "$out/tree/cat/demo/Makefile" <<'MK'
DISTNAME=	demo-1.0
PKGREVISION=	1
.include "../../mk/bsd.pkg.mk"
MK
printf '%s\n' '--- a/demo.c' '+++ b/demo.c' > "$out/tree/cat/demo/patches/patch-demo.c"
cat > "$out/pkg_info" <<'WRAP'
#!/bin/sh
exit 1
WRAP
cat > "$out/bmake" <<WRAP
#!/bin/sh
out=$out
dir= target= varname= varnames= native=no stage=no queries=
for a do echo "\$a" >> "$out/calls"; done
while [ "\$#" -gt 0 ]; do
    case "\$1" in
        -C) dir=\$2; shift 2 ;;
        -V) queries="\$queries \$2"; target=query; shift 2 ;;
        VARNAME=*) varname=\${1#VARNAME=}; shift ;;
        VARNAMES=*) varnames=\${1#VARNAMES=}; shift ;;
        USE_CROSS_COMPILE=no) native=yes; shift ;;
        _EMBER_STAGE_LOCAL_PACKAGE_INSTALL=yes) stage=yes; shift ;;
        *=*) shift ;;
        *) target=\${target:+\$target }\$1; shift ;;
    esac
done
pkg=\${dir##*/}
rev=
[ ! -f "\$dir/Makefile" ] || rev=\$(sed -n 's/^PKGREVISION=[[:space:]]*//p' "\$dir/Makefile")
name=\$pkg-1.0\${rev:+nb\$rev}
work=$out/work/cat/\$pkg
[ "\$native" = no ] || work=$out/work-native/cat/\$pkg
case "\$target" in
    query)
        for v in \$queries; do
            case "\$v" in
                '\${WRKDIR}') echo "\$work" ;;
                '\${_COOKIE.tools}') echo "\$work/.tools_done" ;;
                '\${USE_TOOLS}') echo ;;
                *) exit 2 ;;
            esac
        done ;;
    show-var)
        case "\$varname" in
            EMBERBSD_NATIVE_TOOLSET_VERIFIED) echo fake ;;
            EMBERBSD_HOST_PYTHON) echo "$host_python" ;;
            EMBERBSD_SDK_SOURCE) echo "$out/sdk" ;;
            PACKAGES) echo "$out/packages" ;;
            PKG_INFO) if [ "\$native" = yes ]; then echo "$out/pkg_info -K $out/native-db"; else echo "$out/pkg_info -K $out/target-db"; fi ;;
            NATIVE_PKG_ADD_CMD) echo "$out/pkg_add" ;;
            *) echo ;;
        esac ;;
    show-vars)
        for v in \$varnames; do
            case "\$v" in
                OPSYS) echo NetBSD ;;
                MACHINE_ARCH) echo aarch64 ;;
                MACHINE_GNU_PLATFORM) echo aarch64--netbsd ;;
                EMBERBSD_HOST_PYTHON) echo "$host_python" ;;
                EMBERBSD_SDK_SOURCE) echo "$out/sdk" ;;
                PKGBASE) echo "\$pkg" ;;
                PKGNAME) echo "\$name" ;;
                PKGVERSION_NOREV) echo 1.0 ;;
                PKGPATH) echo "cat/\$pkg" ;;
                PKGFILE) if [ "\$native" = yes ]; then echo "$out/packages-native/All/\$name.tgz"; else echo "$out/packages/All/\$name.tgz"; fi ;;
                WRKDIR) echo "\$work" ;;
                WRKOBJDIR) echo "\${work%/cat/*}" ;;
                WRKSRC) echo "\$work/demo-1.0" ;;
                PATCHDIR) echo "\$dir/patches" ;;
                FILESDIR) echo "\$dir/files" ;;
                DISTINFO_FILE) echo "\$dir/distinfo" ;;
                CFLAGS) echo '-O2' ;;
                _COOKIE.configure) echo "\$work/.configure_done" ;;
                GNU_CONFIGURE) echo no ;;
                CONFIGURE_DIRS) echo "\$work/demo-1.0" ;;
                CONFIG_SHELL) echo /bin/sh ;;
                .MAKE.MAKEFILES) echo "\$dir/Makefile ../../mk/bsd.pkg.mk $out/mk.conf" ;;
                .CURDIR) echo "\$dir" ;;
                *) echo ;;
            esac
        done ;;
    clean) echo "TARGET clean \$native" >> "$out/targets"; rm -rf "\$work" ;;
    depends-clean*|_package-clean) for t in \$target; do echo "TARGET \$t \$native" >> "$out/targets"; done ;;
    package-install|package|install)
        echo "TARGET \$target \$native stage=\$stage" >> "$out/targets"
        mkdir -p "\$work"
        if [ ! -f "\$work/.build_done" ]; then
            echo "COMPILE \$name \$native" >> "$out/targets"
            echo "object of \$name" > "\$work/demo.o"
            for c in extract configure build; do echo "\$name" > "\$work/.\${c}_done"; done
        elif [ "\$(cat "\$work/.build_done")" != "\$name" ] && [ "\$stage" != yes ]; then
            echo "install-check-version refused \$name" >&2; exit 1
        fi
        echo "\$name" > "\$work/.install_done"
        echo "\$name" > "\$work/.package_done"
        if [ "\$native" = yes ]; then
            : > "$out/packages-native/All/\$name.tgz"; : > "$out/native-db/\$name"
        else
            : > "$out/packages/All/\$name.tgz"; : > "$out/target-db/\$name"
        fi ;;
    *) echo "unknown target: \$target" >&2; exit 2 ;;
esac
WRAP
chmod +x "$out/pkg_info" "$out/bmake"
printf '#!/bin/sh\nexit 0\n' > "$out/pkg_add"
chmod +x "$out/pkg_add"
fail() { echo "FAIL: $*" >&2; exit 1; }
target_work=$out/work/cat/demo
native_work=$out/work-native/cat/demo
bulk()
{
    env BMAKE="$out/bmake" MAKECONF="$out/mk.conf" PKGSRCDIR="$out/tree" \
        CROSS_BULK_SHELL="$selected_shell" CROSS_BULK_VARS_CACHE=no \
        CROSS_BULK_CPUS=2 CROSS_BULK_JOBS=1 \
        "$selected_shell" "$ports/scripts/cross-bulk.sh" build "$out/list" "$out/state" \
        > "$out/$1.log" 2>&1
}
revision() { sed "s/^PKGREVISION=.*/PKGREVISION=	$1/" "$out/tree/cat/demo/Makefile" > "$out/mk.tmp" && mv "$out/mk.tmp" "$out/tree/cat/demo/Makefile"; }
done_row() { awk -v p="$1" '$1 == p { n = $2 } END { print n }' "$out/state/done"; }
printf '%s\n' cat/demo cat/demo@native > "$out/list"
printf '%s\n' cat/demo cat/demo@native > "$out/state/order"
printf '%s\n' 'cat/demo cat/demo' 'cat/demo@native cat/demo@native' > "$out/state/edges"
: > "$out/state/done"

# A first build compiles and records the build inputs of both roles.
: > "$out/targets"
bulk first || fail "first build: $(cat "$out/first.log")"
[ "$(grep -c '^COMPILE demo-1.0nb1' "$out/targets")" -eq 2 ] || fail "first build did not compile both roles: $(cat "$out/targets")"
for w in "$target_work" "$native_work"; do
    grep -Eq '^cross-bulk-inputs-v1 [0-9a-f]{64}$' "$w/.cross-bulk-inputs" || fail "no build-input record in $w"
done
[ "$(done_row cat/demo)" = demo-1.0nb1 ] || fail 'target nb1 was not recorded done'
target_record=$(cat "$target_work/.cross-bulk-inputs")

# Only PKGREVISION changes: repackage both kept stages without clean or compile.
revision 2
: > "$out/targets"
bulk metadata || fail "metadata build: $(cat "$out/metadata.log") $(cat "$out/state/logs/"*.log)"
! grep -q '^COMPILE' "$out/targets" || fail "revision-only change compiled again: $(cat "$out/targets")"
! grep -q '^TARGET clean' "$out/targets" || fail 'revision-only change cleaned a kept stage'
grep -q '^TARGET depends-clean no$' "$out/targets" && grep -q '^TARGET _package-clean no$' "$out/targets" ||
    fail "target metadata was not reset: $(cat "$out/targets")"
grep -q '^TARGET package-install no stage=yes$' "$out/targets" || fail "target did not use the stage-local metadata path: $(cat "$out/targets")"
grep -q '^TARGET depends-clean yes$' "$out/targets" || fail "native metadata was not reset: $(cat "$out/targets")"
grep -q '^TARGET install yes stage=yes$' "$out/targets" || fail "native did not use the stage-local metadata path: $(cat "$out/targets")"
[ "$(cat "$target_work/demo.o")" = 'object of demo-1.0nb1' ] || fail 'kept target objects changed'
[ "$(cat "$native_work/demo.o")" = 'object of demo-1.0nb1' ] || fail 'kept native objects changed'
[ "$(done_row cat/demo)" = demo-1.0nb2 ] || fail 'target nb2 was not recorded done'
[ "$(done_row cat/demo@native)" = demo-1.0nb2 ] || fail 'native nb2 was not recorded done'
[ -f "$out/packages/All/demo-1.0nb2.tgz" ] || fail 'target nb2 package is missing'
[ "$(cat "$target_work/.cross-bulk-inputs")" = "$target_record" ] || fail 'metadata path changed the input record'
grep -q 'only the package revision changed' "$out/state/logs/cat_demo.log" || fail 'metadata path is not explained in the package log'

# PKGREVISION and a patch change: the stage is preserved and the build stops.
revision 3
printf '%s\n' '+changed' >> "$out/tree/cat/demo/patches/patch-demo.c"
: > "$out/targets"
rc=0
bulk changed || rc=$?
[ "$rc" -ne 0 ] || fail 'a revision change with changed inputs did not stop'
grep -q 'build inputs changed since this work directory was built' "$out/state/logs/"*worker.log ||
    fail "changed-input refusal is unclear: $(cat "$out/state/logs/"*worker.log)"
! grep -q '^TARGET' "$out/targets" || fail "changed inputs ran package targets: $(cat "$out/targets")"
[ "$(cat "$target_work/demo.o")" = 'object of demo-1.0nb1' ] || fail 'changed-input refusal touched target objects'

# A work directory without a record keeps the earlier explicit stop.
restored=$(sed '$d' "$out/tree/cat/demo/patches/patch-demo.c")
printf '%s\n' "$restored" > "$out/tree/cat/demo/patches/patch-demo.c"
rm -f "$target_work/.cross-bulk-inputs" "$native_work/.cross-bulk-inputs"
: > "$out/targets"
rc=0
bulk unrecorded || rc=$?
[ "$rc" -ne 0 ] || fail 'a revision change without a record did not stop'
grep -q 'no recorded build inputs for this work directory' "$out/state/logs/"*worker.log ||
    fail 'unrecorded refusal is unclear'
! grep -q '^TARGET' "$out/targets" || fail 'unrecorded stage ran package targets'
echo 'PASS: revision-only changes repackage kept target/native stages; changed or unrecorded inputs preserve and stop'
