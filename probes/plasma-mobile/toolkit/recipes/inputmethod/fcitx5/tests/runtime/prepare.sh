#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Package original upstream runtime tests.
set -eu
[ "$#" = 4 ] || {
    echo "Usage: $0 SOURCE BUILD SOURCE_ARCHIVE NEW_PAYLOAD" >&2
    exit 2
}
source=$1 build=$2 archive=$3 out=$4
for item in "$@"; do
    case "$item" in /*) ;; *) echo 'Absolute paths required' >&2; exit 2 ;; esac
done
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
recipe=$(CDPATH= cd -- "$here/../.." && pwd -P)
hash_file() {
    if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | awk '{print $1}'
    elif command -v sha256 >/dev/null 2>&1; then sha256 -q "$1"
    else shasum -a 256 "$1" | awk '{print $1}'
    fi
}
expected=d287119db9dc3113bb3a2b0e78ce8670e064b744c14d3aaec69799374aadb00b
[ "$(hash_file "$archive")" = "$expected" ] || { echo 'Source archive hash mismatch' >&2; exit 1; }
target_source=$(sed -n 's/^#define FCITX5_SOURCE_DIR "\(.*\)"$/\1/p' "$build/test/testdir.h")
target_build=$(sed -n 's/^#define FCITX5_BINARY_DIR "\(.*\)"$/\1/p' "$build/test/testdir.h")
case "$target_source" in /*/source) ;; *) echo 'Configure a target fixture root ending in /source' >&2; exit 1 ;; esac
target_root=${target_source%/source}
[ "$target_build" = "$target_root/build" ] || { echo 'Configure the matching target /build fixture root' >&2; exit 1; }
[ ! -e "$out" ] && [ ! -L "$out" ]
mkdir "$out"
out=$(cd "$out" && pwd -P)
mkdir -p "$out/build/bin" "$out/build/test/addon" "$out/build/src/modules" "$out/source" "$out/provenance"
tar -xf "$archive" -C "$out/source" --strip-components 1 \
    fcitx5-5.1.23/test fcitx5-5.1.23/LICENSES \
    fcitx5-5.1.23/src/modules/emoji/data \
    fcitx5-5.1.23/src/modules/unicode/charselectdata \
    fcitx5-5.1.23/src/modules/quickphrase/quickphrase.d
# Only the two test path plumbing files differ from the upstream archive.
# Recreate those expected changes from the verified recipe patches.
for item in patch-test_CMakeLists.txt patch-test_testdir.h.in; do
    actual=$(sed '/^\$NetBSD/d' "$recipe/patches/$item" | shasum | awk '{print $1}')
    expected_patch=$(awk -v name="($item)" '$1 == "SHA1" && $2 == name {print $4}' "$recipe/distinfo")
    [ "$actual" = "$expected_patch" ]
    cp "$recipe/patches/$item" "$out/provenance/"
    patch -s -F 0 -d "$out/source" -p0 < "$recipe/patches/$item"
done
# The source tree has generated files in some subdirectories. Compare every
# archived test source/fixture, not generated build files or backup files.
(cd "$out/source" && find test -type f | LC_ALL=C sort) > "$out/provenance/upstream-test-files.txt"
while read -r item; do cmp "$out/source/$item" "$source/$item"; done < "$out/provenance/upstream-test-files.txt"
cp "$here/cases.tsv" "$here/run.sh" "$here/README.md" "$out/"
cp "$build/config.h" "$build/test/testdir.h" "$build/test/CTestTestfile.cmake" "$out/provenance/"
printf '%s\n' "$target_root" > "$out/provenance/target-root.txt"
sed -n 's/^add_test(\([^ ]*\) .*/\1/p' "$build/test/CTestTestfile.cmake" | LC_ALL=C sort > "$out/provenance/registered.txt"
cut -f 1 "$here/cases.tsv" | LC_ALL=C sort > "$out/provenance/expected.txt"
cmp "$out/provenance/expected.txt" "$out/provenance/registered.txt"
[ "$(wc -l < "$out/provenance/registered.txt" | tr -d ' ')" = 51 ]
while IFS="$(printf '\t')" read -r name mode; do
    case "$mode" in remote) continue ;; direct|dbus|data|fixture) ;; *) exit 1 ;; esac
    [ -x "$build/bin/$name" ] || { echo "Missing target test: $name" >&2; exit 1; }
    file "$build/bin/$name" | grep -q 'ELF 64-bit LSB.*ARM aarch64'
    cp "$build/bin/$name" "$out/build/bin/"
done < "$here/cases.tsv"
# Only these two modules are uninstalled test fixtures. All production and
# installed testing modules are resolved from /usr/pkg on the target.
for item in libdummyaddon.so libdummyaddondeps.so; do
    [ -f "$build/bin/$item" ]
    cp "$build/bin/$item" "$out/build/bin/"
done
for item in "$build/test/addon"/*.conf; do cp "$item" "$out/build/test/addon/"; done
for item in "$build/src/modules"/*/*.conf; do
    relative=${item#"$build/"}
    # Preserve the upstream build-root-relative module layout.
    mkdir -p "$out/build/$(dirname "$relative")"
    cp "$item" "$out/build/$relative"
done
[ -s "$build/src/modules/spell/en_dict.fscd" ]
cp "$build/src/modules/spell/en_dict.fscd" "$out/build/src/modules/spell/"
printf '%s  %s\n' "$expected" "${archive##*/}" > "$out/provenance/source-archive.sha256"
printf 'Source: %s\nBuild: %s\n' "$source" "$build" > "$out/provenance/local-build.txt"
cd "$out"
find . -type f ! -name SHA256.tsv | LC_ALL=C sort | while read -r item; do
    printf '%s\t%s\n' "$(hash_file "$item")" "${item#./}"
done > SHA256.tsv
printf 'Prepared all 51 registered cases for target fixture root %s\n' "$target_root"
printf 'No target program was executed. Payload: %s\n' "$out"
