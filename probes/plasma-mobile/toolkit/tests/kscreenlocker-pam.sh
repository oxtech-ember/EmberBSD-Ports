#!/bin/sh
# Exercise the generated pkgsrc scripts without installing target binaries.
# Usage: sh kscreenlocker-pam.sh ABSOLUTE_PKGINSTALL_DIR ABSOLUTE_KDE_PAM NEW_OUTPUT
set -eu

[ "$#" -eq 3 ] || {
	echo "usage: $0 ABSOLUTE_PKGINSTALL_DIR ABSOLUTE_KDE_PAM NEW_OUTPUT" >&2
	exit 2
}
scripts=$1
example=$2
output=$3
for path in "$scripts" "$example" "$output"; do
	case "$path" in
	/*) ;;
	*) echo "paths must be absolute: $path" >&2; exit 2 ;;
	esac
done
[ -f "$scripts/INSTALL" ] && [ -f "$scripts/DEINSTALL" ]
[ -f "$example" ]
[ ! -e "$output" ] || {
	echo "output already exists: $output" >&2
	exit 2
}

# The default recipe paths are relative to PKG_PREFIX. Reject other metadata
# before executing scripts, so this check cannot write to a real PAM directory.
awk '
/^# DIR: / && $3 != "etc" && $3 != "etc\/pam.d" { bad = 1 }
/^# FILE: / {
	if ($3 != "etc\/pam.d\/kde" || $4 != "c" ||
	    $5 != "share\/examples\/pam.d\/kde" || $6 != "0644") bad = 1
	files++
}
END { exit bad || files != 1 }
' "$scripts/INSTALL"

mkdir -p "$output/pkgdb/plasma6-kscreenlocker" "$output/prefix/share/examples/pam.d"
cp "$scripts/INSTALL" "$scripts/DEINSTALL" "$output/pkgdb/plasma6-kscreenlocker/"
cp "$example" "$output/prefix/share/examples/pam.d/kde"
PKG_PREFIX=$output/prefix
PKG_DBDIR=$output/pkgdb
PKG_METADATA_DIR=$PKG_DBDIR/plasma6-kscreenlocker
PKG_REFCOUNT_DBDIR=$output/refcount
PKG_CONFIG=yes
export PKG_PREFIX PKG_DBDIR PKG_METADATA_DIR PKG_REFCOUNT_DBDIR PKG_CONFIG
cd "$PKG_METADATA_DIR"

install_config()
{
	sh ./INSTALL plasma6-kscreenlocker PRE-INSTALL
	sh ./INSTALL plasma6-kscreenlocker POST-INSTALL
}

remove_config()
{
	sh ./DEINSTALL plasma6-kscreenlocker DEINSTALL
	sh ./DEINSTALL plasma6-kscreenlocker POST-DEINSTALL
}

install_config > "$output/install.log" 2>&1
cmp "$example" "$PKG_PREFIX/etc/pam.d/kde"
remove_config > "$output/remove.log" 2>&1
[ ! -e "$PKG_PREFIX/etc/pam.d/kde" ]
[ ! -d "$PKG_PREFIX/etc/pam.d" ]
echo "PASS: fresh install and default configuration removal"

install_config > "$output/reinstall.log" 2>&1
cmp "$example" "$PKG_PREFIX/etc/pam.d/kde"
printf '%s\n' '# Local PAM policy must survive package removal and reinstall.' \
	> "$output/local-policy"
cp "$output/local-policy" "$PKG_PREFIX/etc/pam.d/kde"
remove_config > "$output/remove-modified.log" 2>&1
cmp "$output/local-policy" "$PKG_PREFIX/etc/pam.d/kde"
install_config > "$output/reinstall-modified.log" 2>&1
cmp "$output/local-policy" "$PKG_PREFIX/etc/pam.d/kde"
echo "PASS: reinstall and local configuration preservation"
