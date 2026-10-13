#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Exercise actual pkgsrc option and dependency rules.
set -eu
[ "$#" = 4 ] || {
    echo "Usage: $0 PKGSRC MAKECONF LIBCANBERRA_RECIPE NEW_OUTPUT" >&2
    exit 2
}
: "${BMAKE:?Set the native bmake executable}"
for path in "$@"; do
    case "$path" in /*) ;; *) echo 'Absolute paths required' >&2; exit 2 ;; esac
done
pkgsrc=$1 conf=$2 recipe=$3 work=$4
[ -f "$pkgsrc/mk/bsd.pkg.mk" ] && [ -f "$conf" ]
[ -f "$recipe/Makefile" ] && [ -f "$recipe/buildlink3.mk" ]
mkdir "$work"

# Query the candidate against the real dependency tree without exporting it.
query()
{
    "$BMAKE" -C "$pkgsrc/audio/libcanberra" -f "$recipe/Makefile" \
        MAKECONF="$conf" WRKOBJDIR="$work/work" USE_CROSS_COMPILE="$1" PKG_DEFAULT_OPTIONS= \
        "PKG_OPTIONS.libcanberra=$2" \
        -V 'OPTIONS=${PKG_OPTIONS}' \
        -V 'ARGS=${CONFIGURE_ARGS}' \
        -V 'DEPS=${DEPENDS} ${BUILD_DEPENDS} ${TOOL_DEPENDS}' \
        -V 'GTK=${PLIST.gtk:Uno}' \
        -V 'GTK3=${PLIST.gtk3:Uno}' \
        -V 'GTK_ANY=${PLIST.gtk-any:Uno}' \
        -V 'FAIL=${PKG_FAIL_REASON}'
}
field()
{
    sed -n "s/^$1=//p" "$2"
}
fail()
{
    echo "FAIL: $*" >&2
    exit 1
}
for mode in no yes; do
    for option in default gtk3 disabled; do
        selected=
        case "$option" in gtk3) selected=gtk3 ;; disabled) selected=-gtk3 ;; esac
        log=$work/$mode-$option.log
        query "$mode" "$selected" > "$log"
        [ -z "$(field FAIL "$log")" ] || fail "pkgsrc rejected $mode $option"
        args=" $(field ARGS "$log") "
        deps=" $(field DEPS "$log") "
        case "$args" in *' --disable-gtk '*) ;; *) fail 'GTK2 auto-detection remains enabled' ;; esac
        case "$deps" in *:../../x11/gtk2*) fail 'GTK2 entered the dependency graph' ;; esac
        case "$deps" in *:../../multimedia/gstreamer1*) ;; *) fail 'GStreamer event sounds were removed' ;; esac
        case "$deps" in *:../../audio/libvorbis*) ;; *) fail 'Vorbis event sounds were removed' ;; esac
        [ "$(field GTK "$log")" = no ] || fail 'GTK2 payload enabled'
        if [ "$option" = gtk3 ]; then
            case "$args" in *' --enable-gtk3 '*) ;; *) fail 'GTK3 not explicitly enabled' ;; esac
            case "$args" in *' --disable-gtk3 '*) fail 'conflicting GTK3 flags' ;; esac
            case "$deps" in *'gtk3+>=3.24.52:../../x11/gtk3'*) ;; *) fail 'modern GTK3 dependency absent' ;; esac
            [ "$(field GTK3 "$log")" = yes ] && [ "$(field GTK_ANY "$log")" = yes ] || fail 'GTK3 payload missing'
        else
            case "$args" in *' --disable-gtk3 '*) ;; *) fail 'GTK3 auto-detection remains enabled' ;; esac
            case "$args" in *' --enable-gtk3 '*) fail 'GTK3 enabled in core package' ;; esac
            case "$deps" in *:../../x11/gtk3*) fail 'GTK3 entered the core dependency graph' ;; esac
            [ "$(field GTK3 "$log")" = no ] && [ "$(field GTK_ANY "$log")" = no ] || fail 'GTK payload in core package'
        fi
    done
    for obsolete in gtk gtk2; do
        log=$work/$mode-$obsolete.log
        query "$mode" "$obsolete" > "$log"
        [ -n "$(field FAIL "$log")" ] || fail "obsolete option accepted: $obsolete"
    done
done

# Test the public buildlink with the options of each resulting package.
# Explicit values model the package's recorded PKG_OPTIONS; no package is installed.
cat > "$work/consumer.mk" <<'MAKE'
DISTNAME= canberra-consumer-1.0
CATEGORIES= audio
USE_BUILDLINK3= yes
.include "../../mk/bsd.prefs.mk"
.include "${CANBERRA_RECIPE}/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
MAKE
for mode in no yes; do
    for option in default gtk3 gtk; do
        selected=
        [ "$option" = default ] || selected=$option
        log=$work/consumer-$mode-$option.log
        "$BMAKE" -C "$pkgsrc/devel/kf6-knotifications" -f "$work/consumer.mk" \
            MAKECONF="$conf" WRKOBJDIR="$work/work" USE_CROSS_COMPILE="$mode" \
            CANBERRA_RECIPE="$recipe" "PKG_BUILD_OPTIONS.libcanberra=$selected" \
            -V 'DEPS=${DEPENDS} ${BUILD_DEPENDS} ${TOOL_DEPENDS}' \
            -V 'GTK3_LINK=${BUILDLINK_TREE:Mgtk3}' \
            -V 'FAIL=${PKG_FAIL_REASON}' > "$log"
        if [ "$option" = gtk ]; then
            case "$(field FAIL "$log")" in *'unsupported GTK2 adapter'*) ;; *) fail 'old GTK2 buildlink accepted' ;; esac
            continue
        fi
        [ -z "$(field FAIL "$log")" ] || fail 'consumer metadata failed'
        deps=" $(field DEPS "$log") "
        case "$deps" in *'libcanberra>=0.30nb26:../../audio/libcanberra'*) ;; *) fail 'old provider still accepted' ;; esac
        case "$deps" in *:../../x11/gtk2*) fail 'consumer pulled GTK2' ;; esac
        if [ "$option" = gtk3 ]; then
            [ "$(field GTK3_LINK "$log")" = gtk3 ] || fail 'explicit GTK3 adapter lost buildlink'
        else
            [ -z "$(field GTK3_LINK "$log")" ] || fail 'core consumer pulled GTK3'
        fi
    done
done

echo 'PASS: native/cross core metadata has no GTK; explicit GTK3 metadata is retained; GTK2 is rejected'
echo 'Package checks and sound playback are separate acceptance steps.'
