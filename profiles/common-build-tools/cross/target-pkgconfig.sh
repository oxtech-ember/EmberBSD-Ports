#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Keep build-host paths out of staged target
# pkg-config files.
#
# A cross configure runs pkg-config with PKG_CONFIG_SYSROOT_DIR=CROSS_DESTDIR,
# so the -I and -L flags of its dependencies name the build host's sysroot.
# Packages that copy those flags into their own .pc file (Cflags,
# Libs.private) would ship that sysroot, and a consumer in another build
# root then gets a path that does not exist. Rewrite such flags to the target
# path, which the target pkg-config uses as is and a later cross pkg-config
# roots again. A .pc file that still names the sysroot or another build
# directory (WRKDIR, TOOLDIR) after the rewrite is refused.
set -eu
[ "$#" -ge 2 ] || {
    echo 'Usage: target-pkgconfig.sh DESTDIR SYSROOT [BUILD_DIRECTORY...]' >&2
    exit 2
}
destdir=$1 sysroot=$2
shift 2
for path in "$destdir" "$sysroot" "$@"; do
    case "$path" in
    /?*) ;;
    *) echo "target-pkgconfig: not an absolute path: $path" >&2; exit 2 ;;
    esac
    case "$path" in
    *[!A-Za-z0-9_./+-]*) echo "target-pkgconfig: unsupported path: $path" >&2; exit 2 ;;
    esac
done
[ -d "$destdir" ] || exit 0
sysroot=${sysroot%/}
roots=$sysroot
real=$(CDPATH= cd -- "$sysroot" 2> /dev/null && pwd -P) || real=
[ -z "$real" ] || [ "$real" = "$sysroot" ] || roots="$roots $real"
edit=
for root in $roots; do
    quoted=$(printf '%s\n' "$root" | sed -e 's/[.+]/\\&/g')
    edit="$edit -e s#(-I|-L|-isystem[[:space:]]*)$quoted/#\\1/#g"
done
status=0
scratch=$(mktemp -d "${TMPDIR:-/tmp}/target-pkgconfig.XXXXXX")
trap 'rm -rf "$scratch"' EXIT
find "$destdir" -type f -path '*/pkgconfig/*.pc' | sort > "$scratch/list"
while IFS= read -r file; do
    # The expressions hold pattern characters; do not expand them as globs.
    set -f
    # shellcheck disable=SC2086
    sed -E $edit "$file" > "$scratch/pc"
    set +f
    if ! cmp -s "$scratch/pc" "$file"; then
        # Rewrite in place to keep the staged file's mode and owner.
        if [ -w "$file" ]; then
            cat "$scratch/pc" > "$file"
        else
            chmod u+w "$file"
            cat "$scratch/pc" > "$file"
            chmod u-w "$file"
        fi
        echo "target-pkgconfig: removed the build sysroot from ${file#"$destdir"}"
    fi
    for dir in $roots "$@"; do
        if grep -F -q -- "${dir%/}" "$file"; then
            echo "target-pkgconfig: ${file#"$destdir"} names build directory $dir:" >&2
            grep -F -n -- "${dir%/}" "$file" >&2 || :
            status=1
        fi
    done
done < "$scratch/list"
exit "$status"
