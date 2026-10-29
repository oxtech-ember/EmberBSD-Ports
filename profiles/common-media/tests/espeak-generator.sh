#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Check that cross espeak-ng takes its data
# compiler from the native audio/espeak-ng-generator package of the same release.
set -eu
[ "$#" = 2 ] || { echo 'Usage: espeak-generator.sh PKGSRC NEW_WORK' >&2; exit 2; }
: "${BMAKE:?Set native bmake}" "${MAKECONF:?Set cross MAKECONF}"
tree=$(CDPATH= cd -- "$1" && pwd)
mkdir "$2"
work=$(CDPATH= cd -- "$2" && pwd)
fail() { echo "FAIL: $*" >&2; exit 1; }
consumer=$tree/audio/espeak-ng
generator=$tree/audio/espeak-ng-generator
get() { dir=$1; shift; "$BMAKE" -C "$dir" "$@"; }
host=$(get "$consumer" -V '${TOOLBASE}')
case "$host" in /*) ;; *) fail 'cross TOOLBASE is not absolute' ;; esac

# A cross build needs no build-host prefix variable: a former one is ignored.
for extra in '' EMBERBSD_ESPEAK_HOST=/nonexistent/espeak-ng; do
    set -- -V '${PKG_FAIL_REASON}' -V '${TOOL_DEPENDS}' -V '${MAKE_FLAGS}'
    [ -z "$extra" ] || set -- "$extra" "$@"
    get "$consumer" "$@" > "$work/cross.txt"
    [ -z "$(sed -n 1p "$work/cross.txt")" ] || fail "cross espeak-ng refused ($extra): $(sed -n 1p "$work/cross.txt")"
    sed -n 2p "$work/cross.txt" | tr ' ' '\n' |
        grep -Fx 'espeak-ng-generator-1.52.0{,nb[0-9]*}:../../audio/espeak-ng-generator' >/dev/null ||
        fail 'cross espeak-ng lacks the exact native generator dependency'
    sed -n 3p "$work/cross.txt" | tr ' ' '\n' |
        grep -Fx "ESPEAK_GEN=$host/libexec/espeak-ng-generator" >/dev/null ||
        fail "cross espeak-ng does not use the TOOLBASE generator ($extra)"
done
# The configure gate accepts only the same release.
for version in 1.52.0 1.51.1; do
    fake=$work/espeak-ng-generator-$version
    printf '#!/bin/sh\necho "eSpeak NG text-to-speech: %s  Data at: /x"\n' "$version" > "$fake"
    chmod +x "$fake"
    mkdir "$work/w-$version"
    if get "$consumer" WRKDIR="$work/w-$version" ESPEAK_GENERATOR="$fake" \
        emberbsd-espeak-generator-check > "$work/check-$version.log" 2>&1; then
        [ "$version" = 1.52.0 ] || fail "cross espeak-ng accepted generator $version"
    else
        [ "$version" != 1.52.0 ] || fail 'cross espeak-ng refused the matching generator'
    fi
done

# Native espeak-ng builds its own data and has no generator dependency.
get "$consumer" USE_CROSS_COMPILE=no -V '${TOOL_DEPENDS}' -V '${MAKE_FLAGS}' > "$work/native.txt"
if grep -F espeak-ng-generator "$work/native.txt" >/dev/null; then fail 'native espeak-ng uses the generator'; fi
if grep -F ESPEAK_GEN= "$work/native.txt" >/dev/null; then fail 'native espeak-ng overrides ESPEAK_GEN'; fi

# The generator is a build-host package of the same release and distfile.
[ "$(get "$generator" USE_CROSS_COMPILE=no -V '${PKGNAME}')" = espeak-ng-generator-1.52.0 ] || fail 'unexpected generator package'
[ -z "$(get "$generator" USE_CROSS_COMPILE=no -V '${PKG_FAIL_REASON}')" ] || fail 'native generator refused'
get "$generator" USE_CROSS_COMPILE=no DISTNAME=espeak-ng-1.51.1 -V '${PKG_FAIL_REASON}' |
    grep -F 'must be eSpeak NG 1.52.0' >/dev/null || fail 'generator accepted another release'
get "$generator" -V '${PKG_FAIL_REASON}' | grep -F 'is a build-host tool' >/dev/null || fail 'generator accepted as a target package'
grep -F '(espeak-ng-1.52.0.tar.gz)' "$generator/distinfo" > "$work/generator-distinfo.txt"
grep -F '(espeak-ng-1.52.0.tar.gz)' "$consumer/distinfo" | cmp -s - "$work/generator-distinfo.txt" || fail 'generator distfile differs'
for version in 1.52.0 1.51.1; do
    src=$work/src-$version
    mkdir -p "$src/src"
    cp "$work/espeak-ng-generator-$version" "$src/src/espeak-ng"
    mkdir "$work/g-$version"
    if get "$generator" USE_CROSS_COMPILE=no WRKDIR="$work/g-$version" WRKSRC="$src" \
        post-build > "$work/post-build-$version.log" 2>&1; then
        [ "$version" = 1.52.0 ] || fail "generator package accepted build $version"
    else
        [ "$version" != 1.52.0 ] || fail 'generator package refused its own release'
    fi
done
# The rebuilt package records the generator change.
[ "$(get "$consumer" -V '${PKGNAME}')" = espeak-ng-1.52.0nb6 ] || fail 'unexpected espeak-ng package'
echo 'PASS: cross espeak-ng uses the same-release TOOLBASE generator; native build and generator package checked'
