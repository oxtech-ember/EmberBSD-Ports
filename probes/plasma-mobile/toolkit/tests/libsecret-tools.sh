#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), inspect actual package generator selection.
set -eu
[ "$#" = 3 ] || { echo 'Usage: libsecret-tools.sh PKGSRC CROSS_MAKECONF NEW_WORK' >&2; exit 2; }
pkgsrc=$1 config=$2 work=$3
: "${BMAKE:=bmake}"
mkdir "$work"
query() {
    MAKECONF="$config" "$BMAKE" -C "$pkgsrc/security/libsecret" \
        _MAKEVARS_MK=defined _PKGSRC_BARRIER=yes "$@"
}
name=$(query USE_CROSS_COMPILE=no -V '${PKGNAME}')
case "$name" in
    libsecret-0.21.8.2) complete_cross=yes; series=0.21 ;;
    *) echo "Unexpected libsecret package: $name" >&2; exit 1 ;;
esac
for mode in yes no; do
    for selection in default disabled; do
        set -- USE_CROSS_COMPILE="$mode"
        [ "$selection" = default ] || set -- "$@" PKG_OPTIONS.libsecret=-doc
        prefix=$work/$mode-$selection
        variables='PKGNAME MASTER_SITES PKG_FAIL_REASON MESON_BINARIES MESON_NATIVE_ARGS BUILD_DEPENDS TOOL_DEPENDS BUILDLINK_API_DEPENDS.vala BUILDLINK_API_DEPENDS.py-gi-docgen MESON_ARGS PLIST.doc PLIST_SRC TEST_DEPENDS'
        for variable in $variables; do set -- "$@" -V "\${$variable}"; done
        query "$@" > "$prefix-values.txt"
        index=1
        for variable in $variables; do
            sed -n "${index}p" "$prefix-values.txt" > "$prefix-$variable.txt"
            index=$((index + 1))
        done
        grep -qx "$name" "$prefix-PKGNAME.txt"
        [ "$(cat "$prefix-PKG_FAIL_REASON.txt")" = '' ]
        if grep -qE -- '-D(tests|manpage)=false' "$prefix-MESON_ARGS.txt"; then exit 1; fi
        grep -q 'py.*dbus' "$prefix-TEST_DEPENDS.txt"
        tr -s ' ' '\n' < "$prefix-MASTER_SITES.txt" > "$prefix-sites.txt"
        grep -q "/sources/libsecret/$series/\$" "$prefix-sites.txt"
        if grep -v "/sources/libsecret/$series/\$" "$prefix-sites.txt"; then exit 1; fi
        enabled=no
        if [ "$selection" = default ] && { [ "$mode" = no ] || [ "$complete_cross" = yes ]; }; then enabled=yes; fi
        if [ "$enabled" = yes ]; then
            grep -q -- '-Dgtk_doc=true' "$prefix-MESON_ARGS.txt"
            grep -qx yes "$prefix-PLIST.doc.txt"
            if [ "$mode" = yes ]; then
                grep -q gi-docgen "$prefix-MESON_BINARIES.txt"
            else
                grep -q gi-docgen "$prefix-BUILDLINK_API_DEPENDS.py-gi-docgen.txt"
            fi
        else
            grep -q -- '-Dgtk_doc=false' "$prefix-MESON_ARGS.txt"
            [ "$(cat "$prefix-PLIST.doc.txt")" = '' ]
            if cat "$prefix-MESON_BINARIES.txt" "$prefix-BUILDLINK_API_DEPENDS.py-gi-docgen.txt" \
                "$prefix-BUILD_DEPENDS.txt" "$prefix-TOOL_DEPENDS.txt" | grep -q gi-docgen; then exit 1; fi
        fi
        if [ "$complete_cross" = yes ]; then
            if grep -E -- '-D(introspection|vapi)=false' "$prefix-MESON_ARGS.txt"; then exit 1; fi
            if [ "$mode" = yes ]; then
                grep -q g-ir-scanner "$prefix-MESON_BINARIES.txt"
                grep -q vapigen "$prefix-MESON_BINARIES.txt"
                grep -q glib2-introspection "$prefix-BUILD_DEPENDS.txt"
            else
                grep -q vala "$prefix-BUILDLINK_API_DEPENDS.vala.txt"
            fi
        fi
    done
done
# Only API reference entries are conditional; the manual and runtime stay listed.
plist=$pkgsrc/security/libsecret/PLIST
grep -q '^\${PLIST.doc}share/doc/libsecret-1/' "$plist"
if grep -q '^share/doc/libsecret-1/' "$plist"; then exit 1; fi
awk '/^\$\{PLIST.doc\}/ && !/^\$\{PLIST.doc\}share\/doc\/libsecret-1\// { exit 1 }' "$plist"
for path in bin/secret-tool man/man1/secret-tool.1 lib/libsecret-1.so \
    lib/girepository-1.0/Secret-1.typelib share/gir-1.0/Secret-1.gir \
    share/vala/vapi/libsecret-1.vapi; do
    grep -Fqx "$path" "$plist"
done
if [ "$complete_cross" = yes ]; then
    # Cross generators are native TOOLBASE packages, not configured prefixes.
    tr -s ' ' '\n' < "$work/yes-default-TOOL_DEPENDS.txt" > "$work/cross-tools.txt"
    grep -qx 'vala>=0.56.19:../../lang/vala' "$work/cross-tools.txt"
    grep -qx 'py[0-9]*-gi-docgen>=2026.1:../../devel/py-gi-docgen' "$work/cross-tools.txt"
    tr -s ' ' '\n' < "$work/yes-disabled-TOOL_DEPENDS.txt" | grep -qx 'vala>=0.56.19:../../lang/vala'
    toolbase=$(query USE_CROSS_COMPILE=yes -V '${TOOLBASE}')
    query USE_CROSS_COMPILE=yes EMBERBSD_VALA_HOST=/nonexistent-ember-generator \
        EMBERBSD_GI_DOCGEN_HOST=/nonexistent-ember-generator \
        -V '${PKG_FAIL_REASON}' -V '${MESON_BINARY.vapigen}' -V '${MESON_BINARY.vala}' \
        -V '${MESON_BINARY.gi-docgen}' > "$work/legacy-host-variables.txt"
    printf '%s\n' '' "$toolbase/bin/vapigen" "$toolbase/bin/valac" "$toolbase/bin/gi-docgen" |
        cmp -s - "$work/legacy-host-variables.txt"
    query USE_CROSS_COMPILE=yes -n emberbsd-secret-native > "$work/native-plan.txt"
    for check in "$toolbase/bin/valac --version" "'Vala 0.56.19'" "$toolbase/bin/vapigen --version" \
        "'Vala API Generator 0.56.19'" "$toolbase/bin/gi-docgen --version" "'2026.1'"; do
        grep -Fq -- "$check" "$work/native-plan.txt"
    done
    if grep -q '_HOST' "$work/native-plan.txt"; then exit 1; fi
    # libproxy shares the generators and has no configured prefixes either.
    MAKECONF="$config" "$BMAKE" -C "$pkgsrc/www/libproxy" USE_CROSS_COMPILE=yes \
        EMBERBSD_VALA_HOST=/nonexistent-ember-generator EMBERBSD_GI_DOCGEN_HOST=/nonexistent-ember-generator \
        -V '${PKG_FAIL_REASON}' -V '${TOOLS_PATH.vapigen}' -V '${TOOLS_PATH.gi-docgen}' > "$work/libproxy-tools.txt"
    printf '%s\n' '' "$toolbase/bin/vapigen" "$toolbase/bin/gi-docgen" | cmp -s - "$work/libproxy-tools.txt"
    query USE_CROSS_COMPILE=yes PKG_OPTIONS.libsecret=-doc -n emberbsd-secret-native > "$work/disabled-native-plan.txt"
    grep -q vapigen "$work/disabled-native-plan.txt"
    if grep -q gi-docgen "$work/disabled-native-plan.txt"; then exit 1; fi
else
    query USE_CROSS_COMPILE=yes PKG_OPTIONS.libsecret=doc \
        -V '${PKG_FAIL_REASON}' > "$work/unsupported-cross-doc.txt"
    grep -q 'cannot generate the GIR required by documentation' "$work/unsupported-cross-doc.txt"
fi
echo 'PASS: libsecret native/cross documentation selection, runtime inventory and generator prerequisites'
