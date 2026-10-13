#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), actual pkgsrc file-check dependencies.
# Input PKGSRC must not contain pkgsrc-check-error-dir.patch yet.
# Use serial bmake: pkgsrc mk/misc/common.mk rejects infrastructure -j jobs.
# This test copies two make fragments. It does not build or install packages.
set -eu

[ "$#" = 2 ] || {
    echo "Usage: $0 PKGSRC NEW_WORK" >&2
    exit 2
}
pkgsrc=$(CDPATH= cd -- "$1" && pwd)
profile=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bmake=${BMAKE:-bmake}
patch=${PATCH:-patch}
command -v "$bmake" >/dev/null 2>&1 || {
    echo 'A BSD make executable is required. Set BMAKE.' >&2
    exit 2
}
# The upstream check-files fragment does not quote these make target paths.
case "$2" in
    *[!A-Za-z0-9_./-]*) echo 'NEW_WORK must contain only portable path characters.' >&2; exit 2 ;;
esac
mkdir "$2"
work=$(CDPATH= cd -- "$2" && pwd)
export LC_ALL=C

for variant in original patched; do
    mkdir -p "$work/$variant/mk/check"
    cp "$pkgsrc/mk/bsd.pkg.error.mk" "$work/$variant/mk/"
    cp "$pkgsrc/mk/check/check-files.mk" "$work/$variant/mk/check/"
done
(cd "$work/patched" && "$patch" -F0 -p1 \
    < "$profile/patches/pkgsrc-check-error-dir.patch") > "$work/patch.log" 2>&1

# Record actual directory creation. Do not create missing directories here.
cat > "$work/mkdir.sh" <<'EOF'
#!/bin/sh
set -eu
printf '%s\n' "$@" >> "$DIR_LOG"
exec mkdir -p "$@"
EOF

cat > "$work/fixture.mk" <<'EOF'
WRKDIR= ${CASE}/work
DESTDIR= ${CASE}/dest
PREFIX= /usr/pkg
LOCALBASE= ${PREFIX}
PKG_SYSCONFDIR= /etc
VARBASE= /var
PKG_DBDIR= ${PREFIX}/pkgdb
DISTDIR= /distfiles
PACKAGES= /packages
PERL5_INSTALLARCHLIB= ${PREFIX}/lib/perl
PLIST= ${CASE}/PLIST
PKGNAME= check-error-dir-1.0
CHECK_FILES= yes
CHECK_FILES_SUPPORTED= yes
CHECK_FILES_STRICT= yes
CHECK_FILES_ONLY_PREFIX= yes
ICON_THEMES= no
USE_CROSS_COMPILE= no
RUN= @set -e;
MKDIR= sh ${FIXTURE}/mkdir.sh
RM= rm
ECHO= echo
TEST= test
CAT= cat
MV= mv
FIND= find
SED= sed
GREP= grep
SORT= sort
DIFF= diff
CMP= cmp
TRUE= true
STEP_MSG= echo
DO_NADA= true
WARNING_CAT= sed -e 's|^|WARNING: |' 1>&2
ERROR_CAT= sed -e 's|^|ERROR: |' 1>&2
_NONZERO_FILESIZE_P= awk 'END { exit (NR > 0) ? 0 : 1; }'
.include "${FRAGMENTS}/mk/bsd.pkg.error.mk"
.include "${FRAGMENTS}/mk/check/check-files.mk"
.PHONY: plist
plist:
	@test -f ${PLIST}
EOF

fail()
{
    echo "$*" >&2
    exit 1
}

run_make()
{
    DIR_LOG="$case_dir/mkdir.log" "$bmake" -r -f "$work/fixture.mk" \
        FIXTURE="$work" FRAGMENTS="$work/$variant" CASE="$case_dir" "$@"
}

prepare_case()
{
    case_dir=$work/$variant-$case_name
    mkdir -p "$case_dir/work" "$case_dir/dest/usr/pkg/bin" \
        "$case_dir/dest/etc" "$case_dir/dest/var"
    printf '%s\n' 'bin/listed' > "$case_dir/PLIST"
    printf '%s\n' 'cached build marker' > "$case_dir/work/.build_done"
    cp "$case_dir/work/.build_done" "$case_dir/build-before"
    run_make makedirs check-files-pre > "$case_dir/prepare.log" 2>&1
    if [ "$case_name" != missing ]; then
        printf '%s\n' 'payload' > "$case_dir/dest/usr/pkg/bin/listed"
    fi
    case "$case_name" in
        extra) : > "$case_dir/dest/usr/pkg/bin/unlisted" ;;
        sysconfdir) : > "$case_dir/dest/etc/unlisted.conf" ;;
        varbase) : > "$case_dir/dest/var/unlisted" ;;
        only-prefix) mkdir "$case_dir/dest/opt"; : > "$case_dir/dest/opt/unlisted" ;;
    esac
    run_make check-files-post > "$case_dir/post.log" 2>&1
    run_make error-clean > "$case_dir/clean.log" 2>&1
    [ ! -e "$case_dir/work/.error" ] || fail 'error-clean left ERROR_DIR'
    [ ! -e "$case_dir/work/.warning" ] || fail 'error-clean left WARNING_DIR'
    [ -f "$case_dir/work/.check-files.prefix.pre" ] || fail 'Missing cached pre-list'
    [ -f "$case_dir/work/.check-files.prefix.post" ] || fail 'Missing cached post-list'
    : > "$case_dir/mkdir.log"
}

variant=original case_name=valid
prepare_case
if run_make check-files > "$case_dir/check.log" 2>&1; then
    fail 'Original fragments did not reproduce the missing ERROR_DIR failure'
fi
grep -E 'cannot create|No such file|nonexistent directory' "$case_dir/check.log" >/dev/null
grep -F '.error/check-files-' "$case_dir/check.log" >/dev/null
[ ! -s "$case_dir/mkdir.log" ] || fail 'Original check unexpectedly created a directory'

variant=patched
for case_name in valid extra missing sysconfdir varbase only-prefix; do
    prepare_case
    if run_make check-files > "$case_dir/check.log" 2>&1; then
        [ "$case_name" = valid ] || fail "Invalid $case_name payload passed"
    else
        [ "$case_name" != valid ] || { cat "$case_dir/check.log" >&2; fail 'Valid payload failed'; }
    fi
    [ -d "$case_dir/work/.error" ] || fail 'Directory prerequisite was not built'
    [ "$(wc -l < "$case_dir/mkdir.log" | tr -d ' ')" = 1 ] || fail 'Directory was created more than once'
    grep -Fx "$case_dir/work/.error" "$case_dir/mkdir.log" >/dev/null
    cmp "$case_dir/build-before" "$case_dir/work/.build_done"
    case "$case_name" in
        valid) [ ! -s "$case_dir/work/.error/check-files-prefix" ] ;;
        extra) grep -F 'but not in the PLIST:' "$case_dir/work/.error-done/check-files-prefix" >/dev/null ;;
        missing) grep -F 'PLIST but not in' "$case_dir/work/.error-done/check-files-prefix" >/dev/null ;;
        sysconfdir) grep -F 'modified /etc contents directly!' "$case_dir/work/.error-done/check-files-sysconfdir" >/dev/null ;;
        varbase) grep -F 'modified /var contents directly!' "$case_dir/work/.error-done/check-files-varbase" >/dev/null ;;
        only-prefix) grep -F 'outside /usr/pkg:' "$case_dir/work/.error-done/check-files-only-prefix" >/dev/null ;;
    esac
done

# A standalone writer must also recreate ERROR_DIR, without a makedirs call.
case_dir=$work/patched-valid
for scope in prefix sysconfdir varbase only-prefix; do
    run_make error-clean > "$case_dir/direct-$scope-clean.log" 2>&1
    : > "$case_dir/mkdir.log"
    run_make "$case_dir/work/.error/check-files-$scope" \
        > "$case_dir/direct-$scope.log" 2>&1
    [ -f "$case_dir/work/.error/check-files-$scope" ] || fail "Missing direct $scope result"
    [ ! -s "$case_dir/work/.error/check-files-$scope" ] || fail "Invalid direct $scope result"
    [ "$(wc -l < "$case_dir/mkdir.log" | tr -d ' ')" = 1 ] || fail 'Direct check recreated a directory more than once'
done

echo 'PASS: original failure, cached checks, one directory prerequisite, direct writers and five rejected payloads'
