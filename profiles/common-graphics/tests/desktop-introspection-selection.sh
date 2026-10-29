#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), actual recipe selection regression.
set -eu
[ "$#" = 3 ] || { echo 'Usage: desktop-introspection-selection.sh PKGSRC CROSS_MAKECONF NEW_WORK' >&2; exit 2; }
tree=$(cd "$1" && pwd -P)
conf=$2
case "$conf" in /*) ;; *) exit 2;; esac
[ -f "$conf" ]
mkdir "$3"
work=$(cd "$3" && pwd -P)
make=${BMAKE:-bmake}
query() {
    recipe=$1; var=$2; shift 2
    "$make" -C "$tree/$recipe" MAKECONF="$conf" "$@" -V "\${$var}"
}
for recipe in fonts/harfbuzz devel/pango x11/gtk3 devel/at-spi2-core; do
    name=${recipe##*/}
    options=$(query "$recipe" PKG_OPTIONS)
    printf '%s\n' "$options" > "$work/$name-options"
    case " $options " in *' introspection '*) ;; *) exit 1;; esac
    scanner=$(query "$recipe" MESON_BINARY.g-ir-scanner)
    [ -x "$scanner" ]
    [ "$(query "$recipe" MESON_CROSS.emberbsd_gi_cross)" = true ]
    native=$(query "$recipe" MESON_BINARY.g-ir-scanner USE_CROSS_COMPILE=no)
    [ -z "$native" ]
    query "$recipe" MESON_ARGS "PKG_OPTIONS.$name=-introspection" > "$work/$name-disabled"
    case "$name" in gtk3) flag=false;; *) flag=disabled;; esac
    grep -- "-Dintrospection=$flag" "$work/$name-disabled" > /dev/null
    # An absent query configuration must not refuse fetch; configure refuses it.
    query "$recipe" PKG_FAIL_REASON EMBERBSD_GI_QUERY_CONFIG=/ember-missing-gi-query.json > "$work/$name-missing-query"
    ! grep 'EMBERBSD_GI_QUERY_CONFIG must name' "$work/$name-missing-query" > /dev/null
    if "$make" -C "$tree/$recipe" MAKECONF="$conf" EMBERBSD_GI_QUERY_CONFIG=/ember-missing-gi-query.json \
        emberbsd-gi-inputs > "$work/$name-missing-check" 2>&1; then exit 1; fi
    grep 'EMBERBSD_GI_QUERY_CONFIG must name an existing absolute file' "$work/$name-missing-check" > /dev/null
    printf 'PASS: %s real cross/native selection, optional disable and configure-time query refusal\n' "$recipe"
done
options=$(cat "$work/gtk3-options")
case " $options " in *' quartz '*) exit 1;; esac
case " $options " in *' wayland '*) ;; *) exit 1;; esac
case " $options " in *' x11 '*) ;; *) exit 1;; esac
if [ "$(query x11/gtk3 OPSYS USE_CROSS_COMPILE=no)" = Darwin ]; then
    native=$(query x11/gtk3 PKG_OPTIONS USE_CROSS_COMPILE=no)
    case " $native " in *' quartz '*) ;; *) exit 1;; esac
fi
scanner=$(query x11/gtk3 MESON_BINARY.wayland-scanner)
[ -x "$scanner" ]
printf '%s\n' 'PASS: GTK target uses X11/Wayland and the real native Wayland scanner; native Quartz stays native'
