# Common compiler-rt package and LLVM runtime sources

This owner prepares the LLVM runtime components used by Ports and the EmberBSD
native OS build. `../llvm/version.mk` and `../llvm/distinfo` remain the sole
version and release-archive selection. `files/source-components.json` selects
compiler-rt, libc++, libc++abi, libunwind and their common CMake/header inputs;
it does not import a second LLVM code generator.

The producer uses Python's standard library and the explicitly selected SDK
source preparation API 2. It verifies the archive bytes and every patch, uses
the SDK's bounded component extraction, applies the complete patch set with
zero fuzz (including applicable CMake patches from `lang/llvm`), and publishes a new source directory. Existing output is never
replaced. It does not configure or compile a target and needs no final SDK
sysroot.

```sh
python3.15 -B pkgsrc/lang/compiler-rt/files/runtime.py --sdk-source /absolute/EmberBSD-SDK prepare \
    --archive /absolute/distfiles/llvm-project-23.1.4.src.tar.xz \
    --source /absolute/prepared-llvm --patch /absolute/patch --git /absolute/git
python3.15 -B pkgsrc/lang/compiler-rt/files/runtime.py --sdk-source /absolute/EmberBSD-SDK verify-source \
    --source /absolute/prepared-llvm --git /absolute/git
```

Run these commands from the Ports source checkout. The returned JSON is also
stored as `llvm-source.json` inside the source root. Its format is
`emberbsd-llvm-source`, version 1. It records the LLVM version, selected
components, archive basename/checksums/size, Ports revision, exact recipe input
hashes and a hash of the complete prepared tree. The manifest excludes itself
from that inventory. Verification compares relevant recipe inputs; unrelated
Ports commits do not invalidate the same prepared source.

The OS consumes this root through `EMBER_LLVM_SOURCE`. Its own native makefiles
retain libc ABI integration, CRT objects and installation paths. The runtime
root contains `runtimes/CMakeLists.txt`, `compiler-rt/CMakeLists.txt` and
`llvm/cmake`; it intentionally omits `llvm/CMakeLists.txt` and backend sources.

`patch-00-binary128-fenv` transfers the EmberBSD AArch64 libc floating-point
exception policy onto the current upstream binary128 comparator. The opt-in
`COMPILER_RT_NETBSD_AARCH64_FENV` applies only to hard-float userland libc.
Ordered comparisons raise invalid for every NaN, while equality and unordered
comparisons raise it only for signaling NaNs. Other builds retain upstream
behavior. The existing comparator and architecture-specific result types stay
upstream-owned. The transferred adaptation retains its MIT/NCSA licensing in
`compiler-rt/lib/builtins/LICENSE.EmberBSD-BINARY128.TXT`; the exact legacy
contributors list remains in `compiler-rt/CREDITS.TXT`.

`tests/source.py` exercises actual preparation with the selected archive and
checks existing-output, changed-file, added-file, changed-identity and corrupt
archive refusals. Supply `--sdk-source`, `--archive`, `--git`, `--patch` and a
new `--work` directory. The binary128 source tests require explicit `CC`,
`BINARY128_SOURCE` and a caller-owned `TMPDIR`. The contract compiles the full
production comparator with only its bit container and hardware exception hook
substituted; it covers 3,600 input/predicate combinations. The boundaries test
checks seven forbidden opt-ins and malformed extraction. These checks do not
replace real AArch64 object inspection or device FENV execution.

The ordinary `lang/compiler-rt` package uses the same monorepo patch directory
and archive as this source preparation interface. Native Clang depends on it
so its compiler-owned builtins and diagnostic runtimes are installed from the
common version. On Darwin, the package requires explicit `OSX_SDK_PATH` and
`EMBERBSD_DARWIN_SDK_VERSION`, selects the native CPU and uses LLVM lipo and
install-name-tool. Other Apple platform runtimes remain separate target builds.
`tests/native-metadata.py` queries the exported recipe with a selected bmake and
make configuration, including missing-SDK and missing-version controls. It also
checks that `PATCH_ARGS` points to the monorepo archive root and applies the
binary128 patch to the corresponding file from the pinned source archive.

`patch-01-gcda-fdopen` fixes an upstream failure path where an unsuccessful
`fdopen` led to a null stream access. It closes the descriptor and releases the
associated lock and filename before returning. `patch-02-libc-gcda-abi` adds the
explicit `COMPILER_RT_LIBC_LEGACY_GCOV` mode for the existing EmberBSD libc GCDA
ABI: the old public entry points, record format and callbacks remain available,
while ordinary compiler-rt retains the current upstream ABI. Both modes share
the current implementation. The transferred code retains its MIT/NCSA notice
in `compiler-rt/lib/profile/LICENSE.EmberBSD-GCOV.TXT` and the common credits.

`patch-03-gcda-allocation-failures` handles failed callback, filename, buffer
and merge allocations, preserves the previous buffer when `realloc` fails,
and stops counter allocations that exceed `SIZE_MAX`. It reports the failure
and releases resources without writing a partial newly created profile. This
does not make updates to an already mapped profile transactional.

`tests/gcda-abi.py --cc /absolute/clang --source /absolute/prepared-llvm` checks
independently expected record bytes, merging, callback and counter boundaries,
and injected `fdopen` failure cleanup in both ABI modes. `--cflags` can select
the host ABI and diagnostic sanitizers; temporary files use the caller's
`TMPDIR`. `tests/gcda-allocations.py` accepts the same compiler/source options
and injects six allocation failures plus a counter-size boundary in both ABI
modes. The boundary exercises the actual source with a modeled 32-bit
`SIZE_MAX`; it is not execution of a 32-bit binary. Host checks do not replace
the target libc ABI and execution checks.

## Target runtime phases

Run `files/runtime.py build` with the selected native prefix's Python. The
native tools and target Clang prefix are explicit independent inputs. The
controller uses the common CMake sources, SDK process runner and SDK runtime
validator; it does not download dependencies or select system build programs.

- `--phase builtins` needs actual EmberBSD preliminary headers and installs PIC
  compiler-rt builtins. OS CRT objects remain owned by the OS producer.
- `--phase bootstrap` first builds those builtins, then PIC static libunwind. This prepares
  the archive before a complete C library is available; it does not establish
  compatibility with the older unwinder embedded in libc.
- `--phase full` needs the resulting EmberBSD libc, CRT and headers, plus the
  verified `--bootstrap-stage`. It reuses the builtins and builds static/shared
  libunwind, libc++abi and libc++. The full static unwind archive is rebuilt
  under this configuration; it is not described as byte-identical bootstrap
  output. Static libc++ includes its ABI library. Filesystem and localization
  retain their upstream enabled behavior.

```sh
/absolute/host-pkg-llvm/bin/python3.15 -B \
  pkgsrc/lang/compiler-rt/files/runtime.py --sdk-source /absolute/EmberBSD-SDK build \
  --source /absolute/prepared-llvm --target aarch64 --phase bootstrap \
  --sysroot /absolute/emberbsd-headers --os-source /absolute/EmberBSD \
  --host-prefix /absolute/host-pkg-llvm --target-prefix /absolute/target-llvm \
  --work /absolute/objects/runtime-bootstrap --stage /absolute/stages/runtime-bootstrap \
  --git /absolute/git --jobs 4
```

All C, C++ and assembly commands disable implicit Clang configuration files.
The selected linker and runtime driver options are scoped with
`--start-no-unused-arguments` / `--end-no-unused-arguments`, so compile-only
feature checks keep their other diagnostics. Runtime builds use source CMake
modules without importing native LLVM/Clang package output paths. Compiler
resource headers are selected separately with `-nobuiltininc -isystem`; host
runtime libraries are never imported into the target resource directory.

### Frame discovery and the OS boundary

Both phases explicitly use `LIBUNWIND_ENABLE_FRAME_APIS=OFF` and
`LIBUNWIND_USE_FRAME_HEADER_CACHE=OFF`; thread support stays enabled. In LLVM 23,
`__register_frame` and `__deregister_frame` remain real public per-FDE JIT APIs
with FRAME_APIS disabled. Enabling FRAME_APIS exposes the `*_frame_info` and frame-table compatibility
stubs; those upstream functions do no registration.
See [the exact LLVM implementation](https://github.com/llvm/llvm-project/blob/llvmorg-23.1.4/libunwind/src/UnwindLevel1-gcc-ext.c).

For ordinary ELF code, LLVM uses `dl_iterate_phdr` and `PT_GNU_EH_FRAME`; the
NetBSD Clang driver already emits `--eh-frame-hdr`. The weak legacy references
in OS crtbegin can remain unresolved on this path. That does not implement the
old frame-info API for consumers that require it. JIT consumers must register
and deregister each FDE with the actual public API, not pass a whole section as
one FDE or depend on the compatibility stubs.

The optional header cache assumes serialized `dl_iterate_phdr` callbacks. The
current OS loader permits concurrent readers, so it does not satisfy that
assumption. Keep the cache off until a separate synchronization change is
verified. The [LLVM cache contract](https://github.com/llvm/llvm-project/blob/llvmorg-23.1.4/libunwind/src/FrameHeaderCache.hpp)
and [OS loader](https://github.com/oxtech-ember/EmberBSD/blob/main/libexec/ld.elf_so/rtld.c)
are the owners of that boundary.

OS integration must select one unwinder implementation and registration cache.
Embedding a bootstrap archive in libc while also exporting a separate full
libunwind is not by itself proof of coherent symbol binding. Before a full
sysroot is accepted, execute static and dynamic backtraces, shared exceptions,
dlopen/dlclose and per-FDE JIT registration/deregistration on each target; check
which DSO provides the APIs. Successful CMake and link checks do not establish
these runtime behaviors.

Both work and stage must be new directories. For the full phase, select the
completed C base with `--sysroot`, use new work/stage paths and add
`--bootstrap-stage /absolute/stages/runtime-bootstrap`. The native compiler
family defaults to Clang; `--host-compiler-family gcc` is an explicit native
exception and does not change the LLVM target runtime.

Each successful phase emits the bare `runtime.json` record, with payload under
`stage/usr/pkg/llvm`. `verify --stage PATH --target aarch64 --phase bootstrap
--git /absolute/git` verifies the component profile, complete payload and current
source/recipe inputs; optional `--base PATH` verifies the recorded base input
subset. The format is the SDK `emberbsd-llvm-runtime`, version 1. The base
identity records actual headers/libraries and every contained symlink hop and
resolved target, without requiring a final SDK manifest. These fingerprints
identify supplied bytes and the independently selected OS revision; they do
not prove that this checkout produced the supplied headers and libraries.
A full stage also
records its consumed bootstrap manifest and archive hashes.

The full producer links C programs dynamically and statically and C++ programs
statically and across a shared-library exception boundary. These consumer
fixtures cover constructors, TLS, threads, locale and filesystem APIs. The
executables stay in the work directory for later execution on the matching
EmberBSD target; successful linking does not claim target execution. Runtime
libraries retain their licenses and transferred adaptation notices in the
installed prefix.

`tests/build-contract.py --sdk-source PATH --work NEW_PATH` checks native/target
routing, phase boundaries and resolved base-input mutations.
`tests/build-stage.py --sdk-source PATH` exercises the actual SDK stage
validator with synthetic target objects, wrong-target and changed-input
controls, failed commands and completion-manifest cleanup.
The older `../llvm/files/build-builtins.py` CLI delegates to these same source
and build mechanisms; its compatibility checks remain under
`profiles/common-build-tools/tests/llvm-builtins.py`.
