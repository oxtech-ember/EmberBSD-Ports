# GN for native build generation

The canonical recipe is `pkgsrc/devel/gn`. It selects current upstream commit
`84f10d13f9041068a7da8f9dfc9b991e1049823a`, whose Git history reports
`initial-commit-2610-g84f10d13` (package version `2610`). Chromium 156's
pinned GN revision is an ancestor of this common version.

The official source is the exact
[GN commit archive](https://gn.googlesource.com/gn/+archive/84f10d13f9041068a7da8f9dfc9b991e1049823a.tar.gz).
Gitiles assigns request-time PAX modification timestamps, so its compressed
archive bytes change between requests. The recipe's normal `fetch` phase calls
`pkgsrc/devel/gn/files/fetch-source.py` to verify all source bytes and executable
bits against Git tree `dd53ce1ebf874ac04939e5684fc39e81d87c2008`, then normalize
archive metadata. That tree was independently obtained from the canonical Git
repository at the unchanged commit. The helper accepts only regular files and
their parent directories; duplicate paths, case collisions, traversal, links,
extra content and changed modes are rejected before an output appears.

The resulting `gn-84f10d13f9041068a7da8f9dfc9b991e1049823a.tar` is an
uncompressed USTAR archive with zero timestamps/ownership and sorted names.
Its 1,088 Git-tracked files retain their content and executable bits. Ordinary
pkgsrc `checksum` verifies this complete normalized archive against `distinfo`.
The recipe sets `EXTRACT_DIR` to `WRKSRC` because files are at the archive root.
A missing output is published atomically; an existing file or symlink is never
overwritten. Interrupted or rejected input does not become a cached distfile.

The source helper consumes a control Python with its standard library,
HTTPS trust store and the selected SDK source code's shared Gitiles API.
`GN_FETCH_PYTHON` defaults to the selected native `TOOL_PYTHONBIN`; it may
explicitly name a control interpreter before that native prefix exists.
Set `EMBERBSD_SDK_SOURCE` to the absolute SDK source checkout in pkgsrc, or
pass `--sdk-source /absolute/sdk-source` to the standalone helper. It invokes
no compiler and requires no built SDK, Node, pip or virtualenv. Normal pkgsrc `fetch` and `checksum` still use the
selected framework configuration and retain its license/error checks; the
source-only result does not qualify arbitrary pkgsrc configurations. For offline inspection, the helper's `--input-archive` accepts an
already obtained Gitiles response with the same complete tree verification.

The existing Ports exporter discovers `pkgsrc/devel/gn` as an overlay recipe.
It maps that directory to `devel/gn` in the composed pkgsrc tree. No
`export.conf` entry or `pkgsrc/replaces` entry is needed. The pinned upstream
pkgsrc tree has no `devel/gn` recipe. Export collision checks remain enabled.

## Source changes

The patch to `build/gen.py` preserves the selected toolchain contract. GN 2610
can otherwise download a private CIPD toolchain when CXX is absent; this recipe
requires explicit CXX and AR and refuses that fallback. It also:

- On POSIX, the GCC probe passes the selected C++ command as an argument vector.
  It does not invoke a system shell. The Windows command route is unchanged.
- `GN_VERSION` supplies the recorded commit position and short hash when the
  source archive has no `.git` directory. The complete string is validated.
  The ordinary Git checkout route and the generated header format remain intact.
- Explicit Darwin `-mmacosx-version-min=` flags remain unchanged in the compile
  and link command. The upstream minimum version `14` is added only when that
  command has no explicit deployment minimum.

The archive-version approach follows
[FreeBSD devel/gn](https://cgit.freebsd.org/ports/tree/devel/gn/files/patch-build_gen.py).
The source keeps the Chromium copyright and BSD-style license. The FreeBSD
and [OpenBSD recipe](https://cvsweb.openbsd.org/ports/devel/gn/Makefile) were
reviewed for the Python, Ninja, archive-version and upstream-test routes.
Their source versions and platform patches are not copied into this recipe.

The Darwin `ScopedTypeRef` patch limits Objective-C ownership annotations to
Objective-C translation units. Plain C++ keeps the same explicit Traits retain
and release operations, including the CoreFoundation specialization.

## Electron BSD host-tool patch ownership

Electron's Chromium Git graph has no `tools/gn` checkout. Its legacy pkgsrc
Chromium GN patches belong to this provider, independently of the Electron
target OS. The selected Darwin host uses the common GN source above:

| Legacy change | Disposition at the pinned common source |
|---|---|
| Replace thin archive `rcsT` with `rcs` | Keep the upstream LLVM-capable route; actual package archive/link checks remain required. |
| OpenBSD generator template and `-lkvm` | OpenBSD host work; not required for a Darwin host targeting EmberBSD. |
| BSD `fsync` to `fdatasync` | Keep upstream `fsync`; the patch changes flushing behavior rather than providing a missing API. |
| Map `evbarm` to `arm64` | Do not infer CPU width from this board family; it covers 32-bit and 64-bit systems. |
| Rename `Version::major/minor/patch` | Already unnecessary: the pinned header undefines `major` and `minor` macros. |
| OpenBSD executable path through kvm | OpenBSD host work; the pinned source already has NetBSD's `KERN_PROC_PATHNAME` route. |

The Electron overlay inventory retains all six patch names with these reasons.
This source review does not qualify an OpenBSD/NetBSD-host GN build or change
Electron's target sandbox. Add any required host adaptation here with its own
platform check; do not introduce a second GN source tree inside Chromium.

## Build and acceptance

Use the native Ports Clang/LLVM prefix for a native GN build. An explicit GCC
platform profile remains supported. The recipe accepts both families and
requires C++23; it does not select or retry a compiler family.
Select it with the SDK `load_host_prefix` API and required roles `cxx`, `ar`,
`python`, `ninja`, `sh`, `rm` and `make`. No producer receipt is required.
Use its compiler ABI flags and selected tool paths in the native pkgsrc configuration.
Keep the native package prefix separate from the EmberBSD target sysroot.
The Python and Ninja tool dependencies run on the build host. The C++ and
archive commands compile for the selected package target.

For native Darwin, the recipe runs these source-owned operations:

1. Selected Python runs `build/gen.py --platform darwin --host darwin`.
   `CXX` and `AR` select selected Ports tools. `GN_VERSION` is
   `2610 (84f10d13f904)`. The selected C++ flags include the SDK preprocessor
   and C++ ABI flags. Link flags remain the selected native link flags.
2. Selected Ninja runs `-C out -j 18 gn` for a jobs-18 build.
3. The test phase separately builds `-C out -j 18 gn_unittests`, then runs
   `out/gn_unittests`. The Python tool fragment supplies the selected native
   `python3` alias used by the upstream process test.
4. Installation copies `out/gn`, `LICENSE` and `README.md` through the pkgsrc
   program and data installation commands.

Each Ninja invocation has one executable link. Keep the existing global heavy
link lock for each invocation when using the SDK process API directly.
Do not start the default `all` target beside the test target. Keep the existing
owned-process deadline, drainage, input leases and MemoryWatch policy.
The recipe retains upstream warnings as errors. It does not select the
Clang-specific LTO option. Selected Darwin SDK deployment flags and the selected compiler runtime remain visible
for the actual ABI and runtime checks.

For cross packages, `--platform` uses `LOWER_OPSYS` and `--host` uses
`NATIVE_LOWER_OPSYS`. The recipe does not run the target executable during
configure or build. The test target refuses host execution of a cross-built
`gn_unittests`; run it on the matching target instead.

After the native package build, check `gn --version` against
`2610 (84f10d13f904)`. Run the upstream unit tests and a small GN-to-Ninja
project. Use `--script-executable=<selected native Python>` for GN generation.
For optional Ninja post-processing, pass
`--ninja-executable=<selected native Ninja>` explicitly.
Verify the installed Mach-O architecture, compiler identity, load commands
and complete runtime closure before adding the `gn` role to an SDK bundle.
Select the installed tool with the SDK host-prefix API. No separate qualification is required.

## Shared CXX bridge

GN uses the installed common `cxxbridge` 1.0.205 generator and matching
`include/rust/cxx.h`. Configure copies only that header to an isolated build include tree, checks its
identity against the generator, and regenerates
GN's bridge from its Rust declarations. Thin adapters retain borrowed string
lifetimes and check that all GN value enum discriminants match. The Rust
Starlark lock selects the same CXX release instead of its former fork.
The ordinary upstream default does not enable experimental Starlark. When
explicitly enabled, its Cargo actions use `--offline --locked`; its separate
Rust source closure and runtime have not been validated here.

The source regression below also supports an explicit bridge check:

```sh
python3 profiles/common-build-tools/tests/gn-cxx.py \
  --archive /absolute/distfiles/gn-84f10d13f9041068a7da8f9dfc9b991e1049823a.tar \
  --patch /absolute/host/bin/gpatch --cxxbridge /absolute/host/bin/cxxbridge \
  --include /absolute/host/include --cxx /absolute/host/bin/clang++
```

It applies the full source series without fuzz, verifies generator/header and
Rust lock identities, and compiles five real GN FFI translation units. It is
not an enabled Starlark runtime test.

## Source regression

Run the pure regression with the exact downloaded source archive:

```sh
python3 profiles/common-build-tools/tests/test-gn-recipe.py \
  --archive /absolute/path/gn-84f10d13f9041068a7da8f9dfc9b991e1049823a.tar -v
```

It checks the archive and patch checksums, exact patch context, POSIX compiler
argument preservation, the Windows route, compiler macro failures, version
header identity, malformed version refusal and Darwin SDK minimum preservation.
It also runs the complete patched upstream generator for native Darwin and
Darwin-to-NetBSD Clang routing, plus explicit GCC routing. Generated Ninja
commands retain C++23, warnings as errors, the selected C++/archive tools and
compiler-specific warning flags. Compiler macro responses are mocked; no
compiler, GN or Ninja binary runs by default. Passing
`--initial-cxx-command '/absolute/initial/clang++ declared-flags'` adds actual
Clang macro detection through the same upstream generator. That optional source
inspection uses the explicitly declared initial compiler only for
`-dM -E -` on empty input; it does not compile or link GN objects.
Native build, package lifecycle, upstream test and installed runtime acceptance
remain pending.

The source-owner regression uses two real Gitiles responses with different
request timestamps. Obtain them from the official commit archive above, then run:

```sh
EMBERBSD_SDK_SOURCE=/absolute/sdk-source python3 profiles/common-build-tools/tests/gn-source.py \
  --gitiles-archive /absolute/first-response.tar.gz \
  --gitiles-archive /absolute/second-response.tar.gz -v
```

It requires different input bytes, reconstructs the pinned tree for both and
requires identical normalized `distinfo` output. Separate negative controls
cover changed blobs/modes, missing/extra files, special permissions, duplicate
paths, case-colliding parents, traversal, symlinks/hardlinks/devices, truncated
input and existing output preservation. This checks source acquisition only.

## Darwin C++ ownership regression

`tests/gn-scoped-typeref.cc` includes the actual GN header and CoreFoundation traits.
Compile it with the selected native C++ compiler and `-std=c++23 -DNDEBUG -Wall -Wextra
-Werror -Wno-unused-parameter`, the GN source include directory, and
`-framework CoreFoundation`. The repaired include directory must precede
the original GN source directory for a paired check.

On Darwin arm64, the original header fails compilation. The repaired header
compiles without diagnostics and prints `gn-scoped-typeref: PASS`.
The fixture checks explicit ownership counts and real CFString operations.
Removing retain or release still compiles but fails the runtime checks.
GCC16 ASan and UBSan runs pass. LeakSanitizer does not complete on this host;
leak checking and Valgrind execution remain unverified.
Cppcheck and GCC16 analyzer report no findings. Clang Static Analyzer reports
one moved-from-use warning for the intentional empty-state test. The move
constructor explicitly clears that state, and `get()` permits reading it.
These focused checks do not establish a complete GN build.

## Xcode platform errors

The Xcode writer validates project attributes before it constructs the project.
Invalid `target_xcode_platform` values reach the caller through its `Err` object.
The parser still accepts `iphoneos` and `tvos`. An absent value still selects
`iphoneos` for an iOS target. macOS keeps its existing platform behavior.
This repair is AI-assisted EmberBSD work. It is not submitted upstream.

Run the real generation regression with a native GN binary and explicit Python:

```sh
python3 profiles/common-build-tools/tests/gn-xcode-errors.py \
  --gn /absolute/path/to/gn --python /absolute/path/to/python3
```

The eight cases check default, iPhoneOS, tvOS and macOS attributes. They require
normal error exits for invalid type, unknown value and empty value. Invalid
settings must not write an Xcode project. The fixture does not compile or run
Ninja targets. It must run on the binary's host. Generation, source analysis
and a successful object compile do not establish a complete package or Xcode
application build.

A paired Darwin arm64 GCC16 check reproduces the null `this` diagnostic in the
original translation unit. The changed translation unit compiles with the same
warnings and optimization flags. Clang Static Analyzer completes without
findings on either version. Cppcheck reports the same 64 diagnostics before
and after the change. Three inherited diagnostics concern null-pointer
arithmetic after allocation failure in `hash_table_base.h`; they remain
unresolved. No analyzer categories are disabled. The real generation fixture,
ASan/UBSan execution of this path and the complete GN tests remain pending.

The native GCC16 build passed all 817 upstream unit tests and all eight generation cases.
A diagnostic build instrumented the changed Xcode writer and its inline code with GCC16 ASan and UBSan.
All eight generation cases passed without sanitizer diagnostics.
The diagnostic link used one shared GCC C++ runtime. The ordinary build kept its existing runtime policy.
Leak detection was disabled because LSan did not complete on this host. This is not a leak-check result.
