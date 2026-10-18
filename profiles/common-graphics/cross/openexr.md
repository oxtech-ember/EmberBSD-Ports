# OpenEXR and OpenJPH common providers

The update keeps `graphics/openexr` as the single OpenEXR provider.
OpenEXR 3.5.2 is the official stable release published on 2026-10-03:
[tag and release](https://github.com/AcademySoftwareFoundation/openexr/releases/tag/v3.5.2).
Its source commit is `69b2604fc76e370615438bdc8d2cd95b9349c12e`.
The archive SHA256 is
`85a291b9b8563fabef1aa3f6e912d744ce1d4b9fd5a8f978eda194cd51b15ae9`.
The upstream BSD-3-Clause license remains unchanged.
New EmberBSD source and checks disclose AI assistance.

The recipe keeps shared libraries, eleven installed tools, examples and
threading. The default-off Python binding, developer-tool installation,
TBB and fuzzing options stay at their upstream defaults. Library and CLI
checks are enabled. CLI checks use the common native Python 3.15 interpreter;
Python is not added to the target library dependency closure.

OpenEXR 3.5 changes its ABI to the `3_5` namespace and SONAME revision 34.
The buildlink API and ABI floors require 3.5.2. Consumers must rebuild;
no old-SONAME alias is supplied. The pinned pkgsrc tree has OpenEXR consumers
across image processing, visualization and CAD. FreeImage 3.19.25 uses the
public RGBA and general image APIs with the shared Imath half type.
Consumer discovery is not a claim that every downstream application passes.

## External libraries

The common recipe selects Imath 3.2.3, libdeflate 1.26,
OpenJPH 0.32.0 and Zstandard 1.5.7. Imath retains its existing provider and
version. The OpenJPH update replaces `graphics/OpenJPH`; OpenEXR is its only
direct consumer in the pinned tree. OpenJPH retains its shared library,
compress/expand tools and TIFF input/output. Its SONAME becomes `0.32`.
TIFF discovery is required with CMake's standard required-package switch.

OpenJPH now selects SIMD from the actual target architecture. Its old
`OJPH_DISABLE_INTEL_SIMD` option aliases `OJPH_DISABLE_SIMD`, which disables
all architecture implementations. The old non-x86 override is removed.
No default-off stream server, fuzzer or extra test dependency is added.

The opt-in `OPENEXR_REQUIRE_SYSTEM_LIBS` source option rejects each absent
external provider before bundled code or Imath FetchContent can be selected.
Its upstream default is OFF; the common recipe sets it ON. Discovery still
uses genuine CMake or pkg-config metadata. OpenEXR 3.5.2's pkg-config fallback
requests exactly OpenJPH 0.32.0; this update does not claim compatibility with
arbitrary later pkg-config-only OpenJPH providers.

The old pkgsrc test exclusion referenced
[issue 1594](https://github.com/AcademySoftwareFoundation/openexr/issues/1594).
Upstream closed it in 2024. The current test header already includes the
correct NetBSD `sys/types.h` and `machine/bswap.h`. An actual AArch64 GCC16
compile of that header with warnings as errors passes. The recipe no longer
disables the test suite for this repaired issue.

## Release-build test assertions

Four upstream test units did not clear `NDEBUG` before including assertion
headers. The source patch uses the same early `undef` convention as the other
tests. Release optimization and every library/tool compilation flag remain.
The actual native preprocessed units change from zero active assertion calls
to 1, 2, 12 and 1 calls. The upstream `random_float(0)` helper accepts an invalid
empty range without the repair; the corrected helper rejects it by assertion.
This is a test-only repair; codec and application source remains unchanged.

## Test temporary files

The Unix test entry points honor a nonempty `TMPDIR`. Unset and empty values
retain the platform default. Windows keeps its existing `GetTempPathA` path.
The tests keep their unique directory names and normal cleanup. The nested
bad-attribute writer uses the same test directory. An invalid `TMPDIR` fails;
the tests do not silently select another directory.

Two fatal directory errors release their owned strings before the existing
`exit(1)`. The [directory contract](../tests/openexr/check-tempdir.rb) exercises
three actual test executables with invalid, valid and trailing-slash paths.
The [failure-memory contract](../tests/openexr/check-tempdir-exit.rb) recompiles
each genuine upstream entry with a renamed `main` and links its other actual
objects. A small entry wrapper sets the invalid client path after Memcheck
starts. This preserves Valgrind's own valid temporary directory.

```sh
ruby profiles/common-graphics/tests/openexr/check-tempdir.rb \
    /absolute/original-build /absolute/patched-build /absolute/new-output
ruby profiles/common-graphics/tests/openexr/check-tempdir-exit.rb \
    /absolute/pkgsrc/graphics/openexr /absolute/native-mk.conf \
    /absolute/patched-build /absolute/new-memory-output
```

Use the ordinary native build environment and installed library search path.
`BMAKE` and `MEMCHECK` can select their real executables. The memory helper
requires Linux GCC 16.2 and genuine CMake compile and link records.

## Installed API check

The [public consumer](../tests/openexr/roundtrip.cpp) links only the installed
OpenEXR CMake package. It writes and reads 2,048 deterministic RGBA pixels per
codec, including negative values and values above one. It requires exact half
bits with NONE, RLE, ZIPS, ZIP, PIZ, HTJ2K32, HTJ2K256 and ZSTD compression.
It also checks exact float-channel values through Zstandard. A binary-exact
offset makes this float fixture exceed half precision. The library
version, channels, compression metadata and image bounds are checked.
Lossy compression has separate upstream tests; this consumer does not treat
lossy output as bit-exact.

```sh
cmake -S profiles/common-graphics/tests/openexr -B /absolute/new-consumer \
    -DCMAKE_PREFIX_PATH=/absolute/installed-prefix
cmake --build /absolute/new-consumer
mkdir /absolute/new-empty-output
/absolute/new-consumer/openexr-roundtrip /absolute/new-empty-output
```

Use the common GCC16 CMake toolchain when cross-compiling. Execute the target
consumer in EmberBSD with the installed dependency closure. Native execution
and target execution are separate results. Full CLI CTest runs also need their
upstream test images and Python scripts on the same execution side as the tools.

## Current validation boundary

Source archives, dependency requirements and the repaired byte-swap header
are checked. The opt-in system-provider source guards have independent review.
Unchanged Imath 3.2.3 builds through ordinary pkgsrc with native GCC16 and
cross GCC16 for AArch64. Both packages pass the normal packing-list, permission,
runtime-path and work-reference checks. All 38 native upstream tests pass
against the staged package library. Its half C test passes strict Memcheck.
The target library has SONAME `libImath-3_2.so.30` and runtime paths
`/usr/pkg/gcc16/lib:/usr/pkg/lib`. All 38 upstream tests also pass in the
EmberBSD AArch64 VM with the staged package library and verified GCC16 runtime.
The separate private diagnostic Imath build also passes all 38 native tests.
The unchanged libdeflate 1.26 native and target packages pass normal package
checks. Target compression and decompression preserve a known binary payload;
native-to-target and target-to-host gzip compatibility checks also pass.

OpenJPH 0.32.0 passes the ordinary native GCC16 package checks. Its static
packing list matches all 20 actual installed files. Four exact grayscale/RGB
8/16-bit image round trips and TIFF read/write checks pass. All 12 installed
codec-tool invocations pass strict Memcheck with zero errors and live blocks.
The upstream default-off GoogleTest/codestream suite is not enabled or claimed.
The ordinary AArch64 package also passes all package checks with the same
20-entry packing list. Its tools and library are actual AArch64 ELF files
with target runtime paths. Target codec execution remains pending.

The actual OpenEXR configure accepts all four genuine external providers.
Four controls remove one provider's discovery metadata at a time. Each fails
with the intended diagnostic before an internal/download fallback is selected.
Ordinary GCC16 native and AArch64 OpenEXR packages pass the normal package
checks. Their static packing lists match all 208 payload entries. The target
contains 16 regular AArch64 ELF files, target runtime paths and relocatable
CMake/pkg-config metadata. The installed API consumer passes all eight half
codecs and the float-channel check natively. Strict Memcheck reports zero
errors and zero live blocks. The same consumer cross-compiles and links
against the staged target package; target execution remains pending.

The installed consumer passes GCC16 path analysis and Clang19 analysis with
the actual GCC16 standard-library headers. Cppcheck 2.22 cannot parse the
actual preprocessed GCC16 `array` header. This is a recorded analyzer limit,
not a clean Cppcheck result. The four changed temporary-file test modules
also pass GCC16 and Clang19 path analysis before and after the patch.
Their Cppcheck attempts stop in the real math or Linux system headers.
Three actual temporary-directory entry checks
pass on valid paths. Their explicit failure paths return status 1 with zero
Memcheck errors and live blocks. The complete 147-test native CTest run
remains pending; no full-suite or target memory result is claimed.

The complete OCCT library and genuine STEP geometry check remain separate work.
