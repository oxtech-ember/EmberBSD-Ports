#!/bin/sh
# SPDX-License-Identifier: MIT
set -eu
recipe=$(CDPATH= cd "$(dirname "$0")" && pwd)
. "$recipe/common.sh"
[ "$#" = 1 ] || fail 'Usage: test.sh ABS_WORK'
work=$1
absolute "$work"
prefix=$work/install
[ -f "$prefix/share/ember-sdr/sources.tsv" ] || fail 'Missing completed profile install.'
cmp "$recipe/sources.tsv" "$prefix/share/ember-sdr/sources.tsv" >/dev/null || fail 'Installed source inventory differs.'
cmp "$recipe/patches.tsv" "$prefix/share/ember-sdr/patches.tsv" >/dev/null || fail 'Installed patch inventory differs.'
xml_prefix=$(cat "$prefix/share/ember-sdr/xml-prefix")
absolute "$xml_prefix"
cmp "$recipe/../libxml2/sources.tsv" "$prefix/share/ember-sdr/xml-sources.tsv" >/dev/null || fail 'Recorded XML provider differs.'
cmp "$prefix/share/ember-sdr/xml-sources.tsv" "$xml_prefix/share/ember-libxml2/sources.tsv" >/dev/null || fail 'XML provider inventory changed.'
cmp "$recipe/../../pkgsrc/devel/libiio/files/sources.tsv" "$prefix/share/ember-sdr/libiio-sources.tsv" >/dev/null || fail "Common libiio sources differ."
cmp "$recipe/../../pkgsrc/devel/libiio/distinfo" "$prefix/share/ember-sdr/libiio-distinfo" >/dev/null || fail "Common libiio patch set differs."
verify_recipe
jobs=${JOBS:-1}
positive JOBS "$jobs"
if [ "${BUILD_AS_KIB+x}" = x ]; then positive BUILD_AS_KIB "$BUILD_AS_KIB"; ulimit -S -v "$BUILD_AS_KIB"; fi
cmake=${CMAKE:-cmake}
export SOAPY_SDR_ROOT="$prefix" SOAPY_SDR_PLUGIN_PATH="$prefix/lib/SoapySDR/modules0.8"
export LD_LIBRARY_PATH="$prefix/lib:$xml_prefix/lib" DYLD_LIBRARY_PATH="$prefix/lib:$xml_prefix/lib"
run tests-configure "$cmake" -S "$recipe/tests" -B "$work/test-build" -G Ninja \
    -DSDR_PREFIX="$prefix" -DCMAKE_PREFIX_PATH="$prefix" -DLIBIIO_SOURCE="$work/src/libiio-1.0.0" \
    -DCMAKE_BUILD_TYPE=Release -DCMAKE_BUILD_RPATH="$prefix/lib"
run tests-build "$cmake" --build "$work/test-build" --parallel "$jobs"
mkdir -p "$work/fixtures/one" "$work/fixtures/two" "$work/fixtures/empty"
cp "$recipe/tests/fixture.xml" "$work/fixtures/one/fixture.xml"
sed 's/fixture-one/fixture-two/' "$recipe/tests/fixture.xml" > "$work/fixtures/two/fixture.xml"
sed 's/ad9361-phy/unrelated-sensor/' "$recipe/tests/fixture.xml" > "$work/fixtures/non-pluto.xml"
printf '<context broken' > "$work/fixtures/malformed.xml"
cp "$recipe/tests/fixture.xml" "$work/fixtures/empty/fixture.xml"
: > "$work/fixtures/empty/cf-ad9361-lpc_buf0.bin"
for fixture in one two; do "$work/test-build/make-iq" "$work/fixtures/$fixture/cf-ad9361-lpc_buf0.bin"; done
one=emu:$work/fixtures/one/fixture.xml
two=emu:$work/fixtures/two/fixture.xml
bad=emu:$work/fixtures/malformed.xml
other=emu:$work/fixtures/non-pluto.xml
run loopback-bind "$work/test-build/loopback"
run network-errors "$work/test-build/network-errors"
run compat-emu "$work/test-build/compat-contract" "$one"
run soapy-emu "$work/test-build/soapy-contract" "$one" "$two" "$bad" "$other"
run stream-error "$work/test-build/stream-error" "emu:$work/fixtures/empty/fixture.xml"
pids=
cleanup() {
    for pid in $pids; do kill "$pid" 2>/dev/null || :; done
    for pid in $pids; do wait "$pid" 2>/dev/null || :; done
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
# Single candidate pair, no scanning or fallback to another host/interface.
port=${SDR_TEST_PORT:-$((40000 + $$ % 10000))}
positive SDR_TEST_PORT "$port"
[ "$port" -le 65534 ] || fail 'SDR_TEST_PORT must be at most 65534.'
port_two=$((port + 1))
"$prefix/bin/iiod-emu" --loopback -p "$port" "$one" > "$work/logs/server-one.log" 2>&1 &
pid_one=$!
pids=$pid_one
"$prefix/bin/iiod-emu" --loopback -p "$port_two" "$two" > "$work/logs/server-two.log" 2>&1 &
pid_two=$!
pids="$pids $pid_two"
for server in one two; do
    attempt=0
    until grep -q 'Listening on port' "$work/logs/server-$server.log"; do
        kill -0 "$pid_one" 2>/dev/null && kill -0 "$pid_two" 2>/dev/null || fail 'Emulator exited before ready.'
        attempt=$((attempt + 1))
        [ "$attempt" -lt 10 ] || fail 'Emulator did not become ready.'
        sleep 1
    done
done
run compat-network "$work/test-build/compat-contract" "ip:127.0.0.1:$port"
run soapy-network "$work/test-build/soapy-contract" "ip:127.0.0.1:$port" "ip:127.0.0.1:$port_two" "$bad" "$other"
# Inventory is read-only. The Darwin trace also shows the runtime loaded by the shim.
case "$(uname -s)" in
    Darwin)
        { otool -L "$prefix/lib/libiio.so.0"; otool -L "$prefix/lib/libiio.1.dylib";
          otool -L "$prefix/lib/SoapySDR/modules0.8/libPlutoSDRSupport.so";
          otool -L "$work/test-build/soapy-contract"; } > "$work/logs/linked-libraries.txt"
        DYLD_PRINT_LIBRARIES=1 "$work/test-build/compat-contract" "$one" > "$work/logs/loaded-libraries.txt" 2>&1
        grep -F "$prefix/lib/libiio.1.0.0.dylib" "$work/logs/loaded-libraries.txt" >/dev/null || \
            grep -F "$prefix/lib/libiio.1.dylib" "$work/logs/loaded-libraries.txt" >/dev/null
        grep -F "$xml_prefix/lib/libxml2." "$work/logs/loaded-libraries.txt" >/dev/null || fail 'Project XML provider was not loaded.'
        ;;
    NetBSD)
        { ldd "$prefix/lib/libiio.so.0"; ldd "$prefix/lib/libiio.so.1";
          ldd "$prefix/lib/SoapySDR/modules0.8/libPlutoSDRSupport.so";
          ldd "$work/test-build/soapy-contract"; } > "$work/logs/linked-libraries.txt"
        grep -F "$xml_prefix/lib/libxml2.so.16" "$work/logs/linked-libraries.txt" >/dev/null || fail 'Wrong XML provider dependency.'
        if grep -E '/usr/pkg/(gcc|lib/lib(stdc\+\+|gcc_s))|not found' "$work/logs/linked-libraries.txt"; then fail 'Wrong or unresolved C++ ABI dependency.'; fi
        ;;
esac
find "$prefix" -type f | sort | while read -r path; do printf '%s %s\n' "$(sha "$path")" "$path"; done > "$work/logs/installed-sha256.txt"
printf '%s\n' 'PASS installed compat + Soapy RX, two contexts, tails, attributes, invalid contexts, loopback network and bounded libiio1 connection timeout.'
