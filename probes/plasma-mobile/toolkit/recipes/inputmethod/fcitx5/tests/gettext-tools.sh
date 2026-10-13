#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Use native gettext without losing translations.
set -eu
[ "$#" = 5 ] || {
    echo "Usage: $0 PKGSRC MAKECONF FCITX_RECIPE FCITX_SOURCE NEW_OUTPUT" >&2
    exit 2
}
: "${BMAKE:?Set native bmake}" "${CMAKE:?Set native CMake}"
pkgsrc=$1 conf=$2 recipe=$3 source=$4 out=$5
for path in "$@" "$BMAKE" "$CMAKE"; do
    case "$path" in /*) ;; *) echo 'Absolute paths required' >&2; exit 2 ;; esac
done
mkdir "$out"
field() { sed -n "s/^$1=//p" "$2"; }
fail() { echo "FAIL: $*" >&2; exit 1; }
for mode in no yes; do
    "$BMAKE" -C "$pkgsrc/inputmethod/fcitx5" -f "$recipe/Makefile" \
        MAKECONF="$conf" USE_CROSS_COMPILE="$mode" WRKOBJDIR="$out/work" \
        -v PKG_FAIL_REASON -v DEPENDS -v USE_TOOLS -v CMAKE_CONFIGURE_ARGS \
        -v TOOLS_PATH.msgfmt -v TOOLS_PATH.msgmerge -v BUILDLINK_TREE > "$out/$mode.raw"
    awk 'BEGIN { split("FAIL DEPENDS TOOLS ARGS MSGFMT MSGMERGE TREE", labels) }
        { print labels[NR] "=" $0 }' "$out/$mode.raw" > "$out/$mode.log"
    [ -z "$(field FAIL "$out/$mode.log")" ] || fail "$mode metadata rejected"
    case "$(field DEPENDS "$out/$mode.log")" in *:../../devel/gettext-tools*) ;; *) fail 'shell gettext runtime lost' ;; esac
    case " $(field TREE "$out/$mode.log") " in *' gettext '*) ;; *) fail 'LibIntl dependency lost' ;; esac
    for name in msgfmt msgmerge; do
        case " $(field TOOLS "$out/$mode.log") " in *" $name "*) ;; *) fail "$name not declared as build tool" ;; esac
        case "$name" in msgfmt) key=MSGFMT ;; msgmerge) key=MSGMERGE ;; esac
        tool=$(field "$key" "$out/$mode.log")
        [ -x "$tool" ] || fail "$name host executable missing"
        case "$(field ARGS "$out/$mode.log")" in *"-DGETTEXT_${key}_EXECUTABLE:FILEPATH=$tool"*) ;; *) fail "FindGettext does not select $name" ;; esac
    done
done
mkdir "$out/fixture"
cat > "$out/fixture/CMakeLists.txt" <<'CMAKE'
cmake_minimum_required(VERSION 3.19)
project(FcitxTranslations NONE)
find_package(Gettext REQUIRED)
include("$ENV{FCITX_SOURCE}/src/lib/fcitx-utils/Fcitx5Macros.cmake")
set(FCITX_INSTALL_LOCALEDIR share/locale)
set(FCITX_INSTALL_BINDIR /usr/pkg/bin)
set(FCITX_ICON_NAME fcitx)
add_subdirectory("$ENV{FCITX_SOURCE}/po" po)
configure_file("$ENV{FCITX_SOURCE}/data/org.fcitx.Fcitx5.desktop.in.in" fcitx5.desktop.in @ONLY)
fcitx5_translate_desktop_file("${CMAKE_CURRENT_BINARY_DIR}/fcitx5.desktop.in" fcitx5.desktop
    PO_DIRECTORY "$ENV{FCITX_SOURCE}/po")
fcitx5_translate_desktop_file("$ENV{FCITX_SOURCE}/data/org.fcitx.Fcitx5.metainfo.xml.in" fcitx5.metainfo.xml
    XML PO_DIRECTORY "$ENV{FCITX_SOURCE}/po")
CMAKE
FCITX_SOURCE=$source
export FCITX_SOURCE
"$CMAKE" -S "$out/fixture" -B "$out/translations" -G 'Unix Makefiles' \
    "-DGETTEXT_MSGFMT_EXECUTABLE:FILEPATH=$(field MSGFMT "$out/yes.log")" \
    "-DGETTEXT_MSGMERGE_EXECUTABLE:FILEPATH=$(field MSGMERGE "$out/yes.log")" > "$out/configure.log" 2>&1
"$CMAKE" --build "$out/translations" --parallel 1 > "$out/translations.log" 2>&1
count=0
for po in "$source"/po/*.po; do
    language=${po##*/}
    language=${language%.po}
    [ -s "$out/translations/po/fcitx5-$language.mo" ] || fail "catalog missing: $language"
    count=$((count + 1))
done
[ "$count" -gt 0 ] || fail 'upstream catalogs absent'
grep -q '^GenericName\[fr\]=' "$out/translations/fcitx5.desktop" || fail 'desktop translation missing'
grep -q '<summary xml:lang="fr">' "$out/translations/fcitx5.metainfo.xml" || fail 'XML translation missing'
printf 'PASS: native/cross tool metadata, retained runtime gettext, %s upstream catalogs, desktop and XML translations\n' "$count"
echo 'No Fcitx C/C++ or target program was built or executed.'
