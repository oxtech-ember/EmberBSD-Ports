# SPIRV-Tools source and test selection

The common recipe uses SPIRV-Tools v2026.4, commit
`ef96ed763b43b59b33b31b362f09a02b729fa1c9`. The shared Headers recipe uses
the stable vulkan-sdk-1.4.363.0 tag at
`496543121ce6419f23d6fa5d7194ba66c36212d2`, also selected by Tools' DEPS.
The recipes select their component versions independently of other Vulkan
SDK packages. `distinfo` records the original archive hashes.

`patch-source_link_linker.cpp` keeps declarations before definitions when
the linker combines input modules. The existing
[real-tool consumer](../../../../probes/a733-accelerators/host-tools/check-spirv-link-order.py)
checks both module orders, an import-only module, resolved imports and plain
definitions. Run it with newly built tools. Source patch checks do not replace
linker and validator execution.

`patch-installed-gtest` adds `SPIRV_USE_INSTALLED_GTEST`, default OFF.
The recipe enables it, keeps `SPIRV_SKIP_TESTS=OFF`, and selects the common
GoogleTest 1.18.0 provider as a build dependency. Root-scope discovery and
compatibility aliases make all four GoogleTest/Mock targets visible to sibling
test directories. Missing providers or targets are fatal. The installed mode
does not add vendored targets or assign IDE-folder properties to aliases.
The default preserves the upstream vendored path.

Compiler wrappers can add a package include directory during compiler
detection. CMake then treats a matching imported SYSTEM include as implicit
and omits its flag. The patch restores `-isystem` only on matching GoogleTest
imported targets for GNU and Clang-family compilers. The metadata check tests
both matching and non-matching directories; the matching path contains spaces.

The same patch adds the independent `SPIRV_USE_INSTALLED_EFFCEE` option,
default OFF. The recipe enables it and selects common Effcee 1.2026.0 and
RE2 2025-11-05 as build dependencies. These providers are required by the
enabled unit suite. Root-scope aliases expose both targets to sibling tests.
Missing providers or targets are fatal. The installed path does not add
vendored Effcee or RE2 sources.

```sh
python3 -B tests/installed-gtest.py --cmake /absolute/cmake \
    --archive /absolute/SPIRV-Tools-2026.4.tar.gz \
    --patch /absolute/patch --work-parent /absolute/private-test-parent
```

The finite check verifies archive and patch hashes and applies the actual
patch with zero fuzz. It configures the patched selection, upstream vendor
branch and sibling test guard with real CMake and `LANGUAGES NONE`. Twelve
configure checks include the SYSTEM-include collision and its non-collision
control.
GoogleTest, Effcee and RE2 package and vendor fixtures provide only target metadata. They
contain no implementation. The check covers successful installed selection,
missing providers/targets, rejected test skipping, the unchanged default,
independent Effcee test-skip refusal, and causal scope/alias-property faults. It neither selects a compiler nor
builds C or C++ objects.

Run the full native build and `make test` with the actual common GoogleTest,
Effcee, RE2 and Abseil packages before package acceptance. This configure check
does not qualify their binaries, the full upstream unit suite, installed
libraries, or package lifecycle.

The native test phase sets `LD_LIBRARY_PATH` and `DYLD_LIBRARY_PATH`, as in
the common RE2 recipe, to find `libSPIRV-Tools-shared` in the CMake build's
`source` directory. pkgsrc does not define `SHLIB_PATH_VAR`. The shared
C-interface unit test needs this library before package installation.
This environment applies only to `make test`. Installed-library acceptance
uses the normal loader environment. Package RPATH rules are unchanged.

```sh
python3 -B tests/native-test-env.py --bmake /absolute/bmake \
    --pkgsrc-source /absolute/prepared-pkgsrc \
    --work-parent /absolute/private-test-parent
```

This metadata check loads the real prepared pkgsrc `bsd.prefs.mk`, including
its NetBSD platform rules, with explicit native platform facts and an empty
private `MAKECONF`. It checks both recipes' native environment and cross-mode
guard. The cross guard is selected after platform discovery; this does not
qualify the full cross dependency graph. A causal case restores the previous
undefined-variable expression and must fail. External dependency includes are
outside this check. It does not build or execute target programs.

The upstream copyright test walks the source tree. pkgsrc places generated
Khronos headers under `cmake-pkgsrc-build`, which is not matched by the
upstream `build*` exclusion. The local patch excludes that exact directory.
The source-only regression applies the patch to the verified source archive.
It checks the upstream failure and patched pass for generated headers, then
confirms that source files and similarly named directories remain checked.

```sh
python3 -B tests/copyright-build-dir.py \
    --archive /absolute/SPIRV-Tools-2026.4.tar.gz \
    --patch /absolute/patch-check-copyright-cmake-pkgsrc-build \
    --patch-tool /absolute/patch \
    --work-parent /absolute/private-test-parent
```
