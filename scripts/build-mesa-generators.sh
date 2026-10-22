#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
# Build and seal the native Mesa generators from the pinned inputs.
# Each step calls the existing host-tool or seal script. A step that has
# completed is not done again, so an interrupted run can continue.
set -eu
umask 022

[ "$#" -eq 2 ] || {
    echo 'Usage: sh scripts/build-mesa-generators.sh ABSOLUTE_WORK ABSOLUTE_DISTDIR' >&2
    exit 2
}
work=$1
distdir=$2
for dir in "$work" "$distdir"; do
    case "$dir" in
        /*) ;;
        *) echo "Not an absolute path: $dir" >&2; exit 2 ;;
    esac
    case "$dir" in
        *[!A-Za-z0-9_./-]*) echo "Unsafe path: $dir" >&2; exit 2 ;;
    esac
done
[ "$(uname -s)" = Darwin ] && [ "$(uname -m)" = arm64 ] || {
    echo 'The native generators require macOS ARM64.' >&2
    exit 2
}
: "${EMBERBSD_SDK_SOURCE:?Set EMBERBSD_SDK_SOURCE to the EmberBSD SDK source}"
: "${HOST_PREFIX:?Set HOST_PREFIX to the prefix with Meson, Ninja and pkg-config}"
host=$HOST_PREFIX
python=${HOST_PYTHON:-$host/bin/python3.14}
ruby=${HOST_RUBY:-ruby}
profile=${MESA_GENERATOR_PROFILE:-powervr}
export PYTHONDONTWRITEBYTECODE=1
export HOST_PYTHON="$python" HOST_RUBY="$ruby"

ports=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
tools=$ports/probes/a733-accelerators/host-tools
cross=$ports/profiles/common-build-tools/cross
graphics=$ports/profiles/common-graphics

fail()
{
    echo "$*" >&2
    exit 1
}

# Get one archive with the pin from sources.tsv. Column 1 is the archive
# name, unless the file names a package first.
fetch()
{
    name=$1
    table=$2
    line=$(awk -F '\t' -v n="$name" '$1 == n || $2 == n { print; exit }' "$table")
    [ -n "$line" ] || fail "No pin for $name in $table"
    sum=$(printf '%s\n' "$line" | awk -F '\t' -v n="$name" '{ print ($1 == n) ? $2 : $3 }')
    url=$(printf '%s\n' "$line" | awk -F '\t' -v n="$name" '{ print ($1 == n) ? $3 : $4 }')
    if [ ! -f "$distdir/$name" ]; then
        curl -fL --proto '=https' -o "$distdir/$name.part" "$url"
        mv "$distdir/$name.part" "$distdir/$name"
    fi
    [ "$(shasum -a 256 "$distdir/$name" | cut -d ' ' -f 1)" = "$sum" ] ||
        fail "Wrong SHA256: $distdir/$name"
}

# Check out one Khronos repository at the revision that the host tools pin.
checkout()
{
    name=$1
    rev=$2
    dir=$work/deps/src/$name
    [ -n "$rev" ] || fail "No revision pin for $name"
    if [ ! -d "$dir/.git" ]; then
        mkdir -p "$dir"
        git -C "$dir" init -q
        git -C "$dir" remote add origin "https://github.com/KhronosGroup/$name.git"
    fi
    if [ "$(git -C "$dir" rev-parse -q --verify HEAD || true)" != "$rev" ]; then
        git -C "$dir" fetch -q --depth 1 origin "$rev"
        git -C "$dir" checkout -q --detach "$rev"
    fi
}

mkdir -p "$work" "$distdir"
mesa_archive=mesa-26.2.5.tar.xz
llvm_archive=LLVM-23.1.3-macOS-ARM64.tar.xz
fetch "$mesa_archive" "$graphics/sources.tsv"
fetch "$llvm_archive" "$ports/profiles/common-build-tools/sources.tsv"

# 1. Authenticate and extract the native LLVM SDK.
sdk=$work/llvm-sdk/LLVM-23.1.3-macOS-ARM64
if [ ! -f "$work/llvm-sdk/outputs.json" ]; then
    rm -rf "$work/llvm-sdk"
    "$python" "$cross/prepare-llvm-macos.py" "$distdir/$llvm_archive" "$work/llvm-sdk"
fi

# 2. Build SPIRV-Headers, SPIRV-Tools and the translator.
pin_of()
{
    sed -n "s/^check_source $1 \([0-9a-f]*\)\$/\1/p" "$tools/build-deps.sh"
}
if [ ! -x "$work/deps/prefix/bin/spirv-val" ]; then
    checkout SPIRV-Headers "$(pin_of SPIRV-Headers)"
    checkout SPIRV-Tools "$(sed -n "s/^pin = '\([0-9a-f]*\)'\$/\1/p" "$tools/apply-spirv-tools-patches.rb")"
    checkout SPIRV-LLVM-Translator "$(pin_of SPIRV-LLVM-Translator)"
    sh "$tools/build-deps.sh" "$work/deps" "$sdk" "$host"
fi

# 3. Extract a separate Mesa source. The exact-BVNC patch is the only
# accepted source change.
if [ ! -f "$work/mesa-source/VERSION" ]; then
    rm -rf "$work/mesa-source" "$work/mesa-extract"
    mkdir "$work/mesa-extract"
    tar -xJf "$distdir/$mesa_archive" -C "$work/mesa-extract"
    patch -s -p1 -d "$work/mesa-extract/mesa-26.2.5" < "$tools/mesa-26.2.4-pco-bvnc.patch"
    mv "$work/mesa-extract/mesa-26.2.5" "$work/mesa-source"
    rmdir "$work/mesa-extract"
fi

# 4. Install the Python generator modules in the local environment.
if [ ! -x "$work/native/venv/bin/python3" ]; then
    mkdir -p "$work/native"
    "$python" -m venv "$work/native/venv"
    "$work/native/venv/bin/python3" -m pip install -q \
        mako packaging pyyaml lxml==6.1.3 rnc2rng==2.7.0
fi

# 5. Build the native Mesa tools with the existing configuration.
sh "$tools/configure-host.sh" "$work/native" "$work/mesa-source" "$sdk" \
    "$host" "$work/deps/prefix"

# 6. Seal the tools for the MesaLib recipe.
if [ ! -d "$work/sealed" ]; then
    "$ruby" "$graphics/cross/seal-mesa-generators.rb" --profile "$profile" \
        "$distdir/$mesa_archive" "$work/mesa-source" "$work/native/mesa" \
        "$work/deps/prefix/bin/spirv-val" "$work/sealed"
fi
echo "Sealed Mesa generators: $work/sealed"
echo "Set EMBERBSD_MESA_GENERATORS=$work/sealed in the cross MAKECONF."
