# Local SDR receivers

This profile selects the common [AIS-catcher recipe](../../pkgsrc/ham/ais-catcher).
It receives both AIS channels through RTL-SDR or a raw CF32 file.
It does not provide a service, network feed, automatic device selection or web UI.

## Sources and dependencies

AIS-catcher v0.70 is pinned to upstream tag commit
`8833c64b3da0c42e9a724b9bd13eaab2fffadcca`, released on 2026-06-19.
The [upstream archive](https://github.com/jvde-github/AIS-catcher/archive/refs/tags/v0.70.tar.gz)
has SHA256 `e74af11d28c2a9739d4dc5de390ca208959171dd729585744864c65eafba85b7`.
The source permits GPLv3 or later. The package retains `LICENSE`.
Keep the corresponding source archive and these patches with binary distributions.

Use the common `ham/rtl-sdr` 2.0.3 and `devel/libusb1` 1.0.30nb1 providers.
The package requires both libraries and their headers.
The recipe cache file selects the same features for pkgsrc and direct cross builds.
SoapySDR, other device libraries, web UI, databases and optional network libraries are disabled.
The upstream CLI still has network features. Pass `-X off` for local-only reception.

The CMake patch preserves caller compiler flags and uses `CMAKE_DL_LIBS`, which is empty on NetBSD.
The RTL patch makes missing dependencies a configuration error when RTLSDR is enabled.
Two additional patches fix invalid signed-field shifts and escaped-string error offsets.
The socket include patch makes IPv4 types available on NetBSD.
The TCP patch uses `IPPROTO_TCP` and declares timeout values only when supported.
All six patches are local EmberBSD changes with AI assistance; none is submitted upstream.

## Build

Export Ports through its documented source workflow and build `ham/ais-catcher`
with the selected GCC16 SDK and an appropriate target sysroot.
Native pkgsrc creates the package and tracks the RTL-SDR and libusb dependencies.
The profile does not select a compiler from the host environment.

For a direct cross staging check, supply a source tree patched by the common recipe:

```sh
export PY=/absolute/sdk/bin/python3
export CC=/absolute/toolchain/bin/x86_64--netbsd-gcc
export CXX=/absolute/toolchain/bin/x86_64--netbsd-g++
export CMAKE=/absolute/sdk/bin/cmake
export NINJA=/absolute/sdk/bin/ninja
export PKG_CONFIG=/absolute/sdk/bin/pkg-config
sh profiles/sdr-receivers/cross/build.sh /absolute/patched-AIS-catcher \
    /absolute/sysroot /absolute/toolchain /absolute/new-work
```

The sysroot must contain matching GCC16 headers, CRT and runtime plus the common dependencies.
The helper records tools, checks the target and ELF output, and installs into `NEW_WORK/stage`.
This stage is not a registered package. Target execution and package lifecycle remain separate.

## Checks

Run source configuration regressions with explicitly selected native GCC16 tools:

```sh
export CC=/absolute/native-gcc16/bin/gcc
export CXX=/absolute/native-gcc16/bin/g++
"$PY" profiles/sdr-receivers/tests/configure.py /absolute/patched-source /absolute/new-config-check
```

`--baseline` expects the original missing-libdl failure, silent missing-RTL success and discarded caller C++ flags.
The NetBSD fixture runs real CMake with an empty library root and native GCC16.
It checks configuration behavior only, not target compilation or ABI compatibility.
On macOS, select the host SDK through `SDKROOT`.

Execute the independent synthetic decoder contract on the binary's own platform:

```sh
PY=/absolute/python3 sh profiles/sdr-receivers/tests/contracts.sh \
    /absolute/AIS-catcher /absolute/new-contract-check
```

This checks help, RTL backend inclusion, four messages per channel and bad-FCS rejection.
The generator uses artificial identities, zero coordinates and an unavailable-position sentinel.
Its CRC-16/X-25 check value for `123456789` is `0x906e`.
It does not use recorded radio samples or open a receiver.
The `181/91` unavailable-position values remain decoder protocol data; consumers must normalize them.

Run `AIS-catcher -L` separately when device enumeration is authorized.
Select an explicit device for live reception and retain `-X off`.
Synthetic decoding, enumeration and physical radio reception are distinct checks.

The actual-source safety tests cover full-width signed fields, invalid bit ranges
and malformed JSON after an escaped string. Both original defects fail sanitizers.

```sh
CXX=/absolute/native-gcc16/bin/g++ PY=/absolute/python3 \
    sh profiles/sdr-receivers/tests/source-safety.sh /absolute/patched-source /absolute/new-safety
```

Enable `ASAN_OPTIONS=detect_invalid_pointer_pairs=2:halt_on_error=1` for the pointer check.
Keep leak detection enabled on supported hosts. On Darwin, record unavailable
LeakSanitizer coverage separately if its runtime cannot start.
Clang Static Analyzer is diagnostic only; its outputs do not enter packages.

## Ordinary package creation and lifecycle

The bounded staging workflow uses real native pkgtools and an isolated installation
root. Prepare a bundle with `package-order.txt` in dependency order. For each named
package, provide `stage/usr/pkg`, an expanded `PLIST`, `DESCR`, `DEPENDENCIES` and
`BUILD_INFO`. `DEPENDENCIES` contains ordinary pkgsrc patterns separated by spaces.
Expand version placeholders and libtool `.la` payloads in the PLIST before packaging.
The metadata helper rejects any difference between this list and the staged files.

Record actual `OPSYS`, `OS_VERSION`, `MACHINE_ARCH`, `PKGPATH`, compiler versions,
`PKGTOOLS_VERSION` and source provenance in each `BUILD_INFO`. Obtain GCC runtime
payload and provenance from the common development-toolchain runtime verifier.
Keep corresponding sources and licenses with the distribution.

For every package in a new bundle, derive shared-library metadata from its actual
ELF files. The loader must be a verified input inside the selected sysroot:

```sh
"$PY" profiles/sdr-receivers/cross/package-metadata.py \
    "$package/stage/usr/pkg" "$READELF" "$SYSROOT" \
    "$package/PLIST" "$package/BUILD_INFO" "$package/BUILD_INFO.new" \
    "$bundle/base-root" "$LOADER"
mv "$package/BUILD_INFO.new" "$package/BUILD_INFO"
```

The helper records owned ELF libraries and aliases as `PROVIDES`, excludes those
libraries from external `REQUIRES`, and copies the transitive base-library closure.
It copies the verified loader at each executable's actual `PT_INTERP` path.
This includes dependencies such as `librt` used by the RTL tools, even when the
AIS executable itself does not need them. Base inputs retain their original ABI;
they are not rebuilt or registered as fabricated packages.

Select absolute native `PKG_CREATE`, `PKG_ADD`, `PKG_INFO`, `PKG_DELETE`, `PKG_ADMIN` and `SHA256`
executables. `SHA256` must support `-q`. Pin `PKGTOOLS_VERSION` and
`PKG_CREATE_SHA256` from the recorded native tools, then run:

```sh
sh profiles/sdr-receivers/tests/package-lifecycle.sh \
    "$bundle" /absolute/new-root /absolute/new-package-output
```

The regression creates and installs each package before creating its consumers.
`pkg_create` and `pkg_info` use the physical `NEW_ROOT/var/db/pkg` path;
`pkg_add` and `pkg_delete` use logical `/var/db/pkg` with `-P NEW_ROOT`.
It verifies actual `@pkgdep` and `@blddep` records, removes packages in reverse
order, checks that payloads, package records and ownership entries are absent,
and reinstalls them in dependency order. A real second package claiming an
installed file must fail without changing its bytes or owner. No package checks
are disabled.
Package ownership is normalized through `pkg_create -u root -g wheel`.
Failure preserves the private root, packages and database for diagnosis.

The underlying `cross/package.sh` performs creation and the initial isolated
installation only. Both workflows require new output paths. Neither establishes
target execution, real device enumeration, Qt compatibility or physical reception.

Older native pkgtools can leave stale logical ownership keys after `pkg_delete
-P`, although files and package records were removed. The common pkgtools source
already normalizes these keys in `lib/plist.c` (commit `b1204ec47d56`); corrected
tools are required for the default strict lifecycle test. Preserve a failed
strict run and its tool hashes. For an explicitly recorded experiment with old
native tools, `RECOVER_STALE_OWNERSHIP=1` enables a separate recovery mode: only
after every owned path and actual package record is absent, official
`pkg_admin rebuild` reconstructs the index from real `+CONTENTS` records. The
index must then be empty. Reinstallation must restore exactly the previous
ownership map, and the genuine duplicate package must still be rejected. Dumps
before and after recovery are retained. This mode does not qualify the old
`pkg_delete` or turn its strict failure into a pass.
