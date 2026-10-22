#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD, AI-assisted current shell recipe export.
set -eu
[ "$#" = 1 ] || { echo 'Usage: prepare-pkgsrc.sh ABSOLUTE_NEW_DIRECTORY' >&2; exit 2; }
destination=$1
profile=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
root=$(CDPATH= cd -- "$profile/../.." && pwd)
for recipe in devel/editline devel/automake lang/perl5 shells/dash shells/mksh; do
    source=$profile/recipes/$recipe
    case "$recipe" in
        shells/mksh) source=$root/pkgsrc/local-shells/mksh ;;
        devel/automake) source=$root/pkgsrc/devel/automake ;;
        lang/perl5) source=$root/profiles/common-build-tools/recipes/lang/perl5 ;;
    esac
    for name in Makefile distinfo; do
        [ -s "$source/$name" ] || { echo "Missing $recipe/$name" >&2; exit 2; }
    done
    if [ "$recipe" != shells/dash ]; then
        for name in DESCR PLIST; do
            [ -s "$source/$name" ] || { echo "Missing $recipe/$name" >&2; exit 2; }
        done
    fi
    awk '/^SHA1 \(patch-/ {gsub(/[()]/, "", $2); print $2 " " $4}' "$source/distinfo" |
    while read -r name expected; do
        file=$source/patches/$name
        if [ ! -f "$file" ] && [ "$recipe" = shells/dash ]; then
            file=$root/upstream/pkgsrc/$recipe/patches/$name
        fi
        [ -f "$file" ] || { echo "Missing $recipe/$name" >&2; exit 2; }
        actual=$(sed '/[$]NetBSD.*/d' "$file" | shasum -a 1 | awk '{print $1}')
        [ "$actual" = "$expected" ] || { echo "Patch hash differs: $recipe/$name" >&2; exit 2; }
    done
done
sh "$root/scripts/prepare-pkgsrc.sh" "$destination" development-toolchain
patch -p1 -F0 -d "$destination" < "$root/profiles/common-build-tools/patches/current-libtool.patch"
for recipe in devel/editline; do
    rm -rf "$destination/$recipe"
    cp -R "$profile/recipes/$recipe" "$destination/$recipe"
done
rm -rf "$destination/lang/perl5"
cp -R "$root/profiles/common-build-tools/recipes/lang/perl5" "$destination/lang/perl5"
cp -R "$profile/recipes/shells/dash/." "$destination/shells/dash/"
rm -rf "$destination/shells/mksh"
cp -R "$root/pkgsrc/local-shells/mksh" "$destination/shells/mksh"
cat > "$destination/EMBERBSD-SHELLS-MK.CONF" <<'EOF'
.include "${.PARSEDIR}/EMBERBSD-DEVELOPMENT-MK.CONF"
.if defined(BSD_PKG_MK)
GCC_REQD+= 16.2
PERL5_REQD+= 5.44.0
PREFER.editline= pkgsrc
PREFER.ncurses= pkgsrc
BUILDLINK_API_DEPENDS.editline+= editline>=3.1.20260512
BUILDLINK_API_DEPENDS.ncurses+= ncurses>=6.6
.endif
EOF
echo "Prepared current shell recipes in $destination"
