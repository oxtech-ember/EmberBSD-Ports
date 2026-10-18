# JBIG-KIT 2.2 common provider

The common graphics profile updates the existing `graphics/jbigkit` provider.
[The publisher](https://www.cl.cam.ac.uk/~mgk25/jbigkit/) released 2.2 on 2026-10-09.
The upstream tag `v2.2` points to `802dc4c558f36b3325dac329bf3beb291962baa3`.
The [publisher archive](https://www.cl.cam.ac.uk/~mgk25/jbigkit/download/jbigkit-2.2.tar.gz)
has SHA256 `3302109c93b7befbffa3cfe8bceb4355f19dea0ee7dcb5f33710b1648bf6645c`.
This is a locally calculated hash of the HTTPS download, not a signature claim.
The upstream GPLv2 license and authorship remain unchanged.
The recipe and test adaptation disclose AI assistance.

## Package and ABI

The recipe retains both shared and static libraries, three public headers,
four PBM conversion tools, manual pages and library documentation.
The static packing list is the existing pkgsrc contract.
Ordinary Libtool installation supplies the platform-specific library files.
All three upstream core tests remain enabled, including the new `tstjoint`.
The upstream PBM round-trip checks remain enabled too.

SONAMEs remain `libjbig.so.2` and `libjbig85.so.2`.
This compatibility statement applies to the canonical **patched** 2.1nb1 provider.
That recipe already backported the decoder `maxmem` field and its safety fix.
Both public headers preprocess identically between that provider and 2.2,
under native GCC16 and the actual AArch64 GCC16/sysroot configuration.
Comments, version macros and a corrected option macro spelling change.
Raw upstream 2.1 lacks that field and is not ABI-compatible.
The API and ABI dependency floors require 2.2, so consumers rebuild normally.
No alternate provider or old-library alias is introduced.

The pkgsrc Libtool patches now preserve all upstream 2.2 targets.
Required header paths and original warning/ANSI flags appear in compile rules.
Caller `CPPFLAGS`, `CFLAGS` and `LDFLAGS` remain active.
This matters because pkgsrc invokes GNU make with `-e`.
The initial appended-variable form failed the real package build;
the final explicit include rule passes without suppressing diagnostics.

## Test ownership repair

The codec C sources are byte-identical to upstream 2.2.
The test-only patch frees four main-owned buffers on normal and image-export exits.
The T.85 test also frees its three-row caller-owned decoder buffer.
It does so after both decoder feeding modes finish.
All assertions, expected encoded lengths, image comparisons and failure statuses remain.
Fatal allocation or architecture-error exits are outside this cleanup claim.

Before repair, strict native Memcheck fails `tstcodec` with 886,283 retained bytes
and `tstcodec85` with 888,488 retained bytes.
Both image-export branches also fail the same strict check.
After the isolated cleanup patch, all five core/export invocations pass
with zero errors, zero live blocks and no suppressions.
The exported reference images remain byte-identical.

## Reproduce the checks

Prepare the normal `common-graphics` export and configure the common GCC16 profile.
Build `graphics/jbigkit` with `bmake package`; use `bmake test` for native tests.
Cross builds compile the same test programs but do not execute target code on the host.
Do not substitute host test results for EmberBSD execution.

The [installed-test adapter](../tests/jbigkit/CMakeLists.txt) rebuilds the three
upstream test programs against an installed or staged prefix.
It copies only test C files into its build directory.
Their quoted includes therefore use installed headers, not source-tree headers.
Canonical file checks reject headers or libraries outside the selected prefix.
The fixture rejects static-only library selections, including cached overrides.

```sh
cmake -S profiles/common-graphics/tests/jbigkit -B /absolute/new-test-build \
    -DCMAKE_C_COMPILER=/absolute/gcc16 \
    -DJBIG_SOURCE=/absolute/patched-jbigkit-2.2 \
    -DJBIG_PREFIX=/absolute/installed-prefix
cmake --build /absolute/new-test-build
ctest --test-dir /absolute/new-test-build --output-on-failure
valgrind --error-exitcode=99 --leak-check=full --show-leak-kinds=all \
    --errors-for-leak-kinds=all --track-origins=yes \
    /absolute/new-test-build/tstcodec
```

Repeat the memory command for `tstcodec85` and `tstjoint`.
For cross builds, supply the common GCC16 toolchain and run the resulting
programs in EmberBSD with the matching installed libraries.
The ordinary package retains all four installed tools for separate image checks.

## Validation boundary

Native and AArch64 GCC16 ordinary packages pass packing-list, permission,
RELRO, runtime-path and work-reference checks.
The target package also passes the PIE check.
Native upstream core and PBM suites pass through the ordinary recipe.
All three installed-library core tests pass, including strict native Memcheck.
The target installed-library test executables cross-link to SONAME 2.
All four installed image tools preserve the known PBM pixels and reference encoding.
Their strict Memcheck runs fail on inherited exit-owned buffers or open streams:
`jbgtopbm` retains 8,472 bytes, `pbmtojbg` 513,696 bytes,
`pbmtojbg85` 1,120 bytes and `jbgtopbm85` 11,736 bytes.
The unchanged upstream `jbgtopbm` reproduces the exact 8,472-byte failure.
These CLI lifetime findings remain owned by upstream JBIG-KIT; they are not
covered by the separate test-program cleanup patch or described as memory-clean.
Target execution, package lifecycle, TIFF integration and the full KiCad workflow
remain separate acceptance checks.

Cppcheck 2.22 uses actual GCC16 C90 macros and header search paths for all ten C files.
Its 46 style and six warning findings match the pristine 2.2 baseline.
Clang findings also match that baseline after source-root normalization.
Clang 19 path analysis reports inherited codec allocation/shift paths,
uninitialized-value paths, PBM stream-state paths and dead stores.
These are upstream JBIG-KIT findings; the codec and tool C files are unchanged.
They require separate input/path diagnosis and are not reported as clean analysis.
The two touched test modules have no Clang path finding.
GCC16 `-fanalyzer` reports only the existing test-label `sprintf` range warning;
the actual loop has four layer values and three orders, so its counter is 1 through 12.
No warning category or analyzer finding is suppressed.
