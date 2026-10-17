#!/bin/sh
# EmberBSD E12: reconstruct the cross Chromium tree from distfiles.
# Tree: /Volumes/BigData/EmberBSD/work/e12-chromium (agent-local source copy).
# The full cross adaptation set ships as patches/e12-cross-adaptations.patch
# (git diff of the validated tree; libbase.a reproduced byte-identical).
set -eu
BIG=/Volumes/BigData/EmberBSD
DIST=$BIG/distfiles/e12-electron
TREE=$BIG/work/e12-chromium
PROBE=$BIG/work/emberbsd-ports/probes/electron
CROSSTOOLS=$BIG/work/ember-gcc16-toolchain/bin
RUST=$HOME/.rustup/toolchains/nightly-2026-06-17-aarch64-apple-darwin/bin

rm -rf "$TREE"; mkdir -p "$TREE"; cd "$TREE"
COPYFILE_DISABLE=1 tar --no-xattrs -xf "$DIST/chromium-152.0.7977.82.tar.xz" --strip-components=1
git init -q && git add -A
git -c user.name=ember-e12 -c user.email=e12@ember commit -qm "Chromium 152.0.7977.82 official tarball (baseline)"

# chromium-nb patchset (expect exactly 2 rollup-napi failures: N/A upstream files)
fail=0
for p in $BIG/work/emberbsd-ports/upstream/pkgsrc/www/chromium/patches/patch-*; do
  patch --forward --no-backup-if-mismatch -p0 -i "$p" >/dev/null 2>&1 || fail=$((fail+1))
done
rm -f Oops.rej
[ "$fail" -eq 2 ] || { echo "unexpected nb patch failures: $fail"; exit 1; }

# chromium-nb overlay files (netbsd platform sources)
tar -xzf "$DIST/chromium-nb-v151.1.tar.gz" -C /tmp
(cd /tmp/chromium-nb-* && tar -cf - $(find . -type f -not -path './patches/*' -not -name '.gitignore' | sed 's|^\./||')) | tar -xf -
rm -rf /tmp/chromium-nb-*
git add -A && git -c user.name=ember-e12 -c user.email=e12@ember commit -qm "chromium-nb v151.1 patchset + overlay files"

# the validated EmberBSD cross adaptation set
patch -p1 < "$PROBE/patches/e12-cross-adaptations.patch"
git add -A && git -c user.name=ember-e12 -c user.email=e12@ember commit -qm "E12 cross adaptations"

# host tool symlinks
mkdir -p third_party/rust-toolchain/bin && ln -sf "$RUST/rustc" third_party/rust-toolchain/bin/rustc
mkdir -p third_party/gperf/cipd/bin && ln -sf /usr/bin/gperf third_party/gperf/cipd/bin/gperf
for n in netbsd/node-netbsd mac_arm64/node-darwin-arm64; do
  mkdir -p third_party/node/$n/bin && ln -sf /opt/homebrew/opt/node@24/bin/node third_party/node/$n/bin/node
done
mkdir -p sdk/xcode_links && ln -sfn "$(xcrun --show-sdk-path)" sdk/xcode_links/MacOSX27.0.sdk
cp "$DIST/package/bin/esbuild" third_party/devtools-frontend/src/third_party/esbuild/esbuild
chmod +x third_party/devtools-frontend/src/third_party/esbuild/esbuild
mkdir -p third_party/devtools-frontend/src/node_modules/@rollup/rollup-darwin-arm64
tar -xzf "$DIST/rollup-darwin-arm64-4.60.4.tgz" -C third_party/devtools-frontend/src/node_modules/@rollup/rollup-darwin-arm64 --strip-components=1

# ffmpeg configs
(cd media/ffmpeg && EMBER_FFMPEG_CROSS_PREFIX="$CROSSTOOLS/aarch64--netbsd-" \
  /opt/homebrew/bin/python3 scripts/build_ffmpeg.py netbsd arm64 --config-only --branding=Chrome >/dev/null)
B=third_party/ffmpeg/build.arm64.netbsd/Chrome
(cd "$B" && make libavutil/ffversion.h >/dev/null 2>&1 || true)
D=third_party/ffmpeg/chromium/config/Chrome/netbsd/arm64; mkdir -p "$D"
for p in config.h config_components.h libavcodec libavformat libavutil; do cp -pR "$B/$p" "$D/"; done

mkdir -p out/e12
cat > out/e12/args.gn << 'ARGS'
target_os = "netbsd"
target_cpu = "arm64"
custom_toolchain = "//build/toolchain/netbsd:gcc_arm64"
is_clang = false
use_lld = false
use_sysroot = false
is_debug = false
is_component_build = false
is_official_build = false
chrome_pgo_phase = 0
treat_warnings_as_errors = false
fatal_linker_warnings = false
use_partition_alloc = true
use_partition_alloc_as_malloc = false
use_custom_libcxx = true
use_qt5 = false
use_qt6 = false
use_kerberos = false
use_cups = false
use_sndio = false
use_vaapi = false
use_udev = true
disable_fieldtrial_testing_config = true
enable_backup_ref_ptr_support = false
emberbsd_target_sysroot = "/Volumes/BigData/EmberBSD/build/sysroot"
clang_base_path = "/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr"
extra_cxxflags = "-std=gnu++23"
use_system_xcode = true
clang_use_chrome_plugins = false
use_allocator_shim = false
ARGS

PATH="$CROSSTOOLS:/opt/homebrew/bin:$PATH" /opt/homebrew/bin/python3 tools/gn/bootstrap/bootstrap.py -o out/Release/gn >/dev/null 2>&1 || true
PATH="$CROSSTOOLS:/opt/homebrew/bin:$PATH" ./out/Release/gn gen out/e12 --script-executable=/opt/homebrew/bin/python3
echo "DONE"
