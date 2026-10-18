# Run target LLVM metadata queries on the build host

Mesa's cross configuration needs an executable on the build host that describes
the EmberBSD LLVM package. The existing native generator build's `llvm-config`
describes that host and must not be used as target metadata. The target
executable cannot run directly on macOS or Linux.

`build-llvm-config.rb` compiles the pinned upstream LLVM 23.1.3
`tools/llvm-config/llvm-config.cpp`. It reuses the existing native Support,
TargetParser and Demangle archives; it does not build LLVM libraries. Ruby,
the original native C++ compiler and shasum are host dependencies. This is a
private build tool, never a target package or a second installed LLVM provider.

```sh
ruby build-llvm-config.rb /absolute/llvm-source \
    /absolute/target-cmake-build /absolute/native-generator-build \
    /absolute/target-sysroot /absolute/target-stage/usr/pkg /absolute/new-work
ruby test-llvm-config.rb /absolute/new-work
/absolute/new-work/bin/llvm-config --version --host-target --has-rtti
/absolute/new-work/bin/llvm-config --link-shared --shared-mode core orcjit native
```

The source is the `llvm` subdirectory, not the llvm-project root. The two build
directories must have matching LLVM 23.1.3 sources and completed generated
metadata. Keep the input trees unchanged through building, acceptance and
sealing. The sealed tool then permits build-tree cleanup while checking the
installed package on every query. Use a fresh output directory.
The helper currently accepts the canonical
NetBSD/AArch64 or NetBSD/amd64, shared LLVM, RTTI and `/usr/pkg` layout with a
macOS native compiler or genuine GCC16 on GNU/Linux amd64 or AArch64. Linux
requires native `readelf` and `ldd`. Whitespace in paths and unsupported native
library arguments are rejected rather than guessed. Linux triples accept both
`x86_64-linux-gnu` and `x86_64-unknown-linux-gnu` (likewise AArch64); musl and
other native platforms are not covered.

Target `BuildVariables.inc`, `LibraryDependencies.inc` and
`ExtensionDependencies.inc` provide the actual component graph and options.
Target generated configuration supplies both triples; the checked version and
assertion setting also come from that configuration. All native platform and
ABI headers remain native. Report-only substitutions occur after those headers;
target configuration is never substituted into the Support library interfaces.
The source hash and replacement contexts are checked before compilation.
Target triple macros retain their configured spelling. Upstream `llvm-config`
normalizes its reported `--host-target`, including an empty vendor field.
The receipt keeps both the configured and actually queried target triples.
Comparison uses the reported triple captured from the actual executable.

An explicit target prefix replaces upstream's executable-location detection.
For an installed layout it points to the real staged `/usr/pkg` directory;
all library availability checks remain upstream code. A target build directory
can be used for early metadata-only inspection, but it is not the final staged
prefix: this LLVM build creates the `libLLVM-23.so` alias during installation.
Missing shared libraries therefore produce a real failure until staging is
complete. No placeholder library or fake success response is created.
For staged mode the helper also checks matching generated public configuration
headers, the selected ELF64 machine and shared-library identity against this target
build. An unchanged library must match byte for byte. For an `install-strip`
payload, the generated shared-library install script must contain the exact
no-argument `CMAKE_STRIP` operation and no RPATH transformation. The helper
copies the original build output, runs that recorded strip executable, and
requires its SHA256 to match the staged library. Other differences fail.
The receipt records the original, staged and reproduced hashes, strip version,
executable and install script. Both libraries and strip inputs are covered by
the original query-time integrity manifest. Keep those inputs until acceptance,
then seal the accepted tool as described below before cleaning build trees.

Library search flags such as `-L/usr/pkg/lib` map into the supplied target
sysroot. The selected LLVM prefix's libdir comes first, as in upstream.
Runtime RPATH flags remain target paths. Metadata already containing the private
sysroot or unknown external search paths fails. Fix such a leak in the target
LLVM metadata generation first; the host helper must not conceal it.
The LLVM producer omits the common profile's two sysroot `rpath-link` arguments
from reported metadata. Actual build links retain both dependency searches.
The receipt preserves both original and mapped flags, and the supplied sysroot
must match the target configuration.

`receipt.json`, `compile.command` and `compile.log` record the inputs and build.
`inputs.sha256` covers the source, original generated metadata/configuration,
compiler, native archives, actual header dependencies and resulting
tool. Input changes during compilation fail. The `bin/llvm-config` launcher
checks the receipt before every invocation,
then executes the real compiled program; it does not parse query options or
synthesize results. Changed inputs require a fresh tool build.

On Linux, the compiler reports its real include search roots and GCC16 runtime
locations. The dependency file includes system headers as well as LLVM headers;
all are hashed and must belong to those measured native roots or the matching
LLVM source/build. Headers and loaded libraries inside the target trees fail.
The Linux dependency scan retains GCC's include-search header names. This
supports native UAPI header symlinks without admitting their entire destination
directory. A header that resolves inside a target tree still fails.
The focused `tests/llvm-native-headers.rb` regression uses real GCC16 UAPI
dependencies and a work-directory link to an actual target SDK header.
The native Support/TargetParser/Demangle archives remain static. `readelf` and
`ldd` inspect the real compiled helper and its complete ELF dependency graph;
the loaded `libstdc++` and `libgcc_s` must be the selected compiler's files.
The loader and every loaded DSO are copied byte for byte under `native/lib`.
An execution of the copied loader with its cache disabled verifies that the
complete closure resolves inside that payload. Unresolved dependencies,
architecture mismatches, unexpected loaded libraries and shared native LLVM
dependencies fail. The launcher clears loader injection/search environment
variables and invokes the retained loader with that library directory.

## Preserve an accepted tool across build cleanup

The original helper's complete build receipt also checks temporary compiler
inputs and the unstripped target library on every query. Removing a completed
build therefore invalidates that launcher even when its executable and the
installed LLVM package remain unchanged. Do not remove entries from its receipt.

After accepting the tool, use `seal-llvm-config.rb` with the original manifest
SHA256 from the preserved build/acceptance evidence:

```sh
ruby seal-llvm-config.rb /absolute/accepted-helper ORIGINAL_MANIFEST_SHA256 \
    /absolute/new-sealed-helper
ruby ../tests/llvm-config-seal.rb /absolute/accepted-helper \
    ORIGINAL_MANIFEST_SHA256 /absolute/new-sealed-helper \
    /absolute/fresh-target-reference /absolute/new-seal-test-work
```

The mandatory external hash authenticates the unchanged original manifest.
The sealer requires the exact recorded local executable, generated report data,
target configuration headers and installed LLVM library. Every original entry
has an explicit class; unknown paths and missing required entries fail.
Native header classifications come from the authenticated compiler dependency
file. Compiler sources, caches and original build outputs are historical inputs:
their observed hashes or absence remain in `seal.json`. Sealing does not repeat
the historical strip transformation or claim that a missing build DSO was checked.

The small output retains the original receipt, full manifest and launcher in
`provenance/`, together with immutable target metadata. The executable is copied
byte for byte. Its new launcher checks this complete sealed payload and the
live installed headers/library, then runs the same upstream program. No query
answers are synthesized. Source/build cleanup no longer affects execution;
installed-library drift still fails before any query. Preserve the sealed tree
and use its `bin/llvm-config` in the graphics cross MAKECONF.

Linux sealing also retains and verifies the complete native ELF payload. Its
original system/compiler library paths and inspection tools become historical
inputs; the sealed manifest checks their retained copies. The target package's
installed headers and LLVM DSO remain live inputs. This permits later removal
of native compiler/build directories without falling back to another host GCC
runtime. Darwin retains its existing system-library inspection and launcher.

The bounded Linux runtime contract needs no LLVM source or fabricated target
metadata:

```sh
HOST_CXX=/absolute/native-gcc16/bin/g++ \
    ruby ../tests/llvm-native-runtime.rb /absolute/new-native-test-work
```

It compiles and executes a real C++ threads/containers/exceptions program,
checks exact loader resolution, copies it with the production runtime-copy
routine, removes the original helper pathname by renaming its private tree,
and repeats execution. Negative cases cover changed, missing or symlinked
runtime files, directory escapes, foreign ELF machines and unsupported native
triples. A real ELF also retains its interpreter as a direct dependency and
passes closure copying and execution. On 2026-10-18 this contract passed 23
checks on Linux amd64 with
GCC16.2.0. This is native runtime retention coverage, not an LLVM build or full
`seal-llvm-config.rb` acceptance: the new Linux helper still requires real
LLVM23 native/target builds, installed target payload validation and the
16-query agreement below. Earlier Darwin/board receipts do not validate it.

Repeat the 16-query comparison below with a fresh capture from the installed
target after sealing. On 2026-10-08, the unchanged accepted executable agreed
with all 16 groups captured on Zero 3W with the updated kernel. The original
build library had been removed and its CMake cache changed; both facts remain
recorded in the sealed provenance. The installed shared-library SHA256 was
unchanged, so this did not require another LLVM compile or ORC runtime run.

Set the [graphics cross profile's](profile.md) `EMBERBSD_GRAPHICS_LLVM_CONFIG`
to `NEW_WORK/bin/llvm-config` after staging the target library. The helper does
not select that profile or change the shared LLVM recipe by itself.

## Agreement with the actual target executable

After the same LLVM package has been staged and transferred to a target, run:

```sh
sh record-llvm-config.sh --target amd64 /absolute/target-prefix/bin/llvm-config \
    /absolute/new-reference
```

The default remains `--target aarch64`. The capture requires the selected
NetBSD `uname -p`, a matching little-endian ELF64 executable, LLVM 23.1.3 and
the matching NetBSD 11 target triple before it creates the output directory.
Both GNU and `unknown` vendor spellings are accepted. Use the installed base
`readelf`, or set `READELF` to an explicit target-native diagnostic executable.
The standalone script requires no Ports checkout, compiler or headers on the
target. `target.txt` retains its selected target, processor and GNU triple.

From the Ports root, the bounded host source-contract fixture is:

```sh
READELF=/absolute/cross/bin/x86_64--netbsd-readelf \
CROSS_TEST_TOOLS=/absolute/amd64-gcc16 \
    ruby profiles/common-graphics/tests/acceptance-entrypoints.rb
```

It checks both targets and foreign-input refusal with real ELF inspection.
Controlled `uname` and query boundaries do not execute NetBSD code on macOS
or constitute the required real target capture.

Transfer the reference directory back with a verified archive hash. On the build host:

```sh
ruby compare-llvm-config.rb /absolute/new-work /absolute/reference
```

The comparison requires the helper to use a staged prefix, not a development
tree. It checks version, triples, RTTI, assertions, backends, component graph,
compiler flags, linker flags, shared mode and the complete Mesa module request.
Only documented prefix/sysroot mappings are applied; other differences fail.
The capture marks completion only after every actual target query succeeds.
It does not install anything or execute target code on the build host.

The host regression checks real upstream queries plus rejection of unknown
components, Darwin metadata/prefix, private sysroot leaks, modified upstream
source, modified generated metadata, modified helper executable and missing
shared LLVM. This does not replace a target C/C++ API link/run, Mesa
configuration, ORC JIT tests or the
full graphics package acceptance.

On 2026-10-08 the helper passed all 15 query/refusal checks against the
complete LLVM23.1.2 package stage and installed cross sysroot. All 16 query
groups then agreed with the installed executable on Zero 3W (A733). The
same target passed [shared C API and ORC execution](../../common-build-tools/cross/llvm-api-tests.md).
Mesa configuration and rendering remain separate consumer gates.

## Accepted DWP package revision

The accepted `llvm-23.1.2nb1` DWP repair changes the shared library while
preserving LLVM's configuration, component graph and ABI. The old sealed
helper correctly rejects the changed library. For this one recorded update,
`rebind-llvm-config-dwp.rb` checks the externally supplied original manifest
anchor, every unchanged input, and the exact package/library hashes published
in [the DWP acceptance](../../common-build-tools/cross/llvm-dwp-tests.md).
It retains the original evidence and writes a separate migration receipt.
The upstream metadata executable and query behavior remain unchanged.
Other library revisions require a new build or their own validated migration.

```sh
ruby rebind-llvm-config-dwp.rb /absolute/sealed-helper ORIGINAL_MANIFEST_SHA256 \
    /absolute/llvm-23.1.2nb1.tgz /absolute/new-helper
ruby ../tests/llvm-config-dwp.rb /absolute/sealed-helper \
    /absolute/llvm-23.1.2nb1.tgz /absolute/new-test-work
```

The regression queries real target metadata and rejects altered anchors,
packages, missing metadata, changed metadata/executable and runtime drift.

On 2026-10-12 the complete LLVM 23.1.3 package repeats all 16 query groups
on CM5 and passes 21 seal/query integrity checks. The original manifest anchor
and installed-library identity are recorded with the
[actual C API/ORC receipt](../../common-build-tools/cross/llvm-api-tests.md#cm5-llvm-2313-2026-10-12).
