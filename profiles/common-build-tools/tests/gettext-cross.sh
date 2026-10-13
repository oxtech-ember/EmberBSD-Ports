#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Separate gettext's host and target xz use.
set -eu
[ "$#" = 5 ] || {
    echo "Usage: $0 PKGSRC MAKECONF GETTEXT_MAKEFILE GETTEXT_SOURCE NEW_OUTPUT" >&2
    exit 2
}
: "${BMAKE:?Set native bmake}"
pkgsrc=$1 conf=$2 recipe=$3 source=$4 out=$5
for path in "$@" "$BMAKE"; do
    case "$path" in /*) ;; *) echo 'Absolute paths required' >&2; exit 2 ;; esac
done
mkdir "$out"
field() { sed -n "s/^$1=//p" "$2"; }
fail() { echo "FAIL: $*" >&2; exit 1; }
for mode in no yes; do
    "$BMAKE" -C "$pkgsrc/devel/gettext-tools" -f "$recipe" \
        MAKECONF="$conf" USE_CROSS_COMPILE="$mode" WRKOBJDIR="$out/work" \
        -V 'FAIL=${PKG_FAIL_REASON}' -V 'DEPENDS=${DEPENDS}' \
        -V 'USE_TOOLS=${USE_TOOLS}' -V 'XZ=${TOOLS_PATH.xz}' \
        -V 'METHOD=${_TOOLS_DEPMETHOD.xz}' -V 'ARGS=${CONFIGURE_ARGS}' \
        -V 'PYTHON=${PYVERSSUFFIX}' > "$out/$mode.log"
    [ -z "$(field FAIL "$out/$mode.log")" ] || fail "$mode metadata rejected"
    case " $(field ARGS "$out/$mode.log") " in *' --with-xz '*) ;; *) fail 'xz archive support lost' ;; esac
    if [ "$mode" = yes ]; then
        case "$(field DEPENDS "$out/$mode.log")" in *'xz>=5.8.4:../../archivers/xz'*) ;; *) fail 'target xz dependency missing' ;; esac
        case " $(field USE_TOOLS "$out/$mode.log") " in *' xz:run '*) fail 'cross runtime tool rejection restored' ;; esac
        [ "$(field METHOD "$out/$mode.log")" = TOOL_DEPENDS ] || fail 'xz is not a build tool'
    else
        case " $(field USE_TOOLS "$out/$mode.log") " in *' xz:run '*) ;; *) fail 'native runtime tool selection changed' ;; esac
        [ "$(field METHOD "$out/$mode.log")" = DEPENDS ] || fail 'native xz dependency changed'
    fi
done
# Execute the release's archive rule with the selected host tool.
# This does not execute target autopoint or any target program.
xz=$(field XZ "$out/yes.log")
[ -x "$xz" ] || fail 'selected host xz is not executable'
mkdir "$out/bin"
ln -s "$xz" "$out/bin/xz"
awk '/^archive.dir.tar.xz:/ { print; getline; print; exit }' \
    "$source/gettext-tools/autotools/Makefile.am" > "$out/archive.mk"
[ -s "$out/archive.mk" ] || fail 'upstream archive rule absent'
PATH=$out/bin:$PATH "$BMAKE" -C "$out" -f archive.mk \
    "srcdir=$source/gettext-tools/autotools" archive.dir.tar.xz > "$out/archive.log" 2>&1
"$xz" -d -c < "$out/archive.dir.tar.xz" > "$out/decoded.tar"
cmp "$source/gettext-tools/autotools/archive.dir.tar" "$out/decoded.tar"
echo 'PASS: native policy, cross host xz, target xz dependency and upstream archive roundtrip'
echo 'No package was built or installed. Target autopoint execution remains separate.'
