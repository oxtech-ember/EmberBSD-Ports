#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), explicit host msgfmt without a libintl override.
set -eu
[ "$#" = 5 ] || { echo "Usage: $0 PKGSRC CROSS_MAKECONF NATIVE_MAKECONF HOST_MSGFMT NEW_WORK" >&2; exit 2; }
pkgsrc=$1 crossconf=$2 nativeconf=$3 msgfmt=$4 work=$5
bmake=${BMAKE:-bmake}
mkdir "$work"
for mode in native cross; do
    case "$mode" in native) conf=$nativeconf;; cross) conf=$crossconf;; esac
    cat > "$work/$mode.mk.conf" <<EOF
.include "$conf"
.undef EMBERBSD_BUILD_MSGFMT
EOF
    "$bmake" -C "$pkgsrc/archivers/xz" MAKECONF="$work/$mode.mk.conf" \
        USE_BUILTIN.gettext=no -v _TOOLS_USE_PKGSRC.msgfmt \
        -v TOOLS_DEPENDS.msgfmt > "$work/$mode-default.txt"
    grep -qx yes "$work/$mode-default.txt"
    grep -q ':../../devel/gettext-tools' "$work/$mode-default.txt"
    "$bmake" -C "$pkgsrc/archivers/xz" MAKECONF="$work/$mode.mk.conf" \
        USE_BUILTIN.gettext=no EMBERBSD_BUILD_MSGFMT="$msgfmt" \
        -v PKG_FAIL_REASON -v USE_BUILTIN.gettext -v _TOOLS_USE_PKGSRC.msgfmt \
        -v TOOLS_PATH.msgfmt -v TOOL_DEPENDS > "$work/$mode-selected.txt"
    grep -Fxq "$msgfmt" "$work/$mode-selected.txt"
    [ "$(grep -cx no "$work/$mode-selected.txt")" = 2 ]
    if grep -E 'gettext-tools|EMBERBSD_BUILD_MSGFMT requires|must name' "$work/$mode-selected.txt"; then
        echo 'Explicit host msgfmt did not remove the bootstrap dependency' >&2; exit 1
    fi
done
cat > "$work/old-msgfmt" <<'SH'
#!/bin/sh
echo 'msgfmt (GNU gettext-tools) 0.22'
SH
cat > "$work/foreign-msgfmt" <<'SH'
#!/bin/sh
echo 'msgfmt (different implementation) 9.0'
SH
cp "$work/old-msgfmt" "$work/nonexecutable"
cat > "$work/broken-msgfmt" <<'SH'
#!/bin/sh
echo 'msgfmt (GNU gettext-tools) 1.0'
exit 1
SH
chmod +x "$work/old-msgfmt" "$work/foreign-msgfmt" "$work/broken-msgfmt"
for invalid in msgfmt /nonexistent/ember-msgfmt "$work/old-msgfmt" "$work/foreign-msgfmt" "$work/nonexecutable" "$work/broken-msgfmt"; do
    "$bmake" -C "$pkgsrc/archivers/xz" MAKECONF="$work/native.mk.conf" \
        EMBERBSD_BUILD_MSGFMT="$invalid" -v PKG_FAIL_REASON > "$work/invalid.txt"
    grep -q 'EMBERBSD_BUILD_MSGFMT .*\(must name\|requires\)' "$work/invalid.txt"
done

# Compile plural/context data with the actual selected tool, then read it
# through the pkgsrc libintl provider that the override must leave intact.
prefix=$("$bmake" -C "$pkgsrc/archivers/xz" MAKECONF="$nativeconf" -v LOCALBASE)
cat > "$work/consumer.c" <<'C'
#include <libintl.h>
#include <locale.h>
#include <stdlib.h>
#include <string.h>
int main(int argc, char **argv)
{
    if (argc != 2 || setenv("LANGUAGE", "zz", 1) != 0 ||
        setenv("LC_ALL", "en_US.UTF-8", 1) != 0 ||
        setlocale(LC_ALL, "") == NULL) return 1;
    if (!bindtextdomain("ember", argv[1])) return 1;
    if (strcmp(dgettext("ember", "button\004Open"), "Translated open")) return 1;
    if (strcmp(dngettext("ember", "File", "Files", 1), "Translated file")) return 1;
    return strcmp(dngettext("ember", "File", "Files", 2), "Translated files") != 0;
}
C
cat > "$work/catalog.po" <<'PO'
msgid ""
msgstr ""
"Content-Type: text/plain; charset=UTF-8\n"
"Language: zz\n"
"Plural-Forms: nplurals=2; plural=(n != 1);\n"

msgctxt "button"
msgid "Open"
msgstr "Translated open"

msgid "File"
msgid_plural "Files"
msgstr[0] "Translated file"
msgstr[1] "Translated files"
PO
mkdir -p "$work/locale/zz/LC_MESSAGES"
"$msgfmt" -o "$work/locale/zz/LC_MESSAGES/ember.mo" "$work/catalog.po"
. "$(CDPATH= cd -- "$(dirname -- "$0")/../cross" && pwd)/host-gcc16.sh"
ember_require_host_gcc16 HOST_CC c
"$HOST_CC" -Wall -Wextra -Werror -I"$prefix/include/gettext" \
    "$work/consumer.c" -L"$prefix/lib" -Wl,-rpath,"$prefix/lib" -lintl -o "$work/consumer"
"$work/consumer" "$work/locale"
echo 'PASS: default dependency, native/cross host override, invalid tools and libintl plural/context consumer'
