# Electron cross-build regression tests

Run these commands from the Ports repository root.

Run the regressions with host CPython 3.15 and its standard library. Select an
SDK API 1 source with `--sdk-source`. Each test checks the API and module origin.
Commands, stable SHA256 hashes and JSON receipts use that SDK. Select the
host GN and pkgconf explicitly. The full integration test requires a sysroot
with real `gio-unix-2.0` and GTK3 metadata and their dependency closure. The
x64 selector test uses an empty synthetic sysroot and mock pkgconf. POSIX
`patch` must be available on `PATH`. Each `NEW_WORK` path must be new and
outside the selected source and any external sysroot.

```sh
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
python3.15 -E -S probes/electron/tests/gn-mac-host-debug-fission.py \
  --sdk-source /absolute/EmberBSD-SDK --source /absolute/chromium/src \
  --gn /absolute/host-gn \
  --patch /absolute/Ports/probes/electron/patches/gn-mac-host-debug-fission.patch \
  --clang /absolute/pinned-host-clang++ --host-target arm64-apple-macos \
  --target-cxx /absolute/GCC16-target-g++ --target-sysroot /absolute/target-sysroot \
  --target-gcc-lib-version /absolute/GCC16-target-lib-version \
  --target-gcc-lib /absolute/GCC16-target-lib /absolute/NEW_MAC_DWARF_WORK
python3.15 -E -S probes/electron/tests/partition-alloc-netbsd-gcc16.py \
  --sdk-source /absolute/EmberBSD-SDK --ports-root /absolute/Ports \
  --source-root /absolute/chromium/src \
  --patch /absolute/Ports/probes/electron/patches/partition-alloc-netbsd-gcc16.patch \
  --cxx /absolute/GCC16-target-g++ --sysroot /absolute/target-sysroot \
  --workdir /absolute/NEW_PARTITION_ALLOC_WORK
```

The tests accept the original or already fixed source. They apply the carried
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

The Mac debug-fission test copies the production `mac/BUILD.gn` without changes.
It supplies a minimal Apple-template mock that forwards the production toolchain
arguments. Four GN fixtures compare cross-host, NetBSD target, and native Mac
output declarations. The generated original host command fails on its extra
`.dwo` output. The fixed command compiles with the pinned Mac Clang. A header-free
GCC16 target probe retains its object, depfile, and `.dwo`. A native Mac probe is
unchanged, and an intentional GCC warning still fails under `-Werror`. The test
does not evaluate the complete Apple template or compile Chromium source files.

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

The test applies the patch with zero fuzz to copies of two pinned GN files.
It executes the production GN conditions and OS definitions for 13 platforms
with official builds enabled and disabled (52 successful GN runs).
Independent expectations reject the baseline BSD helper selection and verify
the corrected selection, unchanged non-BSD behavior, generic ELF strip targets,
and the existing NetBSD policy sources. The work directory retains hashes,
commands, JSON observations, and bounded fixture sources. It does not build
Electron or validate NetBSD OS isolation or installed sandbox behavior.
