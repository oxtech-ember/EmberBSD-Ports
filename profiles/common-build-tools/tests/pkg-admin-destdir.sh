#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), pkg_admin alternate-root index regression.
set -eu

[ "$#" = 3 ] || {
    echo "Usage: $0 ORIGINAL_PKG_ADMIN FIXED_PKG_ADMIN NEW_WORK" >&2
    exit 2
}
original=$1
fixed=$2
work=$3
for path do
    case "$path" in /*) ;; *) exit 2 ;; esac
    case "$path" in *[!a-zA-Z0-9_./-]*) exit 2 ;; esac
done
[ ! -e "$work" ] || { echo "Work path already exists: $work" >&2; exit 2; }
mkdir -p "$work"

make_record()
{
    root=$1
    pkg=$2
    mode=$3
    db=$root/usr/pkg/pkgdb
    mkdir -p "$db/$pkg"
    case "$mode" in
    rebuild-present|add-present)
        leaf=$mode
        mkdir -p "$root/usr/pkg/bin"
        : > "$root/usr/pkg/bin/$leaf"
        {
            printf '@name %s\n' "$pkg"
            printf '@cwd /usr/pkg\n'
            printf 'bin/%s\n' "$leaf"
        } > "$db/$pkg/+CONTENTS"
        ;;
    rebuild-missing|add-missing)
        leaf=$mode
        {
            printf '@name %s\n' "$pkg"
            printf '@cwd /usr/pkg\n'
            printf 'bin/%s\n' "$leaf"
        } > "$db/$pkg/+CONTENTS"
        ;;
    rebuild-dbdir|add-dbdir)
        : > "$db/$pkg/meta-entry"
        {
            printf '@name %s\n' "$pkg"
            printf '@cwd .\n'
            printf 'meta-entry\n'
        } > "$db/$pkg/+CONTENTS"
        ;;
    *)
        echo "Unknown fixture mode: $mode" >&2
        exit 2
        ;;
    esac
}

assert_owner()
{
    dump=$1
    path=$2
    pkg=$3
    grep -Fx "file: $path pkg: $pkg" "$dump" >/dev/null
}

assert_no_owner()
{
    dump=$1
    path=$2
    if grep -F "file: $path pkg:" "$dump" >/dev/null; then
        echo "Unexpected owner for $path" >&2
        exit 1
    fi
}

# The pristine command must reject -P. This checks that the fixture detects the
# missing option without relying on files that may exist on the host.
root=$work/pristine-root
mkdir -p "$root/usr/pkg/pkgdb"
if "$original" -K "$root/usr/pkg/pkgdb" -P "$root" rebuild \
    > "$work/pristine-rebuild.log" 2>&1; then
    echo "Pristine pkg_admin unexpectedly accepted -P" >&2
    exit 1
fi
if "$original" -K "$root/usr/pkg/pkgdb" -P "$root" add nowhere \
    > "$work/pristine-add.log" 2>&1; then
    echo "Pristine pkg_admin unexpectedly accepted -P for add" >&2
    exit 1
fi

# Rebuild against a staged root. Only target paths belong in the B-tree.
root=$work/rebuild-root
db=$root/usr/pkg/pkgdb
make_record "$root" ember-rebuild-present-1.0 rebuild-present
make_record "$root" ember-rebuild-missing-1.0 rebuild-missing
make_record "$root" ember-rebuild-dbdir-1.0 rebuild-dbdir
"$fixed" -K "$db" -P "$root/" rebuild > "$work/rebuild.log" 2>&1
"$fixed" -K "$db" dump > "$work/rebuild.dump"
assert_owner "$work/rebuild.dump" /usr/pkg/bin/rebuild-present ember-rebuild-present-1.0
assert_owner "$work/rebuild.dump" /usr/pkg/pkgdb/ember-rebuild-dbdir-1.0/meta-entry ember-rebuild-dbdir-1.0
assert_no_owner "$work/rebuild.dump" /usr/pkg/bin/rebuild-missing
assert_no_owner "$work/rebuild.dump" "$root/usr/pkg/bin/rebuild-present"

# The add subcommand must use the same rooted existence check and key format.
root=$work/add-root
db=$root/usr/pkg/pkgdb
make_record "$root" ember-add-present-1.0 add-present
make_record "$root" ember-add-missing-1.0 add-missing
make_record "$root" ember-add-dbdir-1.0 add-dbdir
"$fixed" -K "$db" -P "$root" add \
    ember-add-present-1.0 ember-add-missing-1.0 ember-add-dbdir-1.0 \
    > "$work/add.log" 2>&1
"$fixed" -K "$db" dump > "$work/add.dump"
assert_owner "$work/add.dump" /usr/pkg/bin/add-present ember-add-present-1.0
assert_owner "$work/add.dump" /usr/pkg/pkgdb/ember-add-dbdir-1.0/meta-entry ember-add-dbdir-1.0
assert_no_owner "$work/add.dump" /usr/pkg/bin/add-missing
assert_no_owner "$work/add.dump" "$root/usr/pkg/bin/add-present"

# A DESTDIR longer than an unrelated -K path must not read past the db path.
root=$work/long-destdir-root-that-is-longer-than-the-package-database-path
db=$work/db
pkg=ember-long-destdir-1.0
mkdir -p "$db/$pkg"
printf '@name %s\n@cwd .\n' "$pkg" > "$db/$pkg/+CONTENTS"
"$fixed" -K "$db" -P "$root" add "$pkg" > "$work/long-destdir.log" 2>&1
"$fixed" -K "$db" dump > "$work/long-destdir.dump"
[ ! -s "$work/long-destdir.dump" ] || {
    echo 'Unexpected ownership entry for an empty package' >&2
    exit 1
}

echo 'PASS: pkg_admin rebuild/add checks DESTDIR files and stores target-path keys'
