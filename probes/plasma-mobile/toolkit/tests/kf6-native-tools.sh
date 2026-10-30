#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Cross KDE consumers get their native code
# generators from Ports TOOL_DEPENDS packages built from the same release,
# never from a configured build-host prefix.
set -eu
[ "$#" = 3 ] || { echo 'Usage: kf6-native-tools.sh PKGSRC CROSS_MAKECONF NEW_WORK' >&2; exit 2; }
pkgsrc=$1 cross=$2 work=$3
: "${BMAKE:=bmake}"
mkdir "$work"
query() { # MAKECONF PKGPATH ARGS...
    config=$1 path=$2; shift 2
    MAKECONF="$config" "$BMAKE" -C "$pkgsrc/$path" _MAKEVARS_MK=defined _PKGSRC_BARRIER=yes "$@"
}
# consumer|native tool package|source owner|CMake argument below TOOLBASE
cat > "$work/table" <<'TABLE'
textproc/kf6-sonnet|textproc/kf6-sonnet-parsetrigrams|textproc/kf6-sonnet|-DPARSETRIGRAMS_EXECUTABLE=@TOOLBASE@/bin/parsetrigrams6
textproc/kf6-syntax-highlighting|textproc/kf6-syntax-highlighting-indexer|textproc/kf6-syntax-highlighting|-DKATEHIGHLIGHTINGINDEXER_EXECUTABLE=@TOOLBASE@/bin/katehighlightingindexer
net/kdsoap-ws-discovery-client|net/kdsoap-kdwsdl2cpp|net/kdsoap|-DKDSOAP_KDWSDL2CPP_COMPILER=@TOOLBASE@/bin/kdwsdl2cpp-qt6
x11/kf6-kded|devel/kf6-kconfig-compiler|devel/kf6-kconfig|-DKF6_HOST_TOOLING=@TOOLBASE@/lib/cmake
TABLE
# A native CMake framework build in the same configuration fails for no
# reason of the generator packages.
query "$cross" archivers/kf6-karchive USE_CROSS_COMPILE=no -V '${PKG_FAIL_REASON}' > "$work/native-reference.txt"
n=0
while IFS='|' read -r consumer tool owner arg; do
    n=$((n + 1))
    toolbase=$(query "$cross" "$consumer" -V '${TOOLBASE}')
    [ -n "$toolbase" ]
    arg=$(printf '%s\n' "$arg" | sed "s|@TOOLBASE@|$toolbase|")
    version=$(query "$cross" "$owner" -V '${PKGVERSION_NOREV}')
    pkg=$(query "$cross" "$tool" USE_CROSS_COMPILE=no -V '${PKGBASE}')
    dep="$pkg-$version{,nb[0-9]*}:../../$tool"
    # The former build-host prefix is ignored.
    query "$cross" "$consumer" EMBERBSD_KF6_HOST_TOOLING=/nonexistent-ember-kf6 \
        -V '${USE_CROSS_COMPILE:tl}' -V '${PKG_FAIL_REASON}' \
        -V '${TOOL_DEPENDS}' -V '${CMAKE_CONFIGURE_ARGS}' > "$work/$n-consumer.txt"
    [ "$(sed -n 1p "$work/$n-consumer.txt")" = yes ]
    if sed -n 2p "$work/$n-consumer.txt" | grep -q .; then
        echo "$consumer cannot be fetched or built: $(sed -n 2p "$work/$n-consumer.txt")" >&2; exit 1
    fi
    sed -n 3p "$work/$n-consumer.txt" | tr -s ' ' '\n' | grep -Fqx -- "$dep" ||
        { echo "$consumer does not depend on $dep" >&2; exit 1; }
    sed -n 4p "$work/$n-consumer.txt" | tr -s ' ' '\n' | grep -Fqx -- "$arg" ||
        { echo "$consumer does not pass $arg" >&2; exit 1; }
    if grep -q nonexistent-ember-kf6 "$work/$n-consumer.txt"; then
        echo "$consumer still reads EMBERBSD_KF6_HOST_TOOLING" >&2; exit 1
    fi
    # The tool package builds natively from the owner's release and patches
    # and refuses a cross build.
    query "$cross" "$tool" USE_CROSS_COMPILE=no -V '${PKG_FAIL_REASON}' -V '${DISTFILES}' \
        -V '${DISTINFO_FILE}' -V '${PATCHDIR}' -V '${PKGVERSION_NOREV}' > "$work/$n-native.txt"
    query "$cross" "$owner" USE_CROSS_COMPILE=no -V '${DISTFILES}' \
        -V '${DISTINFO_FILE}' -V '${PATCHDIR}' -V '${PKGVERSION_NOREV}' > "$work/$n-owner.txt"
    sed -n 1p "$work/$n-native.txt" | cmp -s - "$work/native-reference.txt" ||
        { echo "$tool cannot be built natively: $(sed -n 1p "$work/$n-native.txt")" >&2; exit 1; }
    sed 1d "$work/$n-native.txt" | cmp -s - "$work/$n-owner.txt" ||
        { echo "$tool does not use the $owner source" >&2; exit 1; }
    query "$cross" "$tool" -V '${PKG_FAIL_REASON}' | grep -q 'build-host tool' ||
        { echo "$tool accepts a cross build" >&2; exit 1; }
done < "$work/table"
echo "PASS: $n KDE cross consumers use native Ports generator packages"
