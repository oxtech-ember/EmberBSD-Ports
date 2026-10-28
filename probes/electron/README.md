# Electron runtime probe for NetBSD (E12 Blanc browser)

Goal: run Blanc v1.25.0 on EmberBSD. Blanc uses Electron and has no
engine abstraction, so this port needs the native Electron runtime.

## Source pins

| Component | Pin | Source |
|---|---|---|
| Electron | 44.9.3 (`c542df1ecbc2c2978e8f53f8c7baf602404d166f`) | GitHub tag `v44.9.3` |
| Chromium | 152.0.7977.167 (`dd78960ccd8a03a2fe1f629543d27783885b78e9`) | Electron `DEPS` |
| Embedded Node.js | 24.22.1 | Patched Electron `DEPS` |
| Chromium host Node.js | 24.22.1 | Common Node24 provider |
| Blanc | 1.25.0 (`ff55d5948f5c71e802ba2ac464659ef96e055ca9`) | GitHub tag `v1.25.0` |

Electron's `DEPS` graph is the Chromium source of record. Do not substitute the
pkgsrc `.82` archive. Chromium sources require `gclient`; the older archive does
not match Electron's pinned revision.

| Distfile | Size | SHA256 |
|---|---:|---|
| `v44.9.3.tar.gz` | 20,838,185 | `e4e84b70a501c7dffec78bf037309bfe336daee6886289f94f9ac035ec54d80f` |
| `node-v24.22.1.tar.xz` | 57,669,336 | `4f5379796280cdaeb0c2f358fd04b6a16cc4fb7dfa83b5a8c91a9d963b435231` |
| `v1.25.0.tar.gz` | 155,108,408 | `b241d6b135b0fab5839f5dea6f64fafbdefa4f213b46ffa4a2f78820cb880971` |

The recipe backports the twelve source and build changes from Electron
[PR 55162](https://github.com/electron/electron/pull/55162), commit
`7b338a67ff07a12a60fe40059d2e67a39dbb4b3a`. It selects Node.js 24.22.1 and
keeps the Chromium pin. All 64 Node patches apply with full context to Node
commit `ce7aaf1cee78b8cf0ce17364260535c418d3ed26`.

The backport omits the upstream change that disables
`parallel/test-crypto-random-cache-snapshot`. That test uses the standalone Node
snapshot CLI. Electron creates its embedded Node environment through a different
path. Retain the test and the cache-reset fix. Entropy separation across Electron
snapshot restores still requires a runtime check.

Node's GN build selects Chromium's Brotli targets and bundled c-ares 1.34.9.
Chromium's Brotli source pin `cfa184a997ac19454d5a3ae97f6d600aac2445a6`
contains upstream fix `0ed4268a4401abcb4472096340477cf4af7d1a2b`. The two
affected files equal the fixed Node 24.22.1 files. Source checks do not establish
runtime security acceptance. Verify the actual target dependencies during GN
and build acceptance.

## Target contract

- Build on the developer host. Cross-compile all target objects for
  `aarch64--netbsd` or `x86_64--netbsd` with the shared Clang/LLVM toolchain
  and a matching EmberBSD sysroot and runtime. GN names these CPUs `arm64`
  and `x64`. GCC is an explicit platform alternative, never a retry fallback.
- Select host and target tools independently through the SDK.
  Native C/C++ generators use the selected native prefix. Target objects use
  the target compiler, sysroot and runtime. Do not select a host compiler
  through target `CC`/`CXX` or ambient PATH. A family change does not establish
  C++ ABI, builtins or unwinder compatibility.
- Enable Linux-conditioned Chromium source dependencies only to fetch their
  shared code. Do not use a Linux sysroot or Linux target objects.
- Adapt the `chromium-nb` and Electron patch sets to the exact Chromium pin.
  Record the overlay revision and every required drift fix.
- Keep Electron's Chromium sandbox enabled. Do not replace Chromium or Electron
  with another browser engine.

## Current status

- Electron and Node distfiles are pinned to the current supported Electron 44.x
  release and its exact Chromium revision.
- The pkgsrc Chromium baseline is 152.0.7977.82 with `chromium-nb` 151.1.
  The [ordered BSD overlay audit](electron44/bsd-overlay.md) uses the complete
  acquired Git graph after Electron's upstream patches. Five recipe-owned
  adaptations allow 1,632 patches to apply sequentially with zero fuzz in a
  separate source fixture. One dialog patch is superseded by Electron's
  disabled dialog code; eight patches belong to separate GN/Rollup host tools.
  Those host inputs and target build correctness remain unverified.
- Focused production GN checks retain explicit target ELF tools and target
  pkgsrc metadata. Earlier GCC checks do not qualify the new Clang runtime.
  Complete Clang compilation, linking and target execution remain unverified.
- No complete Chromium link, Electron runtime package, Blanc package, or target
  application acceptance run exists yet. Do not treat partial object builds as
  completion.
- Full runtime and application package lifecycle checks remain pending.
- The Blanc application recipe creates an ASAR from an explicit source
  allowlist and 32 lockfile-pinned runtime packages. Eight separate packages
  provide the upstream ASAR build tool. The host controller uses CPython 3.15
  and SDK API 1. Host Node.js 24.22.1 runs required upstream JavaScript tools.
  This application archive does not contain an Electron executable.
- The Blanc source patches select an explicit NetBSD capture descriptor. It
  uses the existing generic Electron/DOM/WebRTC broker, preload and helper.
  All nine runtime and fourteen shared permission hashes remain unchanged.
  A causal host Node24 test fails with `Unsupported capture platform` before
  the change; the patched source passes all 76 focused capture tests. This
  verifies source dispatch and locks. It does not verify native Electron
  startup or NetBSD media capture. Changes to these generic files require
  impact review for Windows and NetBSD.

## Electron source preparation

The recipe-owned [source preparer](electron44/source-preparation.md) verifies a
clean pinned Electron checkout, applies its complete recipe-local patch series
in order and creates an unmanaged `.gclient` with immutable Chromium and Node
pins. Its companion uses the pinned upstream gclient to acquire the Git-only
graph and retain selected CIPD/GCS declarations and LFS object inputs as pending.
A further recipe stage checks every selected patch repository before invoking
Electron's upstream patch CLI. No hooks run. The remaining assets, BSD overlay
and GN integration are necessary before building. The next source stage uses
[one ordered series](electron44/files/source-series.json) for the BSD layer and
all subsequent Ports patches; see the source preparation contract.

## Electron runtime packaging

The [runtime staging contract](electron44/runtime-packaging.md) describes the
existing SDK build entrypoints, the remaining ordinary recipe bindings, and the
bounded ZIP staging helper. The helper does not accept a source build or an
external binary distribution. Keep this recipe in the probe until its own
GN/Ninja build and package lifecycle are checked.

## Blanc application package

`scripts/prepare-pkgsrc.py` does not export this probe. Copy the two recipes
into a new export:

```sh
# Provide a verified source-data export at /absolute/NEW_PKGSRC. See the root README.
cp -RL probes/electron/blanc /absolute/NEW_PKGSRC/www/blanc
cp -RL probes/electron/electron44 /absolute/NEW_PKGSRC/devel/electron44
```

When the recipes are complete, move them to `pkgsrc/www/blanc` and
`pkgsrc/devel/electron44`. Then the normal export includes them. Select the
common Clang cross configuration and matching target runtime, or an explicit
GCC platform profile. Fetch and checksum need no selected Node, Python or SDK
source. Extraction requires `EMBERBSD_CROSS_BUILD_PYTHON` set to the selected
host CPython 3.15 executable and `EMBERBSD_SDK_SOURCE` set to an absolute SDK
API 1 source directory. Build and test additionally require `EMBERBSD_HOST_NODE`
set to the absolute host Node.js 24.22.1 executable and `EMBERBSD_HOST_PREFIX`
set to the installed native Ports prefix. The shared SDK `load_host_prefix`
selects Node and Python without requiring a compiler, checks native CPU,
symlink containment and script interpreters, and supplies the prefix-only child
PATH. The explicit Node path and the running Python must match that selection.
Source extraction does not require a native prefix. The standard pkgsrc phase
hooks validate these inputs; direct `do-extract`, `do-build` and `do-test` calls
retain the same checks. The controller checks the SDK API, module origin and
interpreter versions.

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

`tests/blanc-source-phases.py --help` describes the source-phase regression.
It uses a real pkgsrc export and explicit make tools/configuration, checks that
all 41 distfiles are exposed without build inputs, and verifies the consuming
phases reject missing tools. With `--distdir` it runs normal cached `fetch` and
`checksum`, including negative license and corrupted-input cases. The optional
`--baseline-recipe` reproduces the previous global metadata failure. These
checks do not build an ASAR or qualify the target runtime.
The package-controller suite also uses the real SDK loader to reject missing
or escaped tools, foreign CPU images and external script interpreters. Its
selection fixtures use native Python binaries as Node stand-ins; they do not
claim JavaScript execution. A real child process checks that the selected PATH
cannot discover a system shell. Run these controls with the prepared source
and cached archives:

```sh
"$HOST_PREFIX/bin/python3.15" -B -I -S \
  probes/electron/blanc/files/test_blanc_package.py \
  --sdk-source "$SDK_SOURCE" --source "$BLANC_SOURCE" \
  --distdir "$DISTDIR/e12-electron"
```

The host checks passed 11 package-controller tests and 22 focused Node tests.
The produced ASAR contains 1,674 entries. The production-only registry audit
reported no advisories for the 32 installed runtime packages. This does not
clear the separate upstream development dependency audit. Direct pkgsrc
extraction, patch, build, test, and staged install passed. The ASAR and SBOM
match the independent allowlist build byte-for-byte. The full pkgsrc dependency
lifecycle, target startup, and kernel sandbox acceptance remain unverified.
The application package cannot be installed until the target runtime is built.

## GN and C++ target inputs

The GN and parser patches retain the exact Chromium pin above. Their only full
application order is [source-series.json](electron44/files/source-series.json),
consumed by `prepare-build-sources.py` after Electron's upstream series. Use the
[source preparation contract](electron44/source-preparation.md#ordered-build-sources)
instead of applying individual patches to a prepared production tree. The
individual patch descriptions below explain isolated regression coverage;
they do not define a second preparation sequence.


Set `dawn_host_go_path` to the absolute path of a supported host Go executable
that satisfies Dawn's `go.mod`. Both toolchains forward this value to the same
source generator. Without an explicit path, the wrapper retains the upstream
DEPS-selected CIPD package. BSD hosts need an explicit native Go path; the
inherited CIPD platform mapping does not establish native BSD Go execution.
The patch replaces the unresolved pkgsrc `@GOBIN@` token in direct GN builds.
It keeps module mode, disabled CGO, output paths, and generator exit status.
The carried [source tests](tests/dawn-host-go.md) distinguish host selection
from target compilation.

Set `use_system_libffi=true` for the common NetBSD target profile. Its libffi
package provides the shared `-lffi` contract and does not provide `libffi_pic.a`.
The pinned GN configuration selects `-lffi_pic` by default on NetBSD. The explicit
system setting selects target pkg-config metadata and `-lffi` instead. A bounded
fixture checks both NetBSD settings and the unchanged Linux default. This profile
selection does not establish the complete SwiftShader or Electron link.

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
The resource-version patch preserves upstream Clang metadata for unchanged
upstream toolchains. The explicit native GCC16 family uses its accepted C/C++
drivers and GNU runtime. It does not use Clang's resource directory as a GCC
sysroot. The target C/C++ compiler remains GCC16.
The NASM patch restricts the `/usr/include/string.h` probe to Linux host builds. macOS provides this header through its selected SDK. Linux host detection and target GCC16 compilation stay unchanged.
The FFmpeg patch uses the configured cross prefix and requested target OS for x64 when `EMBER_FFMPEG_CROSS_PREFIX` is set. This prevents the host-arm64 path from passing Linux Clang `--target` flags to the NetBSD GCC toolchain. The default Linux build path stays unchanged.
The FFmpeg config-copy patch adds NetBSD to the generated configuration export list. It keeps the existing per-architecture and per-branding copy behavior.
The Base64 patch keeps invalid enum values fatal and gives GCC an explicit return
after the exhaustive switch. The ASan patch keeps intentional overflow and
underflow reads visible to runtime sanitizers while routing them through a
noinline address reader. This prevents GCC from rejecting the diagnostic test.
The GSL patch enables Clang-only lifetime annotations only on Clang. The Value
alias names its enclosing namespace explicitly for GCC. The FeatureState patch
keeps invalid values fatal and gives GCC an explicit constexpr return path.
The enum patch makes invalid enum values fatal after exhaustive switches.
The POSIX pragma patch selects Clang availability pragmas only on Clang.
The mkdir patch uses a boolean fallback for its boolean condition.
The Glib patch preserves controller lifetime checks during nested dispatch.
The placeholder patch constructs offsets in place and preserves stable ordering.
The WriteInto test patch preserves bounded copying and zero padding without
intentional `strncpy` truncation. It keeps all size and content assertions.
The network enum patch preserves fatal invalid-value paths in DNS, ipcz, and
WebRTC. The identifier patch uses one inline class-name entity across translation
units. It retains nested declarations, constexpr values, and PassKey access.
The Net/UI and HTTP follow-ups add fatal exits after exhaustive switches. They
retain parsing fallbacks, cookie policy, priority sentinels, and valid results.
The graphics enum patch preserves format, paint, shadow, and color-space
selection. Invalid terminal paths use the existing fatal mechanism.
The X509 patch removes a trailing dot with the shrink-only `pop_back()` operation.
Its hostname matching rules remain unchanged.
The Mojo validator patch uses an explicit boolean static-assert predicate.
It preserves compile-time rejection of null enum validators.
The Net/Mojo check patch enforces existing pointer prerequisites in release
builds. It keeps empty and non-associated-handle message paths valid. SPDY
checks stay inside their existing conditions; the cache loop reads pointers
by reference.
The Net devirtualization patch limits GCC16 PR122197 diagnostic scopes to two
derived destructors and one boolean load on proven impossible speculative paths.
Virtual ownership and production compiler flags stay unchanged. Real bounds
errors outside those locations remain fatal. Retire the scopes after a compiler
repair passes the two production inputs and their bounds controls.
The Net enum-exit follow-up preserves socket states, protocol names, dictionary
decoding, session policies, and closed-protobuf presence checks. Its 30 fatal
terminals apply only after the existing exhaustive switches.
The accessibility/display patch preserves XOR check grouping, reads attribute
entries by reference, and makes invalid accessibility enum exits fatal.
The D-Bus map patch builds its element signature with the constexpr array
length. It removes the array marker and final NUL without an implicit suffix
`strlen`. Map iteration, dictionary entries, and wire signatures stay unchanged.
The NetBSD keycode patch selects the existing evdev conversion API on NetBSD.
It keeps the native XKB table, offset, bounds, and media-key normalization.
Use the common `input-headers` package for the Linux input protocol constants.
For Mac→NetBSD Electron/ANGLE, also stage Mesa 26.2.5 public GL API headers
(`gl.h`, `glx.h`, `glxext.h`, `glext.h`, plus `KHR/khrplatform.h`) from
`pkgsrc/graphics/MesaLib`'s distfile into the clang-final sysroot at
`usr/pkg/include/GL/` (and `usr/pkg/include/KHR/`). Keep the existing X11
protocol headers (`glxint.h`, `glxmd.h`, `glxproto.h`, `glxtokens.h`). ANGLE
`SystemInfo_x11.cpp` stubs `CollectMesaCardInfo` on NetBSD so a host XQuartz
`__has_include(<GL/glx.h>)` cannot force a sysroot-missing include.
FFmpeg NetBSD configs are copied from Linux at configure/build time; `ensure_ffmpeg_netbsd_config` then clears `HAVE_GETAUXVAL` because NetBSD has neither `getauxval(3)` nor `<sys/auxv.h>` (x86 CPU flags still use CPUID).
Gemmlowp's `GlobalMutexes` function-local static `Mutex` needs `-Wno-exit-time-destructors` (or a clang diagnostic ignore) because `tflite_kernels` stays on `chromium_code`.
The [runtime fixture](tests/keycode-runtime.cc) checks the actual converter.
The Wayland patch adds fatal exits after exhaustive internal enum switches.
It keeps valid protocol mappings and unknown-wire rejection. It also declares
the complete display-delegate type and the shared header's public dependency.
See the [Wayland checks](tests/wayland-gcc16.md) for the scope and limits.
The TFLite arithmetic patch makes existing comparison grouping and product
conversions explicit. It preserves arithmetic operations and supported types.
See the [TFLite checks](tests/tflite-gcc16.md) for the verification scope.
The GBM patch uses an ELF weak reference for the optional per-plane fd function.
It keeps the function-presence check and existing DRM fallback. Its buffer-usage
switch gains a fatal terminal. See the [GBM checks](tests/gbm-gcc16.md).
The network policy/traits patch makes exhaustive enum exits explicit and
rejects unknown device-session union tags without changing the output. Closed
DNS enum validation remains before native conversion. See the
[network policy checks](tests/network-policy-traits-gcc16.md).
The event/Lottie patch makes internal enum exits fatal and inserts a copied
local handler value through emplace. It preserves handler priorities and
animation progress. See the [event checks](tests/ui-event-lottie-gcc16.md).
The ANGLE AST patch gives checked allocation its explicit size type, inserts
a local pointer through emplace, and checks unary diagnostic descriptors. A
GCC16-only scope covers the proven saved-stack false positive. See the
[ANGLE AST checks](tests/angle-ast-gcc16.md).
The Blink declaration patch uses injected constructor names and qualifies the
vector construction-traits alias. It preserves the constructor bodies and
allocator behavior. See the [Blink declaration checks](tests/blink-string-vector-declarations-gcc16.md).
The SVDF patch passes null for unused integer GEMM scratch in its existing
null-context call. It preserves the floating result buffer and restrict
contract. The [TFLite checks](tests/tflite-gcc16.md) include real numerical
and UBSan execution on NetBSD AMD64.
The IME/network follow-up adds explicit terminals to eight exhaustive-switch
consumers. It preserves closed TextInputMode validation and the existing
32-bit allocation branch. See the [end-path checks](tests/ime-network-endpaths-gcc16.md).
The scenario patch keeps the shared-memory padding diagnostic fatal on
both Clang and GCC. The QUICHE patch checks allocation and handshake invariants,
compares the selected subprotocol without signed conversion errors, and obtains
Settings frames through the existing typed visitor. The Dawn template selects
Clang-only CFI exclusions only on Clang. Generic sanitizer annotations remain
available to other supported compilers.
The Dawn type and dispatch patches preserve Result alignment checks and the
full-width flag conversions. See the [GCC16 checks](tests/dawn-gcc16.md) for
production regressions, negative controls and analysis limits.
The PFFFT patch limits assert-only SIMD validation to assertion-enabled builds.
It retains the public validation symbol and every debug assertion.
The Opus patch retains stack allocation and selects its existing `stdlib.h`
fallback on BSD systems. Other platforms retain their header selection.
The WebRTC media follow-up adds fatal exits after exhaustive codec, transport,
audio, sampling, and task-priority switches. It keeps Clang deprecation pragmas
Clang-only. Both public headers export the checks library through GN.
The parser patch removes three GCC-only diagnostic switches and `--param=`
optimizer settings only from libclang's inputs. Target compiler arguments,
`-Werror`, target triple, and sysroot remain unchanged.
The locale patch restores exclusive font conditions for Mac host resource builds.
It keeps the existing Linux/BSD font selection. See the
[production GRIT gather checks](tests/grit-locale-platforms.md).
The host-Node input patch selects executables by `host_os` for generic Node
and TypeScript protoc actions. It retains Linux Node for remote workers.
The qualified-host patch adds an explicit local `EMBERBSD_HOST_NODE` path.
Obtain it from the accepted SDK `node` role. Keep the same controlled environment
for GN generation and every dependent action. An explicit path must name an
absolute executable file. An empty, relative, missing or nonexecutable selection
fails. No PATH lookup or bundled fallback follows an explicit failure.
The selected local route refuses remote execution and declares only the selected
Node executable in both generic and TypeScript runtime inputs.

The patch restores the production exact version check removed by pkgsrc's
`www/chromium/patches/patch-third__party_node_check__version.py` (revision1.23).
An explicit selection uses the source-owned common Node24.22.1 version input.
The unchanged JavaScript equality check runs before its success marker is written.
The unset selector keeps the upstream executable and Node24.12.0 version input.
This path check does not qualify a provider. Native SDK and JavaScript action
acceptance remain required. Run the pure source controls without Node or GN:

```sh
python3.15 probes/electron/tests/qualified-host-node.py \
  --source /absolute/patched/Chromium -v
```

The existing host-input integration test still checks the unset upstream route.
Actual GN input graphs and JavaScript/TypeScript actions for an explicit qualified
provider must also pass before an Electron build.
The Electron main patch checks NetBSD before the Linux platform alias.
It selects the upstream POSIX main and stdio helper for NetBSD. Its glibc
environment shim stays in the unchanged Linux branch.
The BSD helper patch follows the existing `compile_suid_client` boundary.
It omits the Linux namespace/SUID executable and its distribution-only strip
target on BSD. The root aggregate also omits that unsupported helper.
Its other network and sandbox test dependencies remain. Generic ELF stripping
and the existing NetBSD policy remain.
No runtime sandbox flag changes. The current NetBSD policy does not establish
file, process, or network isolation; that OS acceptance gate remains open.
The distribution patch uses the explicit target OS argument for archive
selection. BSD archives prefer stripped ELF companions under canonical names.
Native Linux, macOS bundle, and Windows archive behavior remain unchanged.
The Mac patch keeps ordinary DWARF in host objects during cross-builds. Target
GCC16 still emits split DWARF. Native Mac toolchain arguments stay unchanged.
The PartitionAlloc patch matches NetBSD's const-qualified `malloc_usable_size`
declaration. It also uses a width-checked unsigned shift for the existing slot
metadata invariant. It keeps other libc signatures and allocator policy.

The reader, wire and media follow-ups preserve closed-enum validation and
array-query sizes. The [GCC16 checks](tests/gcc16-reader-wire-media.md) describe
production compiler results, target fixtures and analyzer limits.

The context, vector and enum follow-ups preserve null initialization, saved
block fields, URL adjustment order and unknown Perfetto wire values. The
[focused checks](tests/gcc16-context-vector-enums.md) describe production
GCC16 comparisons, staged shared-image checks, the 18-case target enum
fixture and analyzer limits. WebRTC checks retain NAL validation and copy
behavior. Complete Electron and Blanc acceptance remain pending.

The [optional link launcher](tests/linker-launcher.md) coordinates native links
across participating builds. It covers target and Mac host C/C++ and final
Rust links. Empty settings preserve existing commands. The reusable rule
checker verifies captured production commands before the production build starts.

## Native and target compiler selection

The unbundled target uses Chromium's existing `is_clang` argument. Set it to
`true` for the ordinary Clang SDK, or `false` for an explicit GCC platform.
The `:host` unbundle toolchain separately defaults `unbundle_host_is_clang`
to `true`. Set it to `false` only when selecting a native GCC prefix.
The [family patch](patches/gn-unbundle-compiler-family.patch) prevents a GCC
target from silently switching native tools into GCC mode. It does not detect
the compiler family from an executable name or replace missing tools.

Supply target commands through `CC`, `CXX`, `AR`, `NM`, `READELF` and their
flag variables. The unbundled host uses the independent `BUILD_*` commands
and flags. Select these commands through the SDK before generating GN files.
For a macOS host, retain the existing Apple Clang toolchain labels and select
`clang_base_path` from the native prefix. The explicit macOS GCC families below
are alternatives. Neither path may substitute Xcode or ambient build tools.
The Mac ABI SDK, deployment flags and required Apple tools remain explicit
native inputs. Target libraries must come from the EmberBSD sysroot.

Run the [family selection check](tests/gn-unbundle-compiler-family.py) with
`--source` and an explicit `--gn`. Six GN cases exercise both target modes,
the independent host default and both explicit host modes. With
`--baseline-source`, two negative cases demonstrate the inherited-mode defect.
Compiler paths, linker drivers, CPU/OS and assembler flags must stay separate.
After the carried link-launcher patch, add `--check-linker-launcher` for four
more GN cases: empty and selected target launchers under both compiler families.
The independent host toolchain must not inherit the target launcher.
These small GN fixtures run no compiler, Ninja or complete Chromium graph.
The ordinary Electron recipe still needs the full dependency sync, BSD overlay
integration and GN bindings; its initial DEPS input preparation is available.

## Native Wayland scanner selection

The [scanner patch](patches/gn-wayland-scanner.patch) adds the GN argument
`wayland_scanner_executable`. Select the native Ports prefix through the SDK
and set this argument to its absolute `bin/wayland-scanner` path. The common
[Wayland provider](../../profiles/common-graphics/cross/wayland.md) and its
[cross selector](../../pkgsrc/devel/wayland/cross-scanner.mk) own native tool
validation. GN checks the absolute-path contract and keeps the executable as
an action input, so replacing it triggers protocol regeneration. This selects
only the host generator; target Wayland libraries retain their own selection.

When the argument is nonempty, protocol actions omit the bundled scanner
build dependency and execute the supplied tool. Missing or nonexecutable tools
fail without fallback. The default empty argument preserves Chromium's host
scanner target and command. Existing generator types and wrapper behavior stay
unchanged.

The [GN/Ninja regression](tests/gn-wayland-scanner.py) reads the three exact
pinned Wayland files from an acquired Chromium Git checkout and verifies that
the prepared leaf still matches them. It applies the public patch in a separate
fixture, runs all four generation modes with the real native scanner and checks
executable-input rebuilds, default dependency routing and refusal cases. Its
default producer copies the native binary to the expected bundled output path;
it does not compile the bundled scanner. No production sources or installed
tools are modified. This checks protocol generation, not the full Chromium
graph, C/C++ compilation, target ABI or Electron runtime.

## Explicit Darwin SDK metadata

The [Darwin metadata patch](patches/gn-darwin-sdk-metadata.patch) keeps
`//build/toolchain/mac:clang_arm64` available for native host generators while
an independent target toolchain builds EmberBSD. Select `emberbsd_sdk_source`,
`emberbsd_xcode_version_plist`, `emberbsd_mac_toolchain_bin` and `mac_sdk_path`
together. The first input must provide the common SDK Python API 1 and
[`DARWIN_SDK_API = 1`](https://github.com/oxtech-ember/EmberBSD-SDK/blob/main/src/emberbsd_sdk/darwin_sdk.py).
The native bin directory comes from the recipe's selected host prefix; the
macOS SDK supplies ABI headers/libraries and metadata, not compiler tools.

The adapter reads the three explicit plists through the shared SDK reader,
compares the required SDK minimum numerically and formats Chromium's DTXcode
fields. It never runs `xcrun`, `xcodebuild`, `xcode-select` or `sw_vers`. Missing
or partial explicit selections fail. With all three EmberBSD arguments empty,
the original upstream discovery behavior remains. The three plist paths are
GN inputs, so metadata changes trigger Ninja's GN regeneration.

The [actual GN/Ninja test](tests/gn-darwin-sdk-metadata.py) applies the patch to
the exact pinned `mac_sdk.gni`, checks actual SDK values, empty-PATH and
process-audit controls, incompatible SDK API, partial arguments, numeric version
ordering and plist regeneration. Imports unrelated to this metadata leaf are
small fixtures; the test does not compile host or target code, generate the
complete Electron graph or establish runtime compatibility. The ordinary
recipe controller must supply these inputs when it selects its native toolchain.

## Explicit native macOS GCC host alternative

The [native GCC16 patch](patches/gn-mac-gcc16-host.patch) follows the link-launcher
patch in the source series. It is pinned to Chromium source
`88173c9141d8c62936a1796b58d3fe3b9e60a1ab`. The source checks accept the exact
three files before or after this patch. They do not execute GN or a compiler.

Run `tests/gn-mac-gcc16-scope.py --source /absolute/chromium/src
--gn /absolute/native/gn` for the compiler-selection regression. It evaluates
both production templates with a real GN binary. The 14 cases preserve explicit
false, explicit true, and the default true under both inherited compiler modes.
A missing `toolchain_args` scope must fail. The private local scope also supplies
`forward_variables_from`; it does not become a toolchain argument. The fixture
defines no compiler rules and does not run Ninja. Add `--baseline-source` with
the pre-repair tree to confirm both original parser failures. This adds two
negative cases. It does not validate the full Chromium graph.

The Mac runtime configuration retains Clang's `-mmacos-version-min` spelling.
The GCC route uses `-mmacosx-version-min` in the same argument position.
Both routes use the selected `mac_deployment_target` value.

Supply `mac_gcc_cc` and `mac_gcc_cxx` from the raw executable paths in the
accepted native SDK command tuples. Supply each ordered tuple tail through
`mac_gcc_cc_args` and `mac_gcc_cxx_args`. Set `mac_gcc_llvm_bin_path` from the
same accepted auxiliary-tool records. A directory name does not qualify its
contents. Do not put shell command strings in the executable arguments.
The patch rejects one-sided bindings and arguments without executable paths.
For a macOS ARM64 host and a NetBSD x64 target, select both families:

```gn
host_toolchain = "//build/toolchain/mac:gcc_arm64"
v8_snapshot_toolchain = "//build/toolchain/mac:gcc_arm64_v8_x64"
use_v8_context_snapshot = false
```

Both compilers emit native ARM64 Mach-O objects. The snapshot family sets
`v8_current_cpu="x64"` for V8 code generation. It does not require an x64
Darwin compiler. Keep the independent NetBSD target toolchain, target sysroot,
ABI flags and target custom libc++ selection. The two new native families
set both custom libc++ flags to false and use the accepted G++ runtime defaults.
Keep the Mac SDK root and deployment value consistent with the native ABI
selection. Do not pass the NetBSD sysroot to the native family.

Both native families select the platform allocator. They set
`use_partition_alloc=false`, `use_allocator_shim=false`, and
`use_partition_alloc_as_malloc=false` in their toolchain arguments. The derived
Rust-host and system-allocator families inherit these settings. The independent
NetBSD target retains its allocator and security settings. V8's snapshot CPU,
startup-data generation, and snapshot layout flags stay unchanged.

This removes the host PartitionAlloc and Apple allocator-shim dependency. It
does not port other Mac Objective-C++ sources in Chromium base or crypto. Those
host generator dependencies still need source and build validation. Do not treat
these source checks as an Objective-C, ARC, or complete Electron acceptance run.

This Mac-to-NetBSD GCC configuration uses V8's ordinary external startup blob.
Keep `v8_use_external_startup_data=true`. `use_v8_context_snapshot=false` selects
the existing non-Blink-context path. It keeps V8's snapshot generation and x64
snapshot layout. The existing cross-OS Node startup and code-cache settings,
V8 sandbox settings, integrity fuse, and runtime checks stay unchanged.

Apply the [checksum-input patch](patches/electron-snapshot-checksum-input.patch)
from the Electron source root before this configuration. It generates the same
checksum header from `snapshot_blob.bin` when the context optimization is off.
The context-enabled input stays unchanged. This change does not add an
internal-startup-data Electron configuration. Use a fresh output directory; an
old checksum header is not an input for the new configuration.

```sh
cd /absolute/chromium/src/electron
# electron-snapshot-checksum-input.patch is included by source-series.json.
```

The [source checker](tests/electron-snapshot-checksum-input.py) verifies both
input/dependency pairs and the retained external-data/default-toolchain guards. Run it with the
selected Python and `--source /absolute/chromium/src/electron`. The probe recipe
still lacks a complete GN build interface. These instructions do not establish
generation, packaging, loading, or host-generator acceptance.

The [host PaX patch](patches/v8-host-paxctl.patch) keeps the NetBSD snapshot
permission step local to a NetBSD build host. Apply it from the V8 source root:

```sh
cd /absolute/chromium/src/v8
# v8-host-paxctl.patch is included by source-series.json.
```

The Mac host does not run NetBSD `paxctl` on its Mach-O snapshot generator.
For a NetBSD build host, set `v8_host_paxctl` to the absolute executable path
from the host prefix's `paxctl` role. Include `paxctl` in the existing
`load_host_prefix` call's `required_roles`. Obtain the path with
`selection.tool("paxctl")`. The path alone does not qualify its provider.
The setting has no default path or PATH lookup. The action declares that file as an input and keeps `+m` on the
selected `mksnapshot($v8_snapshot_toolchain)` output. The wrapper refuses an
empty or relative executable before it starts a child. It preserves the child
exit status. This selector does not qualify an executable.

The [PaX source checks](tests/v8-host-paxctl.py) use no native commands.
Run them with the selected Python and `--source /absolute/chromium/src/v8`.
Actual GN and NetBSD-host permission checks remain required. This change does
not repair other context/code-cache PaX actions or change target browser PaX
and sandbox policy. The current Mac cross configuration keeps the context
optimization off through the separate argument above.

The [Apple C++ split](patches/base-apple-cxx-platform.patch) moves existing
CoreFoundation string conversions, Mach/CoreFoundation time code, and the complete
`BaseBundleID` getter, setter, and shared override state into three C++ files.
It also moves the complete C++ `SysInfo` Apple implementation to a `.cc` file
and the exact Mach `YieldCurrentThread` and pthread `SetName` implementations
to separate C++ files. Thread name registration stays in the common implementation.
Public headers, lifted function bodies, branding defaults, platform branches,
and runtime behavior stay unchanged. NSString and NSDate bridges remain in the
mixed sources. The existing Apple GN branch registers the C++ sources and retains
the four remaining Objective-C++ files.

The [source checks](tests/base-apple-cxx-platform.py) accept the complete pinned
Chromium source before or after this patch. Run them with the selected Python
and `--source /absolute/chromium/src`. They use no GN, compiler, or native tool.
This split does not provide a complete host-only base target. Other required
Objective-C++ dependencies remain. GCC16 compile/link checks, static analysis,
and the applicable upstream runtime tests remain required. These source checks
do not establish host-generator, ARC, or Electron acceptance.

The Apple link driver receives one C++ executable and its separate ordered
arguments. Rust proc macros receive the same executable and ordered link
arguments. The existing link launcher, environment order and final-link pool
stay in place. Clang PCM modules and the Clang coverage wrapper are unsupported
under the explicit GCC family and must not be replaced by stubs.

After source checks, run finite GN generation cases for default and empty
bindings, both GCC families, missing bindings, and derived Rust and allocator
families. Then inspect the complete production graph and every selected
compiler, action and native-link route. Verify native C/C++ runtime behavior,
required generators and the x64 snapshot with the accepted SDK. Objective-C
and ARC capability must follow the actual selected graph. These source-only
checks do not qualify those capabilities or a complete Electron build.

GN and allocator checks are in the [GN regression guide](tests/README.md).
Focused C++ checks are documented in the [libc++](tests/libcxx-gcc16.md) and
[Perfetto](tests/perfetto-gcc16.md) regression guides. See the
[Chromium GCC16 checks](tests/chromium-gcc16.md) for base and allocator coverage.

Apply the carried libc++ fix from its separate source root after its exact
DEPS revision and Electron patches are present:

```sh
cd /absolute/chromium/src/third_party/libc++/src
# libcxx-gcc16-maxsize-function-sbo.patch is included by source-series.json.
# libcxx-gcc16-recursive-function.patch is included by source-series.json.
# libcxx-gcc16-recursive-clone.patch is included by source-series.json.
# libcxx-gcc16-pair-lazy-assign.patch is included by source-series.json.
# libcxx-gcc16-allocation-object-limit.patch is included by source-series.json.
```

The fix bounds string allocation arithmetic and preserves the allocator-free
short buffer. The legacy function implementation uses one size, alignment,
and copy predicate for inline construction, cloning, and destruction. Its
storage layout and virtual interface stay unchanged. GCC diagnostics remain
enabled. The recursive-function patch removes the GCC fallback `always_inline`
from `std::function::operator()`. The clone patch preserves hidden visibility
without forcing recursive `__clone()` inlining. Focused regressions do not
establish a complete runtime build.

The pair patch evaluates assignment constraints lazily. It avoids an unnecessary
trait check on an incomplete second element when the first is not assignable.
The allocation patch rejects byte counts above the implementation object-size
limit before multiplication and allocation.

Apply the Abseil and ipcz follow-ups from their separate DEPS source roots:

```sh
cd /absolute/chromium/src/third_party/abseil-cpp
# abseil-btree-node-kind-gcc16.patch is included by source-series.json.
cd /absolute/chromium/src/third_party/ipcz
# ipcz-checked-cast-gcc16.patch is included by source-series.json.
# ipcz-typed-release-gcc16.patch is included by source-series.json.
```

The B-tree split uses the leaf/internal choice already made by its caller.
Leaf splits do not instantiate child-pointer operations. The ipcz cast checks
both integer bounds with the existing hardening policy. Typed reference release
retains the concrete API object hierarchy and virtual destruction. Node layout,
reference-count storage, ordering, and the public handle ABI stay unchanged.
The carried upstream tests cover B-tree splitting, integer boundaries, and
mixed typed/untyped reference ownership. Test compilation does not establish
runtime execution.

Apply the ANGLE follow-up with `-p1` from the separate `third_party/angle`
DEPS source root:

```sh
cd /absolute/chromium/src/third_party/angle
# angle-scratch-move-gcc16.patch is included by source-series.json.
# angle-netbsd-pci-backend-selection.patch is included by source-series.json.
```

The ScratchBuffer move constructor initializes its empty destination before
swap-based assignment. Its carried tests cover data ownership, countdown
preservation, moved-from reuse, and an empty buffer with an eternal lifetime.
The PCI selection patch excludes the unused Linux libpci backend on NetBSD.
NetBSD retains its existing Mesa/GLX GPU information path and graphics backends.
See the [Chromium GCC16 checks](tests/chromium-gcc16.md) for validation limits.

The pinned Perfetto checkout has a separate GCC16 warning patch. Apply it from
the Chromium source root after the NetBSD adaptations:

```sh
cd /absolute/chromium/src/third_party/perfetto
# perfetto-gcc16-warning-cleanups.patch is included by source-series.json.
```

The bounded MurmurHash tail loop preserves little-endian hash semantics and
avoids out-of-range switch reads. Console formatting now caps the track title
at its 15-byte buffer limit and passes a non-null pointer for an absent
annotation name. Focused GCC16 production-translation-unit checks and golden
vectors cover these changes; they do not establish a complete runtime build.

The V8 patch keeps `TaggedPayload` trivially copyable and permits GCC's generic
atomic-load result storage, marks the Linux-oriented address-space label as
unused on targets without naming support, and makes the Karatsuba threshold
comparison unsigned. It also qualifies the `HeapGrowingMode` enum alias and
uses Clang's `nodebug` attribute only when the compiler supports it. Its
regression replays four production GCC16 compile commands before and after the
patch. It does not disable warnings or change the pointer-table layout.

Apply the V8-specific patch from the pinned V8 source root after the Chromium
NetBSD adaptations:

```sh
cd /absolute/chromium/src/v8
# v8-gcc16-netbsd.patch is included by source-series.json.
```

Use the [V8 GCC16 regression guide](tests/v8-gcc16-netbsd.md) to replay the
production target commands.

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

## Tiling and accessibility positions with GCC 16

[The tiling and AX patch](patches/cc-ax-position-gcc16.patch) preserves the
public tile alias and existing position cases. Its [verification scope](tests/cc-ax-position-gcc16.md)
records five passing production consumers, unchanged analyzer findings and
explicit Cppcheck parsing limits. The upstream AX unit object remains blocked
by four inherited parameterized GTest linkage errors; target execution is pending.

### Refresh a configured Node provider

`electron44/files/build-electron.py reconfigure` accepts the same inputs as
`configure` and regenerates the existing `--work` graph. It allows GN feature and compiler option changes while checking target and
toolchain identity. Compiler bindings are immutable and their content-addressed
paths change when their commands change, so Ninja rebuilds affected commands.
The prepared Node actions record the selected Node, TypeScript and Rollup paths
and versions in their command lines and use those selections. After a provider
update, reconfigure records the current versions; changing a path or version
makes Ninja rerun the affected actions. Each action rejects a version that has
changed since configuration. Existing objects remain for Ninja to update. A failed or interrupted
GN generation leaves `reconfigure-incomplete` and prevents `build`; rerun
`reconfigure` successfully before building. This operation does not establish
that changed compiler or sysroot contents at the same paths are compatible.
Use a new output when those inputs have changed incompatibly.

The Electron producer keeps its build `PATH` inside the selected native prefix.
Source metadata commands receive the explicitly selected `--git` as
`EMBERBSD_CONTROL_GIT`, without adding that control tool's directory to `PATH`.
The reconfigure command accepts the corresponding migration from the earlier
prefix-plus-Git-directory environment and rejects unrelated changes.

The producer expects the selected target Rust standard library to have already
been installed by the shared Ports package. It does not download or install a
private copy. On Darwin it binds Chromium's dsymutil path to the selected native
prefix and rejects an existing different tool. The presence check for Rust
libraries does not establish their provenance or target runtime compatibility.

Electron selects the common target `libdrm` with `use_system_libdrm`. Direct
Chromium references to `//third_party/libdrm` forward to the same target
pkg-config provider. The shared Ports recipe owns the implementation and NetBSD
PCI support; target link and GPU runtime acceptance remain separate checks.
