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

The native Darwin `lang/libcxx` package uses this same prepared source with
`files/native.py`. It builds libc++ with extensive hardening, ABI namespace
`__1`, filesystem, localization, exceptions and RTTI enabled. It selects the
macOS SDK's system libc++abi/unwinder explicitly and re-exports libc++abi from
the library installed in the selected native prefix. Its headers are installed
in `include/libc++/v1`, outside Clang's implicit adjacent-header search; its
library is in `lib/libc++`, outside ordinary prefix library search. The native
binding must select these headers and the matching library together. Target runtimes use
the full runtime producer described below; the native package is not a target
runtime or a target execution check.

`tests/native-contract.py` checks CMake inputs and Darwin load-command
validation. `tests/native-bindings.py --sdk-source /absolute/EmberBSD-SDK`
checks that CMake uses SDK compiler adapters with nonempty ABI flags. For a
normal consumer check, run `tests/native-consumer.py` with `--sdk-source`,
`--host-prefix`, `--macos-sdk`, `--macos-minimum` and a new absolute `--work`.
Pass `--stage` with a producer DESTDIR to check a staged package; omit it to
check the installed default compiler selection. The staged check temporarily
selects that stage for dynamic loading. The caller coordinates shared prefix
and stage access through the SDK context locks.

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
install-name-tool. In the initial compiler phase, its already required LLVM
dependency also supplies `llvm-libtool-darwin`; this prevents the independent
compiler-rt `UseLibtool.cmake` module from discovering the incompatible pkgsrc
GNU libtool wrapper. Full-phase builds retain the explicitly selected
`EMBERBSD_DARWIN_LIBTOOL`. Other Apple platform runtimes remain separate
target builds.
`tests/native-metadata.py` queries the exported recipe with a selected bmake and
make configuration, including missing-SDK and missing-version controls. It also
checks both archive-selection phases and that `PATCH_ARGS` points to the
monorepo archive root and applies the binary128 patch to the corresponding
file from the pinned source archive.
`tests/darwin-archive.py` loads the actual compiler-rt `UseLibtool.cmake` and
builds a real static archive: the observed GNU-wrapper selection must fail,
while the explicitly selected LLVM Darwin archiver must succeed and contain
the compiled object. It takes the same explicit configure-input JSON as the
parallel outline-atomics regression, plus `--libtool` and `--baseline-libtool`.
Source preparation routes patch backups to temporary directories outside the
published source. This supports native BSD patch, whose `-V none` may still
write `.orig` files; unexpected backups or rejects in the source remain errors.
The native extraction explicitly includes libunwind because the shared patch
set changes its CMake library probes. `tests/native-patches.py` reads the owner
Makefile through the selected pkgsrc framework, extracts its exact
`EXTRACT_ELEMENTS`, and applies every native patch to the real archive. Its
missing-libunwind control reproduces the previous incomplete extraction. Pass
`--sdk-source`, `--bmake`, `--pkgsrc`, `--makeconf`, `--archive`, `--git`,
`--patch` and a new `--work`; repeated `--make-arg` selects bootstrap metadata
inputs without starting a package target.

`patch-13-darwin-outline-atomics` makes the shared outline-atomics helper
files dependencies of one producer target. Both ordinary and kernel-extension
Darwin builtin libraries honor their declared `DEPS`; arm64, arm64e and
arm64_32 share that producer. This prevents separate library rules from
running `create_symlink` concurrently for the same output. The source-file
compile definitions and native archive rules remain unchanged.

`tests/outline-atomics-parallel.py` executes the actual generation block and
Darwin library macro with an explicit native CMake/tool selection. It records
calls to the real `cmake -E create_symlink`, requiring duplicate baseline
writers and exactly one writer for each of the 125 patched outputs. Two
small arm64 ASM archives use the real `lse.S`; no-op and missing-output
rebuilds check incremental behavior. arm64e/arm64_32 checks cover the CMake
dependency graph only. The corrected native package honors the configured
pkgsrc job count, including parallel initial and full builds; there is no
package-wide serialization override. `tests/native-metadata.py` checks the
ordinary `MAKE_JOBS=18` route in both phases.

```sh
python3 -B pkgsrc/lang/compiler-rt/tests/outline-atomics-parallel.py \
    --cmake /absolute/native-prefix/bin/cmake \
    --source /absolute/patched-llvm --baseline-source /absolute/llvm-before-fix \
    --configure-input /absolute/native-input.json --work /absolute/new-check --jobs 18
```

The JSON contains `arguments` (explicit CMake generator, compiler, binutils
and platform options) and `environment` (the selected subprocess environment).
A diagnostic Python relay counts writers and briefly widens their scheduling
window, then invokes the selected CMake operation unchanged. Initial bootstrap
compilers may be used only when already declared for that bootstrap. This
small regression does not build or install the complete compiler-rt package.

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

`patch-04-profile-diagnostics` limits decoded GCOV version state to the modern
format that uses it; the legacy mode retains its explicit checksum and record
layout. The private instrumentation profile file handle has a distinct name
from file parameters, preserving the OS build's `-Wshadow` diagnostics.

`tests/gcda-abi.py --cc /absolute/clang --source /absolute/prepared-llvm` compiles
`InstrProfilingFile.c` and both GCDA modes with strict diagnostics, then checks
independently expected record bytes, merging, callback and counter boundaries,
and injected `fdopen` failure cleanup in both ABI modes. `--cflags` can select
the host ABI and diagnostic sanitizers; temporary files use the caller's
`TMPDIR`. `tests/gcda-allocations.py` accepts the same compiler/source options
and injects six allocation failures plus a counter-size boundary in both ABI
modes. The boundary exercises the actual source with a modeled 32-bit
`SIZE_MAX`; it is not execution of a 32-bit binary. Host checks do not replace
the target libc ABI and execution checks.
The strict-diagnostics fix was also checked with the actual target libc
compiler commands. Paired source analysis found no new diagnostics: the
profile filename lifetime and allocation findings from that comparison are
addressed by the separate memory patch below. Cppcheck's Clang AST importer still
asserts internally; its builtin parser was checked on the actual Clang
preprocessed target sources instead. This is not a successful AST-import check.

## Profile filename and IO ownership

`patch-05-profile-memory` retains the previous owned filename until verbose
replacement logging completes, then frees it exactly once. Precedence, same-name
updates, environment selection and invalid-pattern fallback keep their behavior.
The test-only `lprofCreateBufferIOInternal` allocates its writer before changing
shared IO state and returns NULL on allocation failure, without allocating a
new buffer, changing the free hook or freeing a caller's buffer. Failure to
allocate the optional dynamic buffer still uses the existing static buffer.

This is a local, AI-assisted adaptation of
[LLVM 23.1.4](https://github.com/llvm/llvm-project/blob/llvmorg-23.1.4/compiler-rt/lib/profile/InstrProfilingFile.c),
not submitted upstream. LLVM main and
[FreeBSD main](https://github.com/freebsd/freebsd-src/blob/main/contrib/llvm-project/compiler-rt/lib/profile/InstrProfilingFile.c)
retained both paths when inspected on 2026-10-27. The older NetBSD implementation
has a different API. The archive remains pinned by `lang/llvm` and this recipe's
`distinfo`; native packages and OS preparation consume the same patch.

`tests/profile-memory.py` compiles the actual source with scoped allocation hooks.
Select `--cc`, `--source`, `--runtime-archive` (the matching native common profile
archive for unchanged helpers) and explicit host ABI `--cflags`. The 11 cases
cover owned/borrowed names, verbose/quiet and same-name updates, NULL/default and
invalid-pattern fallback, repeated IO roundtrips, optional-buffer failure and
writer failure with empty or caller-owned state. Allocation counters check
releases and retention; assertions stay enabled with caller NDEBUG flags.
`--profile-file` can select the pre-fix file; `--expect-failure` requires
`-fsanitize=address,undefined` and checks four UAF and two writer-NULL failures
while five controls pass.

All 11 patched cases pass on Darwin arm64 normally and with ASan/UBSan. Upstream
`instrprof-bufferio.c` passes its four buffer sizes in both modes. An instrumented
consumer writes a replacement profile readable by installed `llvm-profdata`
with the expected function count. The actual amd64 libc compile passes; Clang
Static Analyzer loses the UAF, and paired Cppcheck on C preprocessed target
source loses three OOM diagnostics without new findings. Existing style
findings and the AST-importer limitation above remain. ASan/UBSan and allocation
accounting are not Valgrind results; no supported Darwin arm64 Valgrind run was
available. Installed package rebuild and EmberBSD target execution remain
separate checks.

## Target runtime phases

Base identity follows the selected headers, libraries and their complete link closure.
Unrelated runtime socket links may remain unresolved in a build sysroot.
Selected links still reject missing targets, cycles and paths outside the sysroot.
Directory links are expanded before processing subsequent parent components.

Run `files/runtime.py build` with the selected native prefix's Python. The
native tools and target Clang prefix are explicit independent inputs. The
controller uses the common CMake sources, SDK process runner and SDK runtime
validator; it does not download dependencies or select system build programs.
It requires SDK native-checks API 1 and the selected `cpp` role. After creating
the private work directory, it binds the selected host environment through
`native_checks.check_environment`; this makes literal host command lookups such
as CMake's `sh config.guess` resolve to the selected prefix shell. Ambient host
compiler flags are scrubbed, while the target compiler, triplet, sysroot and
target flags remain explicit CMake inputs.
The builtins install path is the absolute target resource directory under
`/usr/pkg/llvm`. CMake declares it as `CACHE PATH`, so an untyped relative
command-line value becomes an absolute build-host path. `DESTDIR` prefixes the
selected target path; no build directory is embedded in the installed tree.

- `--phase builtins` needs actual EmberBSD preliminary headers and installs PIC
  compiler-rt builtins. OS CRT objects remain owned by the OS producer.
- `--phase bootstrap` first builds those builtins, then PIC static libunwind. This prepares
  the archive before a complete C library is available; it does not establish
  compatibility with the older unwinder embedded in libc.
- `--phase full` needs the resulting EmberBSD libc, CRT and headers, plus the
  verified `--bootstrap-stage`. It reuses the builtins and builds static/shared
  libunwind, libc++abi and libc++. The full static unwind archive is rebuilt
  under this configuration; it is not described as byte-identical bootstrap
  output. Static libc++ includes its ABI library. libc++ uses vendor hardening
  mode `extensive` for the installed library and its default headers; its
  existing ABI namespace and options are unchanged. Filesystem and localization
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

`patch-20-libunwind-library-probes` makes actual library probes link even when
bootstrap compiler/header probes use static archives. A missing libc, libdl or
pthread must not become a successful library check or an autolink dependency.
The override is function-local and preserves the caller's compile-only mode.

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
routing, phase boundaries, canonical file prefix maps and resolved base-input
mutations.
`tests/native-shell-routing.py --sdk-source PATH --host-prefix PREFIX
--target-prefix PREFIX --source PREPARED_SOURCE --target aarch64 --work NEW_PATH`
reproduces the literal `sh` lookup failure with the unbound native PATH, then
checks `config.guess` and LLVM's actual `GetHostTriple.cmake` with the shared
selected-shell binding. It also checks that hostile host flag variables do not
change the explicit target Clang and CMake settings.
`tests/install-path.py --sdk-source PATH --host-prefix PREFIX --source
PREPARED_SOURCE --work NEW_PATH` evaluates the exact common compiler-rt path
declarations and target install-dir functions with native CMake. It reproduces
the relative-path failures for target and Linux-native layouts, then checks
real `DESTDIR` installations at the selected target path and Clang host-triple
path. Its installed marker is a path fixture, not a compiled runtime.
`tests/build-stage.py --sdk-source PATH` exercises the actual SDK stage
validator with synthetic target objects, wrong-target and changed-input
controls, failed commands and completion-manifest cleanup.
The older `../llvm/files/build-builtins.py` CLI delegates to these same source
and build mechanisms; its compatibility checks remain under
`profiles/common-build-tools/tests/llvm-builtins.py`.

`tests/unwind-library-probes.py --sdk-source PATH --source PREPARED_SOURCE
--git /absolute/git --host-prefix PREFIX --work NEW_PATH` uses that prefix's
Python and real CMake/compiler. It reproduces a static-probe false positive,
requires the patched function to reject the nonexistent library, checks that
its caller still uses static probes, and links the native C library. Target
runtime configuration and execution remain separate checks.

### WASI preview1 builtins

The same source owner supports `wasi-builtins` and `wasi-verify` for the
`wasm32-wasip1` ABI. It builds freestanding compiler-rt with an empty sysroot
using the selected native LLVM; wasi-libc is not needed for this first phase.
The stage contains the archive and the common compiler-rt licenses. A separate
`lang/wasi-compiler-rt` package invokes this producer and supplies the legacy
`wasm32-wasi` resource-directory alias. The target build does not install a
second compiler or compiler-rt source.

For an ordinary exported pkgsrc tree, invoke its `lang/compiler-rt/files/runtime.py`
with `--pkgsrc-root /absolute/export`. Source preparation uses the exported
recipes and the same byte and patch checks without requiring a Git checkout.
Such sources use manifest v2 with an unknown Ports revision; checkout v1
records remain supported. Either mode verifies the other's prepared tree when
all relevant source and recipe bytes match. `tests/export-source.py` prepares
both modes from the actual archive and checks their identical source and recipe
hashes, cross-verification, and changed-patch rejection.
`tests/wasi-stage.py` verifies a completed stage and checks rejection of
changed or missing archive bytes; it does not build or run a WASI program.
