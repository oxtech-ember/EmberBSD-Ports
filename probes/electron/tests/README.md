# Electron cross-build regression tests

Run these commands from the Ports repository root.

The source-only [DEPS preparation regression](../electron44/source-preparation.md#regression-checks)
uses control Python and an explicit Git executable; no installed SDK is needed:

```sh
/absolute/control-python -B probes/electron/tests/electron-source-prepare.py \
  --git /absolute/git --electron-source /absolute/electron-pristine
/absolute/control-python -B probes/electron/tests/electron-git-sources.py \
  --git /absolute/source-tools/bin/git --git-lfs /absolute/source-tools/bin/git-lfs \
  --source-path /absolute/source-tools/bin \
  --depot-tools /absolute/depot-tools
/absolute/control-python -B probes/electron/tests/electron-upstream-patches.py \
  --git /absolute/source-tools/bin/git --git-lfs /absolute/source-tools/bin/git-lfs \
  --source-path /absolute/source-tools/bin --electron-source /absolute/electron-pristine
```

The ordered build-source regression uses the same explicit Git/patch inputs:

```sh
/absolute/control-python -B -I -S probes/electron/tests/electron-build-sources.py \
  --git /absolute/git --patch /absolute/gpatch
```

It executes real tiny Git repositories and patches, including all-before-write
refusals and idempotent materialization. The full pinned-source preparation is
specified by the recipe's `source-series.json`; individual tests below select
isolated leaf inputs and must not reapply patches to that prepared workspace.

Run the remaining build regressions with host CPython 3.15 and its standard
library. Integration
tests select an SDK API 1 source with `--sdk-source` and check its module origin.
Their commands, stable SHA256 hashes and JSON receipts use that SDK. Select the
host GN and pkgconf explicitly. The full integration test requires a sysroot
with real `gio-unix-2.0` and GTK3 metadata and their dependency closure. The
x64 selector test uses an empty synthetic sysroot and mock pkgconf. POSIX
`patch` must be available on `PATH`. Each `NEW_WORK` path must be new and
outside the selected source and any external sysroot.

```sh
python3.15 -B -I -S probes/electron/tests/gn-wayland-scanner.py \
  --source /absolute/acquired-chromium/src --git /absolute/source-git \
  --gn /absolute/native-prefix/bin/gn --ninja /absolute/native-prefix/bin/ninja \
  --scanner /absolute/native-prefix/bin/wayland-scanner \
  --protocol /absolute/native-prefix/share/wayland/wayland.xml \
  --utility-path /absolute/selected-native-utility-path \
  --work /absolute/NEW_SCANNER_WORK
python3.15 -E -S probes/electron/tests/gn-unbundle-compiler-family.py \
  --source /absolute/chromium/src --gn /absolute/host-gn \
  --baseline-source /absolute/chromium-before-family-patch
python3.15 -E -S probes/electron/tests/gn-pkgconfig.py \
  --sdk-source /absolute/EmberBSD-SDK \
  --source /absolute/chromium/src --sysroot /absolute/target-sysroot \
  --gn /absolute/host-gn --pkg-config /absolute/host-pkgconf \
  /absolute/NEW_PKGCONFIG_WORK
python3.15 -E -S probes/electron/tests/gn-netbsd-x64-pkgconfig.py \
  --sdk-source /absolute/EmberBSD-SDK \
  --source /absolute/chromium/src --gn /absolute/host-gn \
  --patch /absolute/Ports/probes/electron/patches/gn-netbsd-x64-targets.patch \
  /absolute/NEW_PKGCONFIG_X64_WORK
python3.15 -E -S probes/electron/tests/gn-readelf.py \
  --sdk-source /absolute/EmberBSD-SDK \
  --source /absolute/chromium/src --gn /absolute/host-gn \
  --readelf /absolute/target-readelf --rustc /absolute/host-rustc \
  /absolute/NEW_READELF_WORK
python3.15 -E -S probes/electron/tests/gn-rust-bindgen.py \
  --sdk-source /absolute/EmberBSD-SDK \
  --source /absolute/chromium/src --gn /absolute/host-gn \
  --bindgen /absolute/chromium/src/third_party/rust-toolchain/bin/bindgen \
  --rustfmt /absolute/chromium/src/third_party/rust-toolchain/bin/rustfmt \
  --sysroot /absolute/target-sysroot \
  --patch /absolute/Ports/probes/electron/patches/gn-rust-bindgen-host-tools.patch \
  --x64-patch /absolute/Ports/probes/electron/patches/gn-netbsd-x64-targets.patch \
  /absolute/NEW_BINDGEN_WORK
python3.15 -E -S probes/electron/tests/gn-clang-resource-version.py \
  --sdk-source /absolute/EmberBSD-SDK \
  --source /absolute/chromium/src --gn /absolute/host-gn \
  --patch /absolute/Ports/probes/electron/patches/gn-clang-resource-version.patch \
  /absolute/NEW_CLANG_RESOURCE_WORK
python3.15 -E -S probes/electron/tests/gn-bindgen-gcc-args.py \
  --sdk-source /absolute/EmberBSD-SDK --source /absolute/chromium/src \
  --out /absolute/EXISTING_NETBSD_GN_OUT \
  --patch /absolute/Ports/probes/electron/patches/gn-bindgen-gcc-warnings.patch \
  /absolute/NEW_BINDGEN_ARGS_WORK
python3.15 -E -S probes/electron/tests/gn-host-node-inputs.py \
  --sdk-source /absolute/EmberBSD-SDK --source /absolute/chromium/src \
  --gn /absolute/host-gn /absolute/NEW_HOST_NODE_WORK
python3.15 -E -S probes/electron/tests/electron-main-selection.py \
  --sdk-source /absolute/EmberBSD-SDK --ports-root /absolute/Ports \
  --chromium-source /absolute/chromium/src \
  --electron-source /absolute/chromium/src/electron \
  --patch /absolute/Ports/probes/electron/patches/electron-netbsd-main.patch \
  --gn /absolute/host-gn --work-dir /absolute/NEW_ELECTRON_MAIN_WORK
python3.15 -E -S probes/electron/tests/partition-alloc-netbsd-gcc16.py \
  --sdk-source /absolute/EmberBSD-SDK --ports-root /absolute/Ports \
  --source-root /absolute/chromium/src \
  --patch /absolute/Ports/probes/electron/patches/partition-alloc-netbsd-gcc16.patch \
  --cxx /absolute/GCC16-target-g++ --sysroot /absolute/target-sysroot \
  --workdir /absolute/NEW_PARTITION_ALLOC_WORK
```

The scanner regression requires the exact acquired pinned Wayland leaf before
its scanner patch; it obtains the pin from the recipe source preparer. It runs
real GN/Ninja protocol actions with a copy of the selected native scanner,
including a changed-executable rebuild. Its fixture toolchains cannot compile
or link. The full Chromium graph and target runtime remain untested.

The other GN tests accept the original or already fixed source. They apply the carried
patch in an isolated fixture and preserve source hashes and command receipts.
The pkg-config integration test uses real pkgconf queries to resolve target
gio/GTK paths; the existing cache case must make no pkgconf calls. The
NetBSD x64 pkg-config test uses the exact production GN template and script,
an empty synthetic sysroot, and a controlled mock pkgconf. It records sixteen
before/after GN snapshots. Baseline x64 GN succeeds with empty metadata; the
patch restores mock include and library flags for default and custom-wrapper
queries. ARM64 default/custom behavior and the GN arguments for native NetBSD,
Linux, and no-sysroot cases stay unchanged. Native-host execution is not part
of this fixture. It does not read a real target sysroot or claim installed GTK
metadata. The readelf test covers ten cases with production `gcc_toolchain.gni`
and generated `solink` and assembly commands. It preserves host and native
fallback and rejects a missing cross tool. A real `.S` graph input checks that
target and host assembler markers stay separate. Unset assembler commands
remain byte-identical. The selected host Rust compiler supplies only
its `-V` result for an unrelated production GN version probe.

The bindgen test covers twelve before/after GN metadata cases and four NetBSD
x64 cases. It also runs the pinned host bindgen and rustfmt on minimal C
headers with host, NetBSD ARM64, and NetBSD x64 parser arguments. It uses the
exact libclang directory below the pinned Rust toolchain. The smoke headers do
not include system headers or exercise the full allocator action. The x64
smoke does not validate sysroot headers. Neither smoke projects GCC-only
`--param` or `-B` flags. Its shared library check currently requires a macOS
host toolchain with `libclang.dylib`.

The resource-version test runs six minimal GN evaluations. The Apple host
selects the pinned compiler's resource version, the NetBSD target retains
version 23, and the forced head revision retains version 24. The test checks
the actual host compiler's `-print-resource-dir` result, a resource header,
and the Darwin compiler runtime archive. It does not compile target objects.

The GCC argument test replays the actual generated allocator bindgen action
before and after the parser patch. It requires the macOS ARM64 host graph
and NetBSD ARM64 unbundle target. The host argument projection stays unchanged.
An unmapped warning option and an intentional header warning still fail with
`-Werror`. The tested allocator header has no system header dependencies.

The host-Node test covers fifteen GN cases, including actual Mac/NetBSD and
simulated BSD/Linux/Windows selectors. It checks the bundled Mac Node against
Chromium's pin. Remoteexec uses a fixture config marker for GN planning only;
no remote action runs. Embedded Electron and ASAR host Node keep separate pins.

These tests pass on macOS. The fixture supplies the E12 macOS cross profile
explicitly; it does not depend on the machine that runs GN. Linux and native
NetBSD values are controlled GN fixture inputs. They do not establish
execution on those hosts. Header-free target smoke compilation does not
establish Electron linking, startup, package, or media acceptance.
The changes are AI-assisted EmberBSD patches and are not submitted upstream.

The [Rust standard-library link regression](gn-rust-netbsd-execinfo.md) checks
NetBSD execinfo propagation through the production GN library list. A real
GCC16 amd64 C++ link fails without that dependency and succeeds with it.
The bounded fixture also passes Cppcheck and analysis-only Clang checks.
Rust standard-library compilation and full Electron linking remain separate.

The Electron main selector test requires `--chromium-source`. It copies the
OS definitions from that checkout's `build/config/BUILDCONFIG.gn` and lets GN
evaluate the exact Electron selector. It does not evaluate GN expressions in
Python. Thirteen OS values run before and after the patch. Explicit expected
lists check Linux, Windows, and NetBSD. The platform definitions include the
BSD aliases and `winuwp`. FreeBSD, OpenBSD, Windows, and the separate macOS
branch retain their selected sources. The original NetBSD
selector and a former late NetBSD branch both select the glibc shim and must
fail the POSIX source-list requirement. Every GN command must succeed before
that rejection check. The corrected NetBSD selector keeps the POSIX main and
stdio helper without the glibc shim. These checks make 27 GN planning cases.
The test accepts the pinned baseline or the exact patched Electron source.
It checks zero-fuzz patch application and preserves source hashes and command
receipts. It does not compile those C++ files or establish runtime startup.

The earlier Mac debug-fission regression remains historical evidence for the
upstream Apple route. It used a pinned Mac Clang and an independent GCC16 target
probe. It does not qualify the explicit native GCC16 family. The native EmberBSD
profile does not run that Clang compile fixture.

The [native macOS GCC16 source test](gn-mac-gcc16-host.py) reads the complete
three pinned production GN files. It applies and reverses the carried patch in
memory. It checks ordered C/C++ words, the Apple link-driver executable and tail,
Rust linker arguments, native/snapshot CPU selection, target scope, and the
existing seven native final-link commands. Quoted compiler paths and arguments
include spaces, apostrophes and literal dollar signs. Causal controls reject an
unquoted compiler, a dropped link tail and a changed source hunk.

```sh
python3.15 -B probes/electron/tests/gn-mac-gcc16-host.py \
  --source /absolute/chromium/src
```

This test uses only Python's standard library and writes no source or output
files. Its string-expression model is not a GN evaluator. It does not run GN,
Ninja, a compiler, a linker, or a produced program. Complete the actual finite
GN/default/failure controls and production graph checks in the
[native toolchain instructions](../README.md#native-macos-gcc16-host-tools).

The PartitionAlloc runner maps the exact GCC target triplet to its ELF class,
byte order, relocatable-file type, and machine. Its `--target-map-self-test`
mode checks NetBSD/aarch64 and NetBSD/amd64 mappings and rejects unsupported
triplets without compiling. Run it with the selected host CPython and SDK:

```sh
python3.15 -B -I -S probes/electron/tests/partition-alloc-netbsd-gcc16.py \
  --sdk-source /absolute/SDK --target-map-self-test
```

The full PartitionAlloc regression checks seven outcomes with GCC16 for either
NetBSD/aarch64 or NetBSD/amd64, selected by the compiler's exact `-dumpmachine`
output. It maps `aarch64--netbsd` to ELF machine 183 and `x86_64--netbsd` to
ELF machine 62. Both require ELF64 little-endian relocatable objects. The
retained complete production-TU compile receipt covers AArch64. The seven
isolated regression outcomes pass with both GCC16 target compilers and their
matching sysroots; full amd64 allocator compilation remains unverified.
It copies two production files, proves forward/reverse patch application, and
extracts the exact metadata assertion into a small compile fixture. The original
assertion fails on signedness; the fixed assertion passes. An out-of-range shift
fails its intended assertion before a shift is evaluated. The real target malloc
header rejects the original shim and accepts the patched shim as the ELF object
selected for that target. Mocked non-NetBSD headers retain the original pointer
signature. These isolated probes do not compile the complete allocator or
execute its runtime.

Target analyzer coverage is partial. Cppcheck 2.18 stops at an unchanged
`time.h` AST error in both revisions. Apple Clang 21 analyzes the metadata TU
with the same three dead-store warnings, but rejects unchanged NetBSD libc
`__THROW`/`noexcept` declarations in the shim TU. These are analyzer limits;
they do not establish a clean analysis of the complete allocator.

The Rust-version test covers the production `build/config/rust.gni` default.
The supplemental `gn-rust-version-netbsd.patch` skips the default `rustc -V`
probe only for a cross build from a non-NetBSD host to NetBSD. A custom Rust
sysroot must provide `rustc_version`; the bundled Chromium Rust toolchain keeps
using its pinned `VERSION` file. Native NetBSD and unrelated targets retain the
existing host Rust fallback. Apply this patch after the NetBSD source adaptations
and before GN generation:

```sh
(cd /absolute/chromium/src && patch -p1 -F0 < /absolute/Ports/probes/electron/patches/gn-rust-version-netbsd.patch)
python3.15 -B -I -S probes/electron/tests/gn-rust-version-netbsd.py \
  --source /absolute/chromium/src --gn /absolute/host-gn \
  --patch /absolute/Ports/probes/electron/patches/gn-rust-version-netbsd.patch \
  --sdk-source /absolute/EmberBSD-SDK --ports-root /absolute/Ports \
  --sysroot /absolute/target-sysroot /absolute/NEW_RUST_VERSION_WORK
```

The runner accepts either the exact baseline or the exact patched `rust.gni`.
It proves that state with strict forward and reverse patch checks, then makes
both fixture variants from isolated copies. Six GN cases cover the original
missing-`./rustc` failure, an explicit cross version, a missing-version error,
the bundled toolchain, native NetBSD, and an unrelated Linux target. It verifies
that only the intended native/unrelated cases invoke `rustc -V`. The test does
not run a real Rust compiler, build Rust targets, or generate the complete
Chromium graph.


The V8 GCC16 test reads the pinned V8 revision from the Chromium checkout and
replays the generated Torque object and Karatsuba production compile commands.
Both baseline commands must fail on the captured GCC16 diagnostics; both
patched commands must succeed. It creates source overlays and writes objects,
depfiles, logs, and a receipt under a new work directory without changing V8,
the GN output, or the sysroot. The SDK lock is shared for the read-only GN and
sysroot inputs.

```sh
/absolute/EmberBSD/host-tools/python315/bin/python3.15 -B -I -S \
  probes/electron/tests/v8-gcc16-netbsd.py \
  --sdk-source /absolute/EmberBSD-SDK --ports-root /absolute/Ports \
  --source-root /absolute/chromium/src --gn-out /absolute/chromium/out/Default \
  --cxx /absolute/GCC16-target-g++ --sysroot /absolute/target-sysroot \
  --workspace /absolute/SDK-workspace --ninja /absolute/host-ninja \
  --patch /absolute/Ports/probes/electron/patches/v8-gcc16-netbsd.patch \
  /absolute/NEW_V8_WORK
```

The compiler command database must select NetBSD x64, GCC16, the matching
sysroot, and `-Werror`. This verifies the targeted source portability fixes;
it does not build or link V8 or Electron. See the [V8 regression guide](v8-gcc16-netbsd.md).

See the [libc++ GCC16 regression guide](libcxx-gcc16.md) and the [Perfetto GCC16 regression guide](perfetto-gcc16.md) for production C++ checks.

The Electron distribution test checks target-based archive policy with host
CPython 3.15, its standard library and an explicit SDK API 1 source. It accepts
the pinned original `build/zip.py` or the exact patched file. Reverse and
forward `patch -p1 -F0` checks recover the pinned baseline and patched bytes.
Use a new work directory outside the selected sources and test directory.

```sh
python3.15 -B -I -S probes/electron/tests/electron-dist-target-os.py \
  --sdk-source /absolute/EmberBSD-SDK \
  --electron-source /absolute/chromium/src/electron \
  --patch /absolute/Ports/probes/electron/patches/electron-dist-target-os.patch \
  --work-dir /absolute/NEW_ELECTRON_DIST_WORK
```

Fourteen cases execute the actual before/after writer. The original
Darwin-to-NetBSD case must fail the explicit ELF archive requirement. NetBSD
from simulated Darwin, Linux and Windows hosts uses stripped files and canonical
names. FreeBSD and OpenBSD retain that ELF policy. Native Linux, macOS, Windows
and flattened macOS results stay equal. SDK `run_logged` preserves command logs
and SHA256 receipts. Temporary archive fixtures are removed. The macOS external
`zip` command is captured, not executed. These synthetic payloads do not qualify
a release ZIP, ELF binaries, a runtime package, sandboxing or target startup.

## Linux SUID-helper selection

Use CPython 3.15, an SDK source that provides Python API 1, host GN, and the
pinned Chromium source with the Electron main-entrypoint patch applied.
The source can contain the Linux SUID-helper patch already.
Choose a new absolute work directory outside the source and SDK trees.

```sh
python3.15 -E -S probes/electron/tests/electron-linux-suid-selection.py \
  --sdk-source "$sdk" --chromium-source "$chromium" --gn "$gn" \
  --patch "$ports/probes/electron/patches/electron-bsd-linux-suid-helper.patch" \
  --work-dir "$work"
```

The test applies the patch with zero fuzz to copies of three pinned GN files.
It executes the production GN conditions and OS definitions for 13 platforms
with official builds enabled and disabled (52 successful matrix cases).
A separate successful GN case reconstructs the former two-file patch.
It must fail because the root `gn_all` group retains the Linux helper.
The complete regression makes 53 successful GN runs.
Independent expectations reject the baseline BSD helper selection and verify
the corrected root and Electron selections, unchanged non-BSD behavior, ELF strip targets,
and the existing NetBSD policy sources. The work directory retains hashes,
commands, JSON observations, and bounded fixture sources. It does not build
Electron or validate NetBSD OS isolation or installed sandbox behavior.

## Darwin host ABI metadata

```sh
python3.15 -B -I -S probes/electron/tests/gn-darwin-sdk-metadata.py \
  --source /absolute/chromium/src --sdk-source /absolute/EmberBSD-SDK \
  --macos-sdk /absolute/MacOSX.sdk \
  --xcode-version-plist /absolute/Xcode.app/Contents/version.plist \
  --native-bin /absolute/native/bin --git /absolute/control/git \
  --gn /absolute/native/bin/gn --ninja /absolute/native/bin/ninja \
  --work /absolute/NEW_DARWIN_METADATA_WORK
```

This reads the exact pinned Chromium leaf from the acquired Git source without
changing it. Real GN invokes the shared SDK reader; actual SDK values, explicit
selection refusals and GN regeneration after a plist change are checked. No
compiler or Apple discovery service runs. See the
[metadata contract](../README.md#explicit-darwin-sdk-metadata) for its scope.

## NetBSD resource allowlist

```sh
python3.15 -B -I -S probes/electron/tests/electron-resource-allowlist.py \
  --source /absolute/prepared/chromium/src --work /absolute/NEW_ALLOWLIST_WORK \
  --gn /absolute/native/bin/gn --git /absolute/control/git \
  --clang /absolute/native/bin/clang++ --ar /absolute/native/bin/llvm-ar \
  --utility-path /absolute/native/bin:/absolute/native/gnu/bin
```

Run this on the canonical source layer immediately before the resource-allowlist
patch. Eight actual GN cases preserve platform and debug/component restrictions.
Selected Clang produces a freestanding NetBSD ELF object with 101 resource
markers. The actual upstream pseudo-link collector and LLVM thin archive feed
the allowlist extractor; Electron's shipped-pak checker accepts the complete
pack and rejects a missing resource. No target program runs and no complete
Electron build is claimed.

## Selected target ELF strip tools

```sh
python3.15 -B -I -S probes/electron/tests/electron-elf-strip.py \
  --source /absolute/prepared/chromium/src --work /absolute/NEW_STRIP_WORK \
  --git /absolute/control/git --gn /absolute/native/bin/gn \
  --ninja /absolute/native/bin/ninja --clang /absolute/native/bin/clang \
  --ld /absolute/native/bin/ld.lld --strip /absolute/native/bin/llvm-strip \
  --objcopy /absolute/native/bin/llvm-objcopy \
  --readelf /absolute/native/bin/llvm-readelf \
  --utility-path /absolute/native/bin:/absolute/native/gnu/bin
```

Use the canonical source immediately before `gn-selected-elf-strip.patch`.
The baseline BSD Python no-op returns success without either promised output.
The restored upstream operation runs through actual GN/Ninja on a freestanding
NetBSD ELF file: separate debug sections and the stripped image's GNU debuglink
are checked. The explicit tool pair remains in Ninja inputs. Partial/relative
selection and corrupt ELF fail; unchanged default and non-NetBSD routing is
checked separately. This does not execute the target or accept an Electron
runtime.

The CUPS configuration check uses the actual prepared Chromium printing block,
its pkg-config GN template and Python helper, selected GN and selected pkg-config.
Explicit metadata-only fixtures verify the NetBSD target prefix, missing CUPS
metadata refusal, macOS/ChromeOS selections and the disabled-printing case. The
unpatched control executes a target `cups-config` script; the patched NetBSD
route never invokes it. This checks configuration only, without compiling a
CUPS library or establishing target ABI/runtime support.

```sh
/absolute/native-prefix/bin/python3.15 -B -I -S \
  probes/electron/tests/electron-cups.py \
  --source /absolute/prepared-electron/src --work /absolute/new-cups-check \
  --git /absolute/control-git --gn /absolute/native-prefix/bin/gn \
  --pkg-config /absolute/native-prefix/bin/pkg-config \
  --utility-path /absolute/native-prefix/bin:/absolute/native-prefix/gnu/bin
```

Run against the prepared source immediately before
`gn-netbsd-cups-pkgconfig.patch`. The common `print/libcups` recipe installs
`cups.pc`; production configuration requires that target package in the selected
EmberBSD sysroot and does not substitute the build host's CUPS metadata.

## Electron provider reconfiguration

```sh
/absolute/native/bin/python3.15 -B -S probes/electron/tests/electron-reconfigure.py \
  --host-prefix /absolute/native --sdk-source /absolute/EmberBSD-SDK
```

This runs real GN generation on a small graph and checks refusal of changed
compiler bindings, retained objects, a failed generation, build refusal, and
subsequent recovery. It does not build Electron or execute target code.

## Explicit control Git for metadata

```sh
/absolute/native/bin/python3.15 -B -S probes/electron/tests/electron-control-git.py \
  --source /absolute/prepared/chromium/src --git /absolute/git \
  --host-prefix /absolute/native
```

The test applies the patch to committed source copies and exercises real Git
metadata in an ordinary checkout and a worktree, the upstream fallback and
missing Git. It does not run a complete Electron build.

## Electron host and Rust inputs

```sh
/absolute/native/bin/python3.15 -B -S probes/electron/tests/electron-tool-selection.py \
  --host-prefix /absolute/native --sdk-source /absolute/EmberBSD-SDK
```

This checks missing target Rust files and, on Darwin, the selected native
`dsymutil` binding and rejection of an external existing tool. It does not
prove Rust package provenance, ABI compatibility, or target execution.

The DNS OpenBSD guard and scoped libsync diagnostics can be checked against a
prepared source layer and the real configured target compiler and GN flags:

```sh
/absolute/control-python -B -I -S probes/electron/tests/dns-libsync-source.py \
  --source /absolute/prepared-source/files --gn-out /absolute/electron-work/out \
  --cc /absolute/electron-work/target-commands/cc
```

The libsync negative control removes the six annotations in a temporary source
and requires six unused-function errors. This does not establish DNS runtime
behavior or target device acceptance.

## Immutable compiler binding invalidation

```sh
/absolute/native/bin/python3.15 -B -S probes/electron/tests/electron-binding-invalidation.py \
  --host-prefix /absolute/native --sdk-source /absolute/EmberBSD-SDK \
  --macos-sdk /absolute/MacOSX.sdk
```

This uses the real SDK binder, native Clang and Ninja to compile and link a
small native fixture, then checks a no-op and recompilation after changed
binding flags. It does not test the Electron target or target execution.

The allocator and bindgen source patches can be checked using the configured
GN output and target compiler. The test compiles the actual allocator source,
checks both original-header failure modes, and exercises bindgen's Darwin and
Linux loader-environment selection with mocked child processes:

```sh
/absolute/control-python -B -I -S probes/electron/tests/allocator-bindgen-source.py \
  --source /absolute/electron-workspace/src --prepared /absolute/prepared-source/files \
  --gn-out /absolute/electron-work/out --cxx /absolute/electron-work/target-commands/cxx \
  --git /absolute/git
```

This does not test an installed allocator or bindgen execution on the target.

## Shared libdrm routing

```sh
/absolute/native/bin/python3.15 -B -S probes/electron/tests/gn-system-libdrm.py \
  --source /absolute/prepared-source/files --gn /absolute/native/bin/gn \
  --cc /absolute/target-commands/cc --pkg-config /absolute/native/bin/pkg-config \
  --sysroot /absolute/target-sysroot --host-prefix /absolute/native
```

The fixture checks both system and bundled GN routes, including direct libdrm
consumers. It links a target consumer using installed target pkg-config metadata;
it does not execute the program or establish GPU support.

## Selected Node provider command invalidation

```sh
/absolute/native/bin/python3.15 -B -S probes/electron/tests/gn-provider-invalidation.py \
  --source /absolute/prepared/chromium/src --host-prefix /absolute/native \
  --git /absolute/git
```

The fixture applies the provider-command patch and runs real GN, Ninja and Node.
It changes Node, TypeScript and Rollup selections one at a time while the new
JavaScript entries have older timestamps than the outputs. It also changes
provider versions at the same paths, including a test Node wrapper that reports
a new version, and checks refusal of stale configured versions. Chromium `node`,
DevTools Python actions and DevTools JavaScript actions rerun and use the new
selections; unchanged invocations are no-ops. Standalone GN generation is
checked separately. This does not execute the complete Electron target.
