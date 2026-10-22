# Electron cross-build regression tests

Run these commands from the Ports repository root.

Run the regressions with host CPython 3.15 and its standard library. Select an
SDK API 1 source with `--sdk-source`. Each test checks the API and module origin.
Commands, stable SHA256 hashes and JSON receipts use that SDK. Select the
host GN and pkgconf explicitly. The sysroot must contain the real
`gio-unix-2.0` and GTK3 metadata and their dependency closure. POSIX `patch`
must be available on `PATH`. Each output path must be new and outside the
selected source and sysroot.

```sh
python3.15 -E -S probes/electron/tests/gn-pkgconfig.py \
  --sdk-source /absolute/EmberBSD-SDK \
  --source /absolute/chromium/src --sysroot /absolute/target-sysroot \
  --gn /absolute/host-gn --pkg-config /absolute/host-pkgconf \
  /absolute/NEW_PKGCONFIG_WORK
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
The pkg-config test covers sixteen before/after cases. Real pkgconf queries
resolve target gio/GTK paths; the existing cache case must make no pkgconf
calls. The readelf test covers ten cases with production `gcc_toolchain.gni`
and generated `solink` and assembly commands. It preserves host and native
fallback and rejects a missing cross tool. A real `.S` graph input checks that
target and host assembler markers stay separate. Unset assembler commands
remain byte-identical. The selected host Rust compiler supplies only
its `-V` result for an unrelated production GN version probe.

The bindgen test covers twelve before/after GN metadata cases. It also runs
the pinned host bindgen and rustfmt on two minimal C headers, with host and
NetBSD ARM64 parser arguments. It uses the exact libclang directory below the
pinned Rust toolchain. The smoke headers do not include system headers or
exercise the full allocator action. The smoke does not project GCC-only
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
