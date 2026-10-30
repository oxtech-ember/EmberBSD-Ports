#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# AI-assisted source candidate, using the upstream frozen dependency graph.
set -eu
[ "$#" -eq 2 ] || { echo 'Usage: build-zigbee2mqtt.sh NEW_WORK ARCHIVE_CACHE' >&2; exit 2; }
work=$1
cache=$2
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
NODE=${NODE:-}
[ -n "$NODE" ] || { echo 'Select the common Node26 with NODE.' >&2; exit 2; }
case "$NODE" in /*) ;; *) echo 'NODE must be an absolute executable path.' >&2; exit 2 ;; esac
[ "$("$NODE" --version)" = v26.13.0 ] || { echo 'Use common Node26.13.0.' >&2; exit 2; }
PATH=$(dirname "$NODE"):$PATH
export PATH
case "$(uname -s)" in
    NetBSD)
        CC=${CC:-/usr/pkg/gcc16/bin/gcc}
        CXX=${CXX:-/usr/pkg/gcc16/bin/g++}
        case "$("$CC" -dumpfullversion)" in 16.2.*) ;; *) exit 2 ;; esac
        [ "$("$CC" -dumpfullversion)" = "$("$CXX" -dumpfullversion)" ] || exit 2
        runtime=$(dirname "$("$CXX" -print-file-name=libstdc++.so)")
        LDFLAGS="${LDFLAGS:-} -Wl,-rpath,$runtime"
        npm_config_build_from_source=true
        export CC CXX LDFLAGS npm_config_build_from_source
        ;;
    *) [ "${EMBER_HOST_CHECK:-0}" = 1 ] || {
        echo 'Native EmberBSD/NetBSD required; EMBER_HOST_CHECK=1 permits a host-only check.' >&2
        exit 2
    } ;;
esac
sh "$here/prepare.sh" zigbee2mqtt "$work" "$cache"
run()
{
    stage=$1; shift
    result=0
    "$@" > "$work/logs/$stage.log" 2>&1 || result=$?
    if [ "$result" -ne 0 ]; then tail -50 "$work/logs/$stage.log" >&2; exit "$result"; fi
}
read -r archive expected url <<EOF
$(awk '!/^#/ && NF {print}' "$here/sources/pnpm.tsv")
EOF
cp "$cache/$archive" "$work/archives/$archive"
if command -v sha256 >/dev/null 2>&1; then actual=$(sha256 -q "$work/archives/$archive")
else actual=$(shasum -a 256 "$work/archives/$archive" | awk '{print $1}'); fi
[ "$actual" = "$expected" ] || { echo 'pnpm checksum mismatch.' >&2; exit 2; }
mkdir "$work/pnpm"
tar -xzf "$work/archives/$archive" --strip-components=1 -C "$work/pnpm"
pnpm=$work/pnpm/bin/pnpm.cjs
[ "$("$NODE" "$pnpm" --version)" = 11.26.0 ]
cp "$here/sources/pnpm.tsv" "$work/logs/pnpm.tsv"
{ uname -a; "$NODE" --version; "$NODE" "$pnpm" --version; } > "$work/logs/environment.txt"
MAKEFLAGS=-j1
npm_config_jobs=1
export MAKEFLAGS npm_config_jobs
cd "$work/source"
run install "$NODE" "$pnpm" install --frozen-lockfile --ignore-scripts \
    --package-import-method=copy --store-dir "$work/store"
# Resolve the exact transitive package after integrity-checked installation.
# Copy import above prevents edits from modifying the pnpm content store.
bindings=$("$NODE" -e 'const {createRequire}=require("node:module"); const path=require("node:path");
const req=createRequire(require.resolve("zigbee-herdsman"));
const file=req.resolve("@serialport/bindings-cpp/package.json");
if(req(file).version!=="13.0.1") process.exit(2); console.log(path.dirname(file));')
run serial-patch patch -f -N -F 0 -p1 -d "$bindings" -i "$here/patches/serialport-netbsd-list.patch"
run rebuild "$NODE" "$pnpm" rebuild
run build "$NODE" "$pnpm" run build
# The release archive has no .git. This is the verified upstream release commit.
printf '%s' 5c0c1c60 > dist/.hash
SERIALPORT_BINDINGS=$bindings
export SERIALPORT_BINDINGS
run serial-test "$NODE" --test "$here/test-serial-list.cjs"
run upstream-test "$NODE" "$pnpm" test
echo "Built and tested Zigbee2MQTT source candidate on $(uname -s): $work/source"
echo 'Radio pairing, MQTT device traffic and service packaging require separate acceptance.'
