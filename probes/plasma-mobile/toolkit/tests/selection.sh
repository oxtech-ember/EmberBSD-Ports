#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; AI-assisted toolkit selection regression.
set -eu
[ "$#" -eq 2 ] || { echo "Usage: $0 TOOLKIT_DIRECTORY NEW_WORK" >&2; exit 2; }
toolkit=$(CDPATH= cd -- "$1" && pwd)
mkdir "$2"
work=$(CDPATH= cd -- "$2" && pwd)
make=${BMAKE:-bmake}
command -v "$make" >/dev/null 2>&1 || {
    echo 'BSD make is required for the toolkit selection test.' >&2; exit 2;
}
# Test the production selection blocks. External pkgsrc includes are omitted:
# these cases check version/recipe selection, not full native recipe parsing.
sed '/^\.include /d' "$toolkit/shared/meta-pkgs/qt6/Makefile.common" > "$work/qt.mk"
sed '/^\.include /d' "$toolkit/shared/meta-pkgs/kde/kf6.mk" > "$work/kf.mk"
sed '/^\.include /d' "$toolkit/shared/meta-pkgs/kde/plasma6.mk" > "$work/plasma.mk"
cat > "$work/Makefile" <<'MAKE'
.include "${FAMILY}.mk"
all:
	@if test -n '${PKG_FAIL_REASON:U}'; then printf '%s\n' '${PKG_FAIL_REASON}'; exit 1; fi
	@test '${QTVERSION:U6.12.0}' = 6.12.0
	@test '${KF6VER:U6.31.0}' = 6.31.0
	@test '${PLASMAVER:U6.7.5}' = 6.7.5
	@test '${GCC_REQD}' = 16.2
MAKE
while IFS="$(printf '\t')" read -r recipe archive sha url; do
    case "$recipe" in ''|'#'*|security/qca2-qt6|security/libsecret|audio/libcanberra|devel/extra-cmake-modules|devel/libinotify|devel/plasma-wayland-protocols|textproc/aspell|textproc/hunspell|textproc/iso-codes|www/litehtml|www/gumbo-parser|sysutils/consolekit|x11/xdg-user-dirs|devel/SDL3|inputmethod/fcitx5|inputmethod/fcitx5-qt|inputmethod/fcitx5-configtool) continue ;; esac
    case "$recipe" in */qt6-*) family=qt ;; */plasma6-*) family=plasma ;; *) family=kf ;; esac
    (cd "$work" && "$make" -r -m / FAMILY="$family" PKGPATH="$recipe")
done < "$toolkit/sources.tsv"
for recipe in www/qt6-qtwebengine graphics/qt6-qt3d databases/qt6-psql; do
    if (cd "$work" && "$make" -r -m / FAMILY=qt PKGPATH="$recipe") > "$work/unprepared-${recipe##*/}.log" 2>&1; then
        echo "Unprepared recipe accepted: $recipe" >&2; exit 1
    fi
    grep -q 'is not prepared in the Plasma toolkit' "$work/unprepared-${recipe##*/}.log"
done
if (cd "$work" && "$make" -r -m / FAMILY=kf PKGPATH=devel/kf6-unprepared) > "$work/unprepared-kf.log" 2>&1; then exit 1; fi
grep -q 'is not prepared in the Plasma toolkit' "$work/unprepared-kf.log"
if (cd "$work" && "$make" -r -m / FAMILY=qt PKGPATH=x11/qt6-qtbase QTVERSION=6.11.2) > "$work/old-qt.log" 2>&1; then exit 1; fi
grep -q 'requires QTVERSION=6.12.0' "$work/old-qt.log"
if (cd "$work" && "$make" -r -m / FAMILY=kf PKGPATH=devel/kf6-kconfig KF6VER=6.30.0) > "$work/old-kf.log" 2>&1; then exit 1; fi
grep -q 'requires KF6VER=6.31.0' "$work/old-kf.log"
if (cd "$work" && "$make" -r -m / FAMILY=plasma PKGPATH=x11/plasma6-layer-shell-qt PLASMAVER=6.7.4) > "$work/old-plasma.log" 2>&1; then exit 1; fi
grep -q 'requires PLASMAVER=6.7.5' "$work/old-plasma.log"
if (cd "$work" && "$make" -r -m / FAMILY=plasma PKGPATH=x11/plasma6-unprepared) > "$work/unprepared-plasma.log" 2>&1; then exit 1; fi
grep -q 'is not prepared' "$work/unprepared-plasma.log"
for family in kf plasma; do
for cross in yes no; do
    "$make" -C "$work" -r -m / FAMILY="$family" PKGPATH=devel/kf6-ki18n \
        USE_CROSS_COMPILE="$cross" -V '${CMAKE_CONFIGURE_ARGS}' > "$work/dirs-$cross.log"
    if [ "$cross" = yes ]; then
        grep -q -- '-DKDE_INSTALL_APP_TEMPLATES=ON' "$work/dirs-$cross.log"
    fi
    for item in QTPLUGINDIR:plugins QMLDIR:qml QTMETATYPESDIR:metatypes QTQCHDIR:doc; do
        value="-DKDE_INSTALL_${item%:*}=qt6/${item#*:}"
        if [ "$cross" = yes ]; then
            grep -q -- "$value" "$work/dirs-$cross.log"
        else
            ! grep -q -- "$value" "$work/dirs-$cross.log"
        fi
    done
done
done
echo 'PASS: toolkit recipe/version selection and target KDE install directories; full native pkgsrc parsing remains required'
