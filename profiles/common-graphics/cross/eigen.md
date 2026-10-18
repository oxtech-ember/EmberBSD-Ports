# Common Eigen 5 provider

The common graphics profile updates the existing `math/eigen3` package to
[Eigen 5.0.1](https://gitlab.com/libeigen/eigen/-/releases/5.0.1).
It keeps `include/eigen3`, `Eigen3::Eigen` and `eigen3.pc` for KiCad and OCCT.
The GCC16 AArch64 package contains all 613 declared payload entries.
Installed target numerical and package lifecycle checks remain pending.

## Source and interfaces

The [source manifest](../sources.tsv) pins the original release archive:

- URL: `https://gitlab.com/libeigen/eigen/-/archive/5.0.1/eigen-5.0.1.tar.gz`
- Tag commit: `bc3b39870ecb690a623a3f49149a358b95c5781d`
- SHA256: `e9c326dc8c05cd1e044c71f30f1b2e34a6161a3b6ecf445d56b53ff1669e3dec`

The recipe retains pkgsrc attribution and upstream copyright notices.
It installs the five original `COPYING.*` texts without modification.
No Eigen implementation source patch is applied.
CMake receives an empty prerelease identifier, matching upstream's release
`Eigen/Version`; its default otherwise labels the installed header `dev`.
The installed version header is byte-identical to the release input.

Eigen 5 requires C++14. Its package and CMake project still use the `Eigen3`
name. Version checks now follow semantic versioning: an old request such as
`find_package(Eigen3 3.4 CONFIG)` rejects 5.0.1. Consumers accepting both
releases can use `find_package(Eigen3 3.3...<6 CONFIG REQUIRED)`.
Versionless discovery and `5.0.1 EXACT` also work. OCCT's versionless discovery
requires no compatibility alias or falsified version metadata.

The complete upstream header and unsupported-header installation is retained.
Upstream's BLAS, LAPACK, demos and testing options remain enabled.
The package includes `libeigen_blas.so`, `libeigen_lapack.so` and their two
static companion archives. The tested environment has no Fortran compiler;
upstream builds its normal C++ LAPACK subset. Fortran extensions and their
tests have not been accepted. Cross documentation follows upstream's normal
default; no target library or numerical feature is switched off by the recipe.

## Build and numerical checks

On 2026-10-18, native GCC 16.2.0 built the unchanged upstream defaults.
The native staged installation contains exactly 613 entries from the static
[package list](../recipes/math/eigen3/PLIST): 600 header/signature files,
four CMake/pkg-config files, four libraries and five license texts.
`eigen3.pc` reports 5.0.1 and the correct header directory, with no link flags
for the template interface. Exact and range-based CMake discovery pass;
the old minimum-version request fails as expected.

The ordinary GCC16 AArch64 pkgsrc build and package pass the normal package
list, permissions, PIE, RELRO, RPATH and work-reference checks. The actual
CMake system is `NetBSD/aarch64`, with `CMAKE_CROSSCOMPILING=TRUE`, using the
verified E34 application sysroot and registered GCC16 runtime package.
An earlier graph configured by the older common profile selected Linux;
it was rejected and preserved, then replaced by a fresh configuration using
the corrected common CMake target settings.

All 613 package entries match the target stage byte for byte.
Both shared libraries and every member of both static archives are AArch64.
Shared-library RPATH is `/usr/pkg/gcc16/lib:/usr/pkg/lib`; the binary runtime
requires the genuine GCC16 `libstdc++.so.7` and `libgcc_s.so.1` providers.
The accepted package SHA256 is
`152b31020518d793f78460bbaa93cd9d761eed76158ef8b0aeccd3129a8cfa3f`.

The [bounded numerical harness](../tests/eigen-upstream/CMakeLists.txt) builds
unchanged upstream sources against the installed `Eigen3::Eigen` target:

- `Tutorial_PartialLU_solve.cpp`: known solution `(-2, 1, 1)`, tolerance `1e-5`.
- `test/cholesky.cpp`, upstream split part 3.
- `test/eigensolver_selfadjoint.cpp`, upstream split part 7.
- `test/jacobisvd.cpp`, upstream split part 10.

All four native CTest cases pass. The three upstream test programs use
`r1 s1`; their own assertion harness remains active in optimized builds.
The same four programs cross-build with GCC16. This subset does not establish
completion of Eigen's full upstream suite or BLAS/LAPACK functional suites.

To repeat the native checks with a real installed provider:

```sh
cmake -S profiles/common-graphics/tests/eigen-upstream -B /absolute/new-build \
  -DEIGEN_UPSTREAM=/absolute/verified-eigen-5.0.1 \
  -DEigen3_DIR=/absolute/prefix/lib/cmake/eigen3 \
  -DCMAKE_CXX_COMPILER=/absolute/native-g++
cmake --build /absolute/new-build --parallel 1
ctest --test-dir /absolute/new-build --output-on-failure
```

For target compilation, use the same source and installed package interface
with the common GCC16 cross profile's actual compiler, sysroot and CMake target
settings. Run the resulting programs on the target; do not execute them as
native build-host tools.

The installed AArch64 package passes the same four numerical checks in the
coherent E34 EmberBSD VM. All 613 payload entries match the archive, including
file modes and symlink targets; `pkg_admin check` passes. The measured GCC16
runtime libraries match the SDK. Normal deletion removes all owned paths.
The compiled header consumers correctly remain executable after deletion;
that check establishes ownership, not a missing-library refusal. Normal
reinstallation restores all entries, and all four numerical checks pass again.
This subset does not establish runtime coverage of the companion BLAS/LAPACK
libraries or the complete upstream test suite.

## Analysis and memory boundary

Clang Static Analyzer 19.1.7 reports no diagnostics for all four native and
all four AArch64 translation units using their real flags and target headers.
Target analysis uses Clang's genuine NEON intrinsic headers and the installed
GCC16 C++ headers. All GCC16 preprocessing steps succeed.
Cppcheck 2.22 cannot complete the same analysis: its native parser rejects a
valid GCC16 `<array>` declaration. Target parsing fails in actual NetBSD
`math.h` and `sys/endian.h`. Its experimental native Clang-AST route also
fails on an AST location. These are analysis limitations, not clean results.
No replacement headers or diagnostic suppression are used.

Strict native Valgrind Memcheck 3.24 passes the known-solution example with
zero errors and all heap allocations freed. Each of the three unchanged
upstream test executables exits 99 under the same strict policy because
`EigenTest::get_registered_tests()` retains 32 bytes in two registry allocations.
They report no invalid accesses, uninitialized uses or lost allocations.
The registry is not patched or suppressed to report a clean memory result.
Target memory instrumentation remains separate.

Full KiCad configuration, its Eigen consumers and the complete CAD workflows
remain independent acceptance gates.
