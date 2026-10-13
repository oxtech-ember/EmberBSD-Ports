#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), native upstream Fcitx5 dictionary compiler.
set -eu
[ "$#" = 4 ] || {
    echo 'Usage: build-fcitx5-host.sh DISTFILES NATIVE_PREFIX ECM_CMAKE_DIR NEW_WORK' >&2
    exit 2
}
dist=$1 native=$2 ecm=$3 work=$4
: "${CMAKE:?Set native CMake}" "${NINJA:?Set native Ninja}"
: "${HOST_CC:?Set native C compiler}" "${HOST_CXX:?Set native C++ compiler}"
: "${JOBS:=1}"
for item in "$dist" "$native" "$ecm" "$work" "$CMAKE" "$NINJA" "$HOST_CC" "$HOST_CXX"; do
    case "$item" in /*) ;; *) echo 'Absolute paths required' >&2; exit 2 ;; esac
    case "$item" in *[!a-zA-Z0-9_./+-]*) echo 'Use paths without shell/CMake metacharacters' >&2; exit 2 ;; esac
done
case "$JOBS" in ''|*[!0-9]*|0) echo 'JOBS must be a positive integer' >&2; exit 2 ;; esac
for program in "$CMAKE" "$NINJA" "$HOST_CC" "$HOST_CXX" "$native/bin/pkg-config" "$native/bin/msgfmt" "$native/bin/msgmerge"; do
    [ -x "$program" ] || { echo "Missing native tool: $program" >&2; exit 2; }
done
[ -f "$ecm/ECMConfig.cmake" ]
intl_include=$native/include
[ ! -f "$native/include/gettext/libintl.h" ] || intl_include=$native/include/gettext
[ -f "$intl_include/libintl.h" ]

# Official release inputs: https://download.fcitx-im.org/fcitx5/ and /data/.
# These pins must follow the target recipe's version and dictionary contract.
source_archive=fcitx5-5.1.23.tar.zst
source_sha=d287119db9dc3113bb3a2b0e78ce8670e064b744c14d3aaec69799374aadb00b
dict_archive=en_dict-20121020.tar.gz
dict_sha=c44a5d7847925eea9e4d2d04748d442cd28dd9299a0b572ef7d91eac4f5a6ceb
verify()
{
    [ "$(shasum -a 256 "$1" | awk '{print $1}')" = "$2" ] || {
        echo "SHA256 mismatch: $1" >&2
        exit 1
    }
}
verify "$dist/$source_archive" "$source_sha"
verify "$dist/$dict_archive" "$dict_sha"
mkdir "$work"
mkdir "$work/source" "$work/bin" "$work/check"
shasum -a 256 "$dist/$source_archive" "$dist/$dict_archive" "$0" \
    "$CMAKE" "$NINJA" "$HOST_CC" "$HOST_CXX" "$native/bin/pkg-config" \
    "$native/bin/msgfmt" "$native/bin/msgmerge" "$intl_include/libintl.h" \
    "$ecm/ECMConfig.cmake" > "$work/inputs.sha256"
{
    "$CMAKE" --version
    "$NINJA" --version
    "$HOST_CXX" --version
    "$native/bin/msgfmt" --version
} > "$work/tools.txt" 2>&1
tar -xf "$dist/$source_archive" -C "$work/source"
tar -xf "$dist/$dict_archive" -C "$work/check"
source=$work/source/fcitx5-5.1.23
# Only the build-time generator and its Utils library are needed on the host.
# These host-only choices do not change any target package feature or test.
"$CMAKE" -S "$source" -B "$work/build" -G Ninja \
    -DCMAKE_MAKE_PROGRAM="$NINJA" -DCMAKE_C_COMPILER="$HOST_CC" \
    -DCMAKE_CXX_COMPILER="$HOST_CXX" -DCMAKE_PREFIX_PATH="$native" \
    -DECM_DIR="$ecm" -DLibIntl_INCLUDE_DIR="$intl_include" \
    -DGETTEXT_MSGFMT_EXECUTABLE="$native/bin/msgfmt" \
    -DGETTEXT_MSGMERGE_EXECUTABLE="$native/bin/msgmerge" \
    -DPKG_CONFIG_EXECUTABLE="$native/bin/pkg-config" \
    -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="$work/prefix" \
    -DCMAKE_EXPORT_COMPILE_COMMANDS=ON -DBUILD_SHARED_LIBS=OFF \
    -DENABLE_X11=OFF -DENABLE_WAYLAND=OFF -DENABLE_DBUS=OFF \
    -DENABLE_SERVER=OFF -DENABLE_KEYBOARD=OFF -DENABLE_EMOJI=OFF \
    -DENABLE_ENCHANT=OFF -DENABLE_LIBUUID=OFF -DEVENT_LOOP_BACKEND=none \
    -DENABLE_TEST=OFF -DENABLE_TESTING_ADDONS=OFF -DENABLE_DOC=OFF \
    -DBUILD_SPELL_DICT=ON > "$work/configure.log" 2>&1
intl_library=$(sed -n 's/^LibIntl_LIBRARY:FILEPATH=//p' "$work/build/CMakeCache.txt")
if [ -n "$intl_library" ]; then
    shasum -a 256 "$intl_library" >> "$work/inputs.sha256"
fi
"$CMAKE" --build "$work/build" --target comp-spell-dict --parallel "$JOBS" \
    > "$work/build.log" 2>&1
cp "$work/build/bin/comp-spell-dict" "$work/bin/comp-spell-dict"
tool=$work/bin/comp-spell-dict
file "$tool" > "$work/binary.txt"

# Check the actual upstream binary format, including little-endian count and
# frequency clamping. Keep paths with spaces in this runtime acceptance case.
export LC_ALL=C
printf '1 hello\n70000 world\n' > "$work/check/tiny input.txt"
printf 'FSCD0000\002\000\000\000\001\000hello\000\377\377world\000' > "$work/check/expected.fscd"
"$tool" --comp-dict "$work/check/tiny input.txt" "$work/check/tiny output.fscd"
cmp "$work/check/expected.fscd" "$work/check/tiny output.fscd"
"$tool" --comp-dict "$work/check/en_dict.txt" "$work/check/en_dict.fscd"
"$tool" --comp-dict "$work/check/en_dict.txt" "$work/check/repeat.fscd"
cmp "$work/check/en_dict.fscd" "$work/check/repeat.fscd"
# Golden bytes also match an independent encoder of the pinned input records.
verify "$work/check/en_dict.fscd" 4f1a4416ed0ce8ba7d13c9280bf6f83e66cee3903b330e5e1d136288fa841452
[ "$(dd if="$work/check/en_dict.fscd" bs=1 count=8 2>/dev/null)" = FSCD0000 ]
set -- $(od -An -tu1 -j8 -N4 "$work/check/en_dict.fscd")
[ "$#" = 4 ]
count=$(( $1 + $2 * 256 + $3 * 65536 + $4 * 16777216 ))
[ "$count" -gt 0 ]
[ "$count" -eq "$(awk 'END {print NR}' "$work/check/en_dict.txt")" ]
expected_size=$(awk '{sub(/^[^ ]* /, ""); size += length($0) + 3} END {print 12 + size}' "$work/check/en_dict.txt")
[ "$expected_size" -eq "$(wc -c < "$work/check/en_dict.fscd")" ]
printf 'invalid\n' > "$work/check/invalid.txt"
if "$tool" --comp-dict "$work/check/invalid.txt" "$work/check/invalid.fscd"; then
    echo 'Invalid dictionary unexpectedly succeeded' >&2; exit 1
else
    [ "$?" -eq 1 ] || { echo 'Invalid-input check crashed' >&2; exit 1; }
fi
if "$tool" --comp-dict "$work/check/missing.txt" "$work/check/missing.fscd"; then
    echo 'Missing dictionary unexpectedly succeeded' >&2; exit 1
else
    [ "$?" -eq 1 ] || { echo 'Missing-input check crashed' >&2; exit 1; }
fi
printf '5.1.23\n' > "$work/version.txt"
printf 'PASS: %s entries; exact tiny fixture; deterministic output; invalid/missing input rejected\n' "$count" > "$work/check/result.txt"
shasum -a 256 "$tool" "$work/check/en_dict.fscd" "$work/check/tiny output.fscd" > "$work/outputs.sha256"
cat "$work/check/result.txt"
printf 'EMBERBSD_FCITX5_COMP_SPELL_DICT=%s\n' "$tool"
printf '%s\n' 'Native generator acceptance only. Target package and input session remain separate gates.'
