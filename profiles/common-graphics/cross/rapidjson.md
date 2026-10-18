# RapidJSON with GCC16

The common `textproc/rapidjson` provider uses upstream commit
`24b5e7a8b27f42fa16b96fc70aade9106cf7102f`, dated 2025-02-05.
It is the current upstream master snapshot checked on 2026-10-18.
Upstream's latest tagged release remains 1.1.0. The package keeps the canonical
snapshot version `1.1.0.20250205` and adds revision `nb1`.
The [source manifest](../sources.tsv) pins the actual archive and SHA256.
Upstream copyright and license files remain intact. The repairs are AI-assisted.

The recipe builds all examples and both upstream test programs with GCC16,
C++17 and genuine installed GoogleTest 1.18. It keeps strict warnings, including
`-Werror`. The upstream instrumentation option is OFF, so cross builds do not
inherit `-march=native`. The existing package exclusion of generated Doxygen
documentation remains; installed headers, examples and readme remain present.
This package boundary is not a claim of full upstream documentation generation.

The source changes preserve the public header interfaces and object layouts:

- Pointer append copies each external token's actual name, then adds its own
  terminator. An external token array has no contiguous owned name buffer.
- A shared user-buffer pool reuses an allocator created lazily by another copy.
  Its final owner releases that allocator once.
- Pool destruction captures the exact owned shared-buffer pointer before
  releasing extra chunks. A caller's buffer remains borrowed.
- The optional installed GoogleTest route requires a real package. Default
  upstream source-provider discovery remains available.
- Modern typed-suite registration retains its older GoogleTest fallback.
  Seven finite floating-point checks use zero tolerance. Wide-stream tests use
  the actual EOF-capable traits type on both signed and unsigned platforms.

The recipe selects the upstream relative `CMAKE_INSTALL_DIR` option.
CMake then derives the imported include directory from the installed config.
This permits genuine staged and sysroot consumers without rewriting headers
or importing a host prefix. Patch backup headers are excluded from the package.

## Reproduce

Build the normal native and target packages from a composed common profile.
Use the ordinary `package` target. Run the native package's `test` target.
Keep the complete upstream test data directory. Cross compilation does not
execute the target test programs.

The finite source regressions need native GCC16, installed GoogleTest and
strict Valgrind Memcheck. They verify the pinned source archive and apply
every public patch with zero fuzz:

```sh
ruby profiles/common-graphics/tests/rapidjson/check-source.rb \
  "$RAPIDJSON_ARCHIVE" "$NATIVE_GXX" "$GTEST_PREFIX" "$NEW_WORK"
```

The original pointer operation must report an invalid read at address zero.
The original shared-pool lifecycle must fail its live-owner assertions and
report the genuine one-byte allocator leak. Both repaired cases must pass
with no errors or live allocations. Both source variants use `-O0` for this
matched memory comparison. The repaired variants also pass separate `-O2`
controls. The optimized original package build retains its actual GCC16
ownership diagnostic; the check does not suppress that diagnostic.

Build the independent installed-header consumer with a genuine package prefix:

```sh
cmake -S profiles/common-graphics/tests/rapidjson -B "$NEW_BUILD" \
  -DRAPIDJSON_PREFIX="$INSTALLED_PREFIX" -DCMAKE_CXX_COMPILER="$NATIVE_GXX"
cmake --build "$NEW_BUILD"
ctest --test-dir "$NEW_BUILD" --output-on-failure
```

Use the normal AArch64 GCC16 CMake toolchain for the target consumer.
Run that executable in EmberBSD with the accepted runtime closure.
The fixture checks external-token ownership, shared stack-pool growth,
DOM values, UTF-8 decoding and schema acceptance/rejection.
Its CMake check rejects imported headers outside the supplied prefix.

## Validation boundary

Both ordinary GCC16 packages pass their complete static packing-list checks:
66 entries each, with 38 byte-identical installed headers. Their installed
CMake targets derive the actual prefix. The native package's complete CTest
run passes all three entries: performance, unit and upstream Valgrind tests.
An additional strict Memcheck run executes all 471 unit tests, including SIMD,
with no filters or suppression file: zero errors and zero live allocations.

The pinned source regressions and independent installed native consumer also
pass strict Memcheck. The consumer cross-links as AArch64 with the genuine
GCC16 runtime and only `/usr/pkg/gcc16/lib` in its runtime search path.
Installed target execution and package lifecycle checks remain pending.
This checkpoint does not accept OCCT or KiCad.

Clang 19 analysis of the actual pointer and allocator test translation units
uses the real GCC16 headers. Document move tests retain eleven baseline
findings, including their deliberate moved-from API checks; no clean whole-module
claim is made. Cppcheck 2.22 cannot parse GCC16's preprocessed `<array>` at line 75.
That parser failure remains recorded. No diagnostics or test assertions are disabled.
