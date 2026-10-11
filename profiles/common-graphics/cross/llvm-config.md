# Run target LLVM metadata queries on the build host

Mesa's cross configuration needs an executable on macOS that describes the
NetBSD LLVM package. The existing native generator build's `llvm-config`
describes Darwin and must not be used as target metadata. The target executable
cannot run directly on macOS.

`build-llvm-config.rb` compiles the pinned upstream LLVM 23.1.2
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
directories must have matching LLVM 23.1.2 sources and completed generated
metadata. Keep the input trees unchanged through building, acceptance and
sealing. The sealed tool then permits build-tree cleanup while checking the
installed package on every query. Use a fresh output directory.
The helper currently accepts the canonical
NetBSD/AArch64, shared LLVM, RTTI and `/usr/pkg` layout with a macOS native
compiler. Whitespace in paths and different native system-library closures
are rejected rather than guessed.

Target `BuildVariables.inc`, `LibraryDependencies.inc` and
`ExtensionDependencies.inc` provide the actual component graph and options.
Target generated configuration supplies both triples; the checked version and
assertion setting also come from that configuration. All native platform and
ABI headers remain native. Report-only substitutions occur after those headers;
target configuration is never substituted into the Support library interfaces.
The source hash and replacement contexts are checked before compilation.

An explicit target prefix replaces upstream's executable-location detection.
For an installed layout it points to the real staged `/usr/pkg` directory;
all library availability checks remain upstream code. A target build directory
can be used for early metadata-only inspection, but it is not the final staged
prefix: this LLVM build creates the `libLLVM-23.so` alias during installation.
Missing shared libraries therefore produce a real failure until staging is
complete. No placeholder library or fake success response is created.
For staged mode the helper also checks matching generated public configuration
headers, the AArch64 ELF header and shared-library identity against this target
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
The receipt preserves both original and mapped flags, and the supplied sysroot
must match the target configuration.

`receipt.json`, `compile.command` and `compile.log` record the inputs and build.
`inputs.sha256` covers the source, original generated metadata/configuration,
compiler, native archives, actual non-system header dependencies and resulting
tool. Input changes during compilation fail. The `bin/llvm-config` launcher
checks the receipt before every invocation,
then executes the real compiled program; it does not parse query options or
synthesize results. Changed inputs require a fresh tool build.

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
sh record-llvm-config.sh /absolute/target-prefix/bin/llvm-config \
    /absolute/new-reference
```

Transfer the reference directory back with a verified archive hash. On macOS:

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
