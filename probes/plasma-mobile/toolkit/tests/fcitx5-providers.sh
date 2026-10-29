#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Inspect real Fcitx5 recipe metadata.
set -eu
[ "$#" = 4 ] || { echo "Usage: $0 PKGSRC MAKECONF DISTDIR NEW_OUTPUT" >&2; exit 2; }
pkgsrc=$(CDPATH= cd -- "$1" && pwd)
makeconf=$(CDPATH= cd -- "$(dirname -- "$2")" && pwd)/$(basename -- "$2")
bmake=${BMAKE:-bmake}
bmake=$(command -v "$bmake")
digest=${DIGEST:-$(dirname -- "$bmake")/digest}
command -v "$digest" >/dev/null
distdir=$(CDPATH= cd -- "$3" && pwd)
mkdir "$4"
out=$(CDPATH= cd -- "$4" && pwd)
failed=0
require() {
    if ! grep -F -q -- "$2" "$1"; then
        echo "FAIL: missing $2 in $1" >&2
        failed=1
    fi
}
# Check the exact archives and every patch before checking provider selection.
for recipe in fcitx5 fcitx5-qt fcitx5-configtool; do
    recipe_dir=$pkgsrc/inputmethod/$recipe
    awk '$1 == "BLAKE2s" || $1 == "SHA512" || $1 == "SHA1" || $1 == "Size" {
        gsub(/[()]/, "", $2); print $1, $2, $4
    }' "$recipe_dir/distinfo" > "$out/$recipe-checksums.list"
    while read -r algorithm source expected; do
        case $algorithm in
        SHA1)
            test -f "$recipe_dir/patches/$source"
            actual=$(sed '/\$NetBSD/d' "$recipe_dir/patches/$source" |
                "$digest" SHA1 | awk '{print $NF}')
            ;;
        Size)
            actual=$(wc -c < "$distdir/$source" | tr -d ' ')
            ;;
        *)
            actual=$("$digest" "$algorithm" "$distdir/$source" | awk '{print $NF}')
            ;;
        esac
        if [ "$actual" != "$expected" ]; then
            echo "FAIL: $algorithm mismatch for $recipe/$source" >&2
            exit 1
        fi
    done < "$out/$recipe-checksums.list"
    for source in "$recipe_dir"/patches/*; do
        [ -f "$source" ] || continue
        grep -F -q "SHA1 (${source##*/}) = " "$recipe_dir/distinfo" || {
            echo "FAIL: unlisted patch $source" >&2
            exit 1
        }
    done
done
for mode in no yes; do
    for recipe in fcitx5 fcitx5-qt fcitx5-configtool; do
        log=$out/$recipe-$mode.log
        env MAKECONF="$makeconf" "$bmake" -C "$pkgsrc/inputmethod/$recipe" \
            USE_CROSS_COMPILE="$mode" _PKGSRC_BARRIER=yes \
            -v PKGNAME -v CMAKE_CONFIGURE_ARGS \
            -v BUILDLINK_API_DEPENDS.qt6-qtbase \
            -v BUILDLINK_API_DEPENDS.kf6-kcmutils \
            -v BUILDLINK_TREE -v PKG_FAIL_REASON > "$log.raw"
        awk 'BEGIN { split("name args qt kf tree errors", labels) }
            { print labels[NR] "=" $0 }' "$log.raw" > "$log"
        errors=$(sed -n 's/^errors=//p' "$log")
        if [ -n "$errors" ]; then
            echo "FAIL: unexpected metadata error in $recipe (cross=$mode): $errors" >&2
            failed=1
        fi
        case $recipe in
        fcitx5)
            require "$log" name=fcitx5-5.1.23
            require "$log" -DENABLE_WAYLAND=ON
            require "$log" -DENABLE_TEST=ON
            require "$log" -DENABLE_TESTING_ADDONS=ON
            require "$log" -DENABLE_ENCHANT=ON
            if grep -E -q 'cldr-emoji-annotation|(^|[[:space:]])-?fmtlib([[:space:]]|$)' "$log"; then
                echo "FAIL: obsolete data/log provider in $log" >&2
                failed=1
            fi
            ;;
        fcitx5-qt)
            require "$log" name=fcitx5-qt-5.1.16
            require "$log" -DENABLE_QT5=OFF
            require "$log" -DENABLE_QT6=ON
            require "$log" -DENABLE_QT6_WAYLAND_WORKAROUND=ON
            require "$log" qt6-qtbase\>=6.12.0
            ;;
        fcitx5-configtool)
            require "$log" name=fcitx5-configtool-5.1.16
            require "$log" -DKDE_INSTALL_QTPLUGINDIR=qt6/plugins
            require "$log" -DENABLE_KCM=ON
            require "$log" -DENABLE_CONFIG_QT=ON
            require "$log" qt6-qtbase\>=6.12.0
            require "$log" kf6-kcmutils\>=6.31.0
            ;;
        esac
        if sed -n 's/^tree=//p' "$log" | tr ' ' '\n' | \
            grep -E -q '^-?(gtk[234]?|qt5-[^[:space:]]*)$'; then
            echo "FAIL: GTK or Qt5 in $recipe dependency tree (cross=$mode)" >&2
            failed=1
        fi
    done
done
# The native dictionary compiler is a Ports TOOL_DEPENDS package; the former
# path variable selects nothing.
env MAKECONF="$makeconf" "$bmake" -C "$pkgsrc/inputmethod/fcitx5" \
    USE_CROSS_COMPILE=yes EMBERBSD_FCITX5_COMP_SPELL_DICT="$out/not-present" \
    -v PKG_FAIL_REASON -v TOOL_DEPENDS > "$out/native-generator.log"
require "$out/native-generator.log" \
    'fcitx5-comp-spell-dict-5.1.23{,nb[0-9]*}:../../inputmethod/fcitx5-comp-spell-dict'
if grep -F -q -e "$out/not-present" -e COMP_SPELL_DICT "$out/native-generator.log"; then
    echo "FAIL: the former native-generator path is still used" >&2
    failed=1
fi
[ "$failed" = 0 ] || exit 1
echo 'PASS: source/patch hashes and current Fcitx5 Qt6/KF6 providers, features and native-generator guard'
