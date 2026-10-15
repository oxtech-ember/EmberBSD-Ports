#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Accept an installed package on a test filesystem.
set -eu
LC_ALL=C
export LC_ALL
umask 077
[ "$#" -eq 3 ] || { echo "Usage: $0 PREFIX NEW_OUTPUT CROSS_BUILT_CONSUMER" >&2; exit 2; }
prefix=$1
output=$2
consumer=$3
case "$prefix:$output:$consumer" in /*:/*:/*) ;; *) echo 'Use absolute paths' >&2; exit 2 ;; esac
info=${PKG_INFO:-pkg_info}
admin=${PKG_ADMIN:-pkg_admin}
command -v "$info" >/dev/null
command -v "$admin" >/dev/null
mkdir "$output"
cd "$output"
"$info" -e attr-2.6.0nb1 > package.log
"$admin" check attr-2.6.0nb1 > package-check.log 2>&1
for op in get set; do
    [ "$(readlink "$prefix/man/man3/attr_${op}f.3")" = "attr_attr_${op}.3" ]
    [ -f "$prefix/man/man3/attr_attr_${op}.3" ]
done
for tool in getfattr setfattr; do
    "$prefix/bin/$tool" --version >> versions.log
done
# Exit 77 means this filesystem cannot support the requested acceptance.
"$consumer" "$output/api-source" "$output/api-destination" > consumer.log 2>&1
mkdir tree
: > tree/file
# The legacy attr CLI has no --version option. Exercise its real interface.
"$prefix/bin/attr" -q -s ember-legacy -V legacy-value tree/file
"$prefix/bin/attr" -q -g ember-legacy tree/file > legacy.value
[ "$(cat legacy.value)" = legacy-value ]
"$prefix/bin/attr" -q -l tree/file > legacy-list.log
grep -qx ember-legacy legacy-list.log
"$prefix/bin/attr" -q -r ember-legacy tree/file
legacy_status=0
"$prefix/bin/attr" -q -g ember-legacy tree/file > legacy-removed.value 2> legacy-removed.log || legacy_status=$?
[ "$legacy_status" -eq 1 ] || { echo 'Legacy removed-attribute read returned an unexpected status' >&2; exit 1; }
grep -Eq 'No such attribute|Attribute not found|No data available' legacy-removed.log
ln -s file tree/link
"$prefix/bin/setfattr" -n user.ember-cli -v target-value tree/file
"$prefix/bin/getfattr" --only-values -n user.ember-cli tree/file > ordinary.value
[ "$(cat ordinary.value)" = target-value ]
# A nofollow read must never return the target's attribute through the symlink.
get_status=0
"$prefix/bin/getfattr" -h --only-values -n user.ember-cli tree/link > nofollow-get.value 2> nofollow-get.log || get_status=$?
[ "$get_status" -eq 1 ] || { echo 'nofollow get returned an unexpected status' >&2; exit 1; }
grep -Eq 'Operation not supported|Not supported|Function not implemented|Operation not permitted|No such attribute|Attribute not found|No data available' nofollow-get.log
list_status=0; "$prefix/bin/getfattr" -h -d -m user.ember-cli tree/link > nofollow-list.log 2>&1 || list_status=$?
[ "$list_status" -eq 0 ] || { [ "$list_status" -eq 1 ] && grep -Eq "Operation not supported|Not supported|Function not implemented|Operation not permitted" nofollow-list.log; }
if grep 'user.ember-cli=' nofollow-list.log; then
    echo 'nofollow list reached the target attribute' >&2
    exit 1
fi
# Only ordinary unsupported-operation errors are accepted for symlink xattrs.
symlink_operation() {
    log=$1
    shift
    status=0
    "$@" > "$log" 2>&1 || status=$?
    if [ "$status" -ne 0 ]; then
        [ "$status" -eq 1 ] || return "$status"
        grep -Eq 'Operation not supported|Not supported|Function not implemented|Operation not permitted|No such attribute|Attribute not found|No data available' "$log"
    fi
}
# Symlink xattrs can be unsupported. Either result must preserve the target.
symlink_operation nofollow-set.log "$prefix/bin/setfattr" -h -n user.ember-cli -v link-value tree/link
"$prefix/bin/getfattr" --only-values -n user.ember-cli tree/file > after-set.value
cmp ordinary.value after-set.value
symlink_operation nofollow-remove.log "$prefix/bin/setfattr" -h -x user.ember-cli tree/link
"$prefix/bin/getfattr" --only-values -n user.ember-cli tree/file > after-remove.value
cmp ordinary.value after-remove.value
"$prefix/bin/getfattr" -R -P -h -d -m user.ember-cli tree > recursive.log
[ "$(grep -c 'user.ember-cli="target-value"' recursive.log)" -eq 1 ]
# A physical restore cannot silently degrade when openat2 is absent.
printf '# file: tree/file\nuser.ember-cli="changed"\n\n' > physical-restore.dump
restore_status=0
"$prefix/bin/setfattr" --restore=physical-restore.dump -P > physical-restore.log 2>&1 || restore_status=$?
[ "$restore_status" -eq 1 ] || { echo 'Physical restore returned an unexpected status' >&2; exit 1; }
grep -q 'Function not implemented' physical-restore.log
"$prefix/bin/getfattr" --only-values -n user.ember-cli tree/file > after-restore.value
cmp ordinary.value after-restore.value
"$prefix/bin/setfattr" -x user.ember-cli tree/file
removed_status=0
"$prefix/bin/getfattr" --only-values -n user.ember-cli tree/file > removed.value 2> removed.log || removed_status=$?
[ "$removed_status" -eq 1 ] || { echo 'Removed-attribute read returned an unexpected status' >&2; exit 1; }
grep -Eq 'No such attribute|Attribute not found|No data available' removed.log
echo 'PASS: installed attr package, libattr consumer, recursive CLI and nofollow target preservation'
