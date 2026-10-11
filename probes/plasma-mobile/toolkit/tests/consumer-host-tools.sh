#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Native Qt path propagation to cross consumers.
set -eu
[ "$#" = 2 ] || { echo "Usage: $0 TOOLKIT_PROFILE NEW_WORK" >&2; exit 2; }
profile=$1 work=$2
: "${BMAKE:?Set the native bmake executable}"
case "$profile:$work" in /*:/*) ;; *) echo 'Absolute paths required' >&2; exit 2;; esac
mkdir "$work"
for order in before after unset; do
    {
        printf '%s\n' 'BSD_PKG_MK=yes' 'EMBERBSD_COMMON_GRAPHICS_CROSS=yes'
        printf '%s\n' 'EMBERBSD_COMMON_TOOLS=yes' 'EMBERBSD_COMMON_GRAPHICS=yes' 'EMBERBSD_COMMON_MEDIA=yes'
        if [ "$order" = before ]; then
            printf 'EMBERBSD_QT_HOST_PATH=%s/host tools\nEMBERBSD_KF6_HOST_TOOLING=%s/kf tools\n' "$work" "$work"
        fi
        printf '.include "%s"\n' "$profile"
        if [ "$order" = after ]; then
            printf 'EMBERBSD_QT_HOST_PATH=%s/host tools\nEMBERBSD_KF6_HOST_TOOLING=%s/kf tools\n' "$work" "$work"
        fi
        printf 'all:\n\t@printf '\''%%s\\n'\'' ${CMAKE_CONFIGURE_ARGS}\n'
    } > "$work/$order.mk"
    for cross in yes no; do
        "$BMAKE" -f "$work/$order.mk" "USE_CROSS_COMPILE=$cross" > "$work/$order-$cross.log"
        if [ "$cross" = yes ] && [ "$order" != unset ]; then
            printf '%s\n' "-DQT_HOST_PATH=$work/host tools" "-DKF6_HOST_TOOLING=$work/kf tools" > "$work/expected"
        else
            printf '\n' > "$work/expected"
        fi
        cmp "$work/expected" "$work/$order-$cross.log"
    done
done
echo 'PASS: cross Qt/KF consumers receive quoted host paths before/after profile inclusion; native and unset cases stay untouched'
