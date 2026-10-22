# Electron runtime probe for NetBSD (E12 Blanc browser)

Goal: run Blanc v1.25.0 on EmberBSD. Blanc uses Electron and has no
engine abstraction, so this port needs the native Electron runtime.

## Source pins

| Component | Pin | Source |
|---|---|---|
| Electron | 44.9.3 (`c542df1ecbc2c2978e8f53f8c7baf602404d166f`) | GitHub tag `v44.9.3` |
| Chromium | 152.0.7977.167 (`dd78960ccd8a03a2fe1f629543d27783885b78e9`) | Electron `DEPS` |
| Embedded Node.js | 24.22.0 | Electron `DEPS` |
| Chromium host Node.js | 24.12.0 | `third_party/node/update_node_binaries` |
| Blanc | 1.25.0 (`ff55d5948f5c71e802ba2ac464659ef96e055ca9`) | GitHub tag `v1.25.0` |

Electron's `DEPS` graph is the Chromium source of record. Do not substitute the
pkgsrc `.82` archive. Chromium sources require `gclient`; the older archive does
not match Electron's pinned revision.

| Distfile | Size | SHA256 |
|---|---:|---|
| `v44.9.3.tar.gz` | 20,838,185 | `e4e84b70a501c7dffec78bf037309bfe336daee6886289f94f9ac035ec54d80f` |
| `node-v24.22.0.tar.xz` | 57,606,320 | `41f97cff2c666f1f8293dc5f85c65e8dd605c16b43fd9febd49ede32ee1e0329` |
| `v1.25.0.tar.gz` | 155,108,408 | `b241d6b135b0fab5839f5dea6f64fafbdefa4f213b46ffa4a2f78820cb880971` |

## Target contract

- Build on the developer host. Cross-compile all target objects for
  `aarch64--netbsd` or `x86_64--netbsd` with GCC 16.2.0 and the matching
  EmberBSD sysroot. GN names those CPUs `arm64` and `x64` respectively.
- Keep host tools separate. Xcode Clang may build host-only tools; target
  compilation must use GCC16.
- Enable Linux-conditioned Chromium source dependencies only to fetch their
  shared code. Do not use a Linux sysroot or Linux target objects.
- Adapt the `chromium-nb` and Electron patch sets to the exact Chromium pin.
  Record the overlay revision and every required drift fix.
- Keep Electron's Chromium sandbox enabled. Do not replace Chromium or Electron
  with another browser engine.

## Current status

- Electron and Node distfiles are pinned to the current supported Electron 44.x
  release and its exact Chromium revision.
- The pkgsrc Chromium baseline is 152.0.7977.82 with `chromium-nb` 151.1. A
  per-patch dry run against Electron's 152.0.7977.167 source applied 1,622 of
  1,641 patches. Five patch hunks need adaptation and fourteen targets are
  absent from the Electron tree. A dry run does not establish patch ordering or
  build correctness.
- The NetBSD GCC16 toolchain and cross sysroot are available. Focused production
  GN checks retain explicit target ELF tools and target pkgsrc metadata.
  Complete target compilation and linking remain separate acceptance gates.
- No complete Chromium link, Electron runtime package, Blanc package, or target
  application acceptance run exists yet. Do not treat partial object builds as
  completion.
- Full runtime and application package lifecycle checks remain pending.
- The Blanc application recipe creates an ASAR from an explicit source
  allowlist and 32 lockfile-pinned runtime packages. Eight separate packages
  provide the upstream ASAR build tool. The host controller uses CPython 3.15
  and SDK API 1. Host Node.js 24.22.0 runs required upstream JavaScript tools.
  This application archive does not contain an Electron executable.
- The Blanc source patches select an explicit NetBSD capture descriptor. It
  uses the existing generic Electron/DOM/WebRTC broker, preload and helper.
  All nine runtime and fourteen shared permission hashes remain unchanged.
  A causal host Node24 test fails with `Unsupported capture platform` before
  the change; the patched source passes all 76 focused capture tests. This
  verifies source dispatch and locks. It does not verify native Electron
  startup or NetBSD media capture. Changes to these generic files require
  impact review for Windows and NetBSD.

## Blanc application package

Export the recipes with the explicit profile:

```sh
sh scripts/prepare-pkgsrc.sh /absolute/NEW_PKGSRC electron
```

The profile adds `www/blanc` and `devel/electron44`. It refuses an existing
destination or an upstream recipe collision. Select the common GCC16 cross
configuration for the target runtime. Set `EMBERBSD_HOST_NODE` to the absolute
host Node.js 24.22.0 executable. Set `EMBERBSD_CROSS_BUILD_PYTHON` to the
selected host CPython 3.15 executable. Set `EMBERBSD_SDK_SOURCE` to an absolute
SDK API 1 source directory. The controller checks the SDK API and module origin.

The recipe fetches the source and 40 NPM archives through pkgsrc distfiles.
The build uses verified local archives and runs no NPM installation or network
fetch. It extracts only allowlisted source files. It keeps tests, build tools,
the lockfile, and environment files out of the installed ASAR. The installed
SBOM records the external Electron 44.9.3 package separately from upstream's
development lock on Electron 44.5.1. A different runtime declaration is refused.

The wrapper selects Electron's packaged application policy. It leaves sandbox
flags unchanged. NetBSD self-updates are disabled because pkgsrc owns updates.
The upstream license notices and the dependency license texts remain installed.
The Blue Oak license text is in `blanc/files/blueoak-1.0.0.txt`; the pinned
pkgsrc catalog does not include its token. Review that text before adding
`blueoak-1.0.0` to `ACCEPTABLE_LICENSES`. Keep the recipe's redistribution
restrictions for unchanged upstream artwork and marks.

The host checks passed 11 package-controller tests and 22 focused Node tests.
The produced ASAR contains 1,674 entries. The production-only registry audit
reported no advisories for the 32 installed runtime packages. This does not
clear the separate upstream development dependency audit. Direct pkgsrc
extraction, patch, build, test, and staged install passed. The ASAR and SBOM
match the independent allowlist build byte-for-byte. The full pkgsrc dependency
lifecycle, target startup, and kernel sandbox acceptance remain unverified.
The application package cannot be installed until the target runtime is built.

## GN and C++ target inputs

The GN and parser patches retain the exact Chromium pin above. Apply them after
its NetBSD GN adaptations, from the Chromium source root:

```sh
patch -p0 -F 0 < /absolute/Ports/probes/electron/patches/gn-pkgconfig-libdir.patch
patch -p1 -F 0 < /absolute/Ports/probes/electron/patches/gn-unbundle-readelf.patch
patch -p0 -F 0 < /absolute/Ports/probes/electron/patches/gn-unbundle-asmflags.patch
patch -p1 -F 0 < /absolute/Ports/probes/electron/patches/gn-rust-bindgen-host-tools.patch
patch -p1 -F 0 < /absolute/Ports/probes/electron/patches/gn-netbsd-x64-targets.patch
patch -p1 -F 0 < /absolute/Ports/probes/electron/patches/gn-rust-version-netbsd.patch
patch -p1 -F 0 < /absolute/Ports/probes/electron/patches/gn-clang-resource-version.patch
patch -p1 -F 0 < /absolute/Ports/probes/electron/patches/gn-bindgen-gcc-warnings.patch
patch -p1 -F 0 < /absolute/Ports/probes/electron/patches/gn-host-node-inputs.patch
patch -p1 -F 0 < /absolute/Ports/probes/electron/patches/electron-netbsd-main.patch
patch -p1 -F 0 < /absolute/Ports/probes/electron/patches/gn-mac-host-debug-fission.patch
patch -p1 -F 0 < /absolute/Ports/probes/electron/patches/partition-alloc-netbsd-gcc16.patch
```

The pkg-config patch keeps the effective `pkg/lib` value in the common cross
arguments. The legacy target block cannot append a later `lib` value.
Ordinary Linux, native, host wrapper and cached-result arguments stay unchanged.
The unbundle patch requires `READELF` for a NetBSD cross toolchain. It forwards
that value to the production shared-library wrapper. Native NetBSD, Linux and
host toolchains retain their existing `readelf` fallback. It does not enable
stripping or change the compiler selection. The assembler patch forwards
`ASFLAGS` and `BUILD_ASFLAGS` to their respective toolchains. Select the target
sysroot and other assembler flags through `ASFLAGS`. Unset values stay empty.
The Rust patch restores the pinned `bindgen`, `rustfmt`, and libclang paths
from `rust_bindgen_root`. It adds EmberBSD parser headers only to a NetBSD
target toolchain whose OS or CPU differs from the build host. Host actions,
native NetBSD, and unrelated target platforms do not receive those headers.
The x64 supplement extends the existing pkgsrc metadata selection and adds
`x86_64-unknown-netbsd` to the bindgen parser arguments. It preserves the
existing ARM64 selector and triple.
The resource-version patch restores the upstream Clang version selection.
The Apple host tools use the pinned compiler below `clang_base_path`, so their
headers and compiler runtime must use that compiler's resource version.
The target C/C++ compiler remains GCC16.
The parser patch removes three GCC-only diagnostic switches and `--param=`
optimizer settings only from libclang's inputs. Target compiler arguments,
`-Werror`, target triple, and sysroot remain unchanged.
The host-Node patch selects local executables by `host_os` for generic Node
and TypeScript protoc actions. It retains Linux Node for remote workers.
The Electron main patch selects the upstream POSIX main and stdio helper for
NetBSD. Its glibc environment shim stays in the unchanged Linux branch.
The Mac patch keeps ordinary DWARF in host objects during cross-builds. Target
GCC16 still emits split DWARF. Native Mac toolchain arguments stay unchanged.
The PartitionAlloc patch matches NetBSD's const-qualified `malloc_usable_size`
declaration. It also uses a width-checked unsigned shift for the existing slot
metadata invariant. It keeps other libc signatures and allocator policy.

Commands, coverage, and limitations are in [the GN regression guide](tests/README.md).

Apply the carried libc++ fix from its separate source root after its exact
DEPS revision and Electron patches are present:

```sh
cd /absolute/chromium/src/third_party/libc++/src
patch -p1 -F 0 < /absolute/Ports/probes/electron/patches/libcxx-gcc16-maxsize-function-sbo.patch
```

The fix bounds string allocation arithmetic and preserves the allocator-free
short buffer. The legacy function implementation uses one size, alignment,
and copy predicate for inline construction, cloning, and destruction. Its
storage layout and virtual interface stay unchanged. GCC diagnostics remain
enabled. Focused regressions do not establish a complete runtime build.

## Acceptance

Run the installed package in the selected EmberBSD target. Check HTTPS navigation, tabs,
Russian text input, file download, ad blocking, persistent profiles, private
profile cleanup, site permissions, sandbox behavior, and package lifecycle.
Check touch input, media codecs, and hardware acceleration separately. Record
target identity, kernel revision, package hashes, and test results.

Blanc is MIT licensed. Its filter lists are CC BY-SA 3.0+, and its name and
logos are trademarks. Resolve redistribution terms before publishing Blanc or
its filter lists.

Owner: Ports (recipe) and OS (kernel/libc gaps).
Task: E12 in the private debt registry.
