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

The Electron main selector test evaluates the exact production source block
in ten GN planning cases. Linux source order, Windows, and macOS stay fixed.
NetBSD selects the POSIX main and stdio helper without the glibc environment
shim. The test accepts baseline or already patched Electron source. It does
not compile those C++ files or establish runtime startup.

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

The libc++ GCC 16 regression compares the exact pinned libc++ header blobs
with the carried max-size and `std::function` small-buffer patch. It checks
string allocator, difference-type, SSO, and character-width bounds at compile
time. A public-API `std::function` fixture compiles copy, move, swap,
over-aligned, throwing-copy, and `std::bind` paths against both the pinned
baseline and patched headers in C++11 and C++14. That fixture checks source and
public API compatibility; it is not a causal reproduction of the GCC array-bounds
diagnostic. A separate executable fixture covers bounded string allocation
and function copy, move, swap, over-alignment, and throwing-copy behavior. The
runner compiles that fixture for exact GCC16 targets `aarch64--netbsd` and
`x86_64--netbsd` with exceptions enabled. It checks every successful object for
ELFCLASS64, little-endian encoding, ET_REL type, and the target machine ID. It
does not execute target objects or claim runtime acceptance.

Run it with the selected host CPython 3.15 and an explicit SDK API 1 source:

```sh
python3.15 -E -S probes/electron/tests/libcxx-gcc16-regression.py \
  --sdk-source /absolute/EmberBSD-SDK \
  --ports-root /absolute/Ports \
  --source-root /absolute/chromium/src \
  --patch /absolute/Ports/probes/electron/patches/libcxx-gcc16-maxsize-function-sbo.patch \
  --cxx /absolute/GCC16-aarch64--netbsd-g++ \
  --sysroot /absolute/target-sysroot \
  --work-dir /absolute/NEW_LIBCXX_WORK
```

The runner requires the pinned libc++ revision to be an ancestor of the checkout
and requires both live headers to match either the exact pinned baseline or the
exact carried patch. It rejects unrelated dirty header edits. It obtains the
baseline header bytes only with `git show <pin>:<path>`, builds before/after
overlays, and records the actual checkout head and header hashes. Use a new work
directory outside Ports, Chromium source, the SDK, and sysroot. The string baseline must
fail its max-size contract checks; both baseline and patched function fixtures
must compile. The memory fixture uses exceptions for its behavioral code,
while Chromium production objects still use the existing `-fno-exceptions`
configuration. This regression does not compile or link the complete libc++ runtime. Target
execution remains deferred until an ABI-matching NetBSD libc++ runtime is
available; this runner does not claim Valgrind, ASan, or UBSan runtime coverage.

The causal GCC array-bounds check uses the exact production Perfetto translation
units `unix_task_runner.cc` and `weak_runner.cc`; both fail before the header
change and compile after it with their full GN flags. `cpu_info.cc` provides
the corresponding allocation-size diagnostic check. Those production receipts
cover AArch64. Cppcheck 2.18 cannot parse the unchanged pinned libc++ input in
either variant, so no clean Cppcheck result is claimed. Apple Clang 21 static
analysis of the function and exception-enabled memory fixtures finds no issues
in either variant. Static analysis does not establish runtime memory safety.


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
