# ICU runtime and development-host SDK

The canonical `textproc/icu` recipe retains ICU 78.3, its complete data and
all installed features. It comes from pkgsrc commit
`fff4deb639a1a640476203c80f752fb77b6cb14b`, with the existing common cross
host-tool and installed-metadata repairs. The recipe retains all 18 actual
pkgsrc patches and their hashes. The lifetime repair below is an additional
EmberBSD patch. A separate test-only repair below preserves the explicit
native Python input. The imported distinfo removes one stale
checksum for `patch-i18n_measunit_extra.cpp`, which that commit does not contain.
The upstream source archive hashes are unchanged.

All complete common profiles, including `common-media` and `plasma-mobile`,
export this same recipe and its companion `textproc/icu-devel`.

| Build | Package | Installed role |
|---|---|---|
| Native | `icu-78.3nb2` | Complete ordinary package, including native generators |
| NetBSD cross | `icu-78.3nb3` | Versioned shared libraries, `icuinfo`, `uconv`, `derb`, their manuals and license |
| NetBSD cross | `icu-devel-78.3nb3` | Headers, static libraries, linker symlinks, generators, generator manuals and build metadata |

The SDK depends on exactly `icu-78.3nb3`. Consumers retain the ordinary ICU
runtime dependency. Cross buildlinks add `icu-devel` as a build-only dependency
and expose its complete development interface. Keep the SDK in the host
sysroot. Install the runtime package in the target image. The cross-only SDK
recipe rejects native packaging. Both AArch64 and amd64 have metadata support.

Both package roles build and install the full upstream source. They then
select an exhaustive partition from static PLISTs with `LIBTOOLIZE_PLIST=no`.
The full PLIST matches all 274 files and links from the complete GCC16
AArch64 install stage. Runtime owns 18 entries; SDK owns 256. No `.la` files
occur in that stage. All six shared-library families remain available.
The SDK owns the `lib/icu/current` directory link and the metadata it exposes.

Set `EMBERBSD_CROSS_BUILD_PYTHON` to Python 3.15 and set
`EMBERBSD_SDK_SOURCE` to an explicit SDK source tree. The SDK must provide
library API 1 and `emberbsd_sdk.stage.STAGE_PARTITION_API = 1`, including
directory-link support. Ports parses the generated package PLISTs and checks
ICU runtime policy. The shared SDK validates complete ownership, dependencies
and links before it removes any unselected file. An SDK link may refer to the
exact runtime dependency. Runtime links cannot depend on the SDK.

Run the policy regression on a complete installed payload before packaging:

```sh
python3.15 -B profiles/common-build-tools/tests/icu-stage-policy.py \
    --sdk-source /absolute/EmberBSD-SDK \
    --full-stage /absolute/complete-stage/usr/pkg \
    --mh-name mh-bsd-gcc --work /absolute/new-policy-check
```

The regression copies the actual declared files. It checks both partitions,
their unchanged union and seven refusals before pruning: unknown role, unlisted
file, duplicate entry, leaked generator, missing file, missing SDK feature and
a boolean in place of the integer feature version.
The previous native nb1 and AArch64 nb2 payload checks pass. Native metadata
retains the complete package; cross metadata selects the two roles and exact dependency.
Those complete GCC16 AArch64 runtime and SDK packages also pass the ordinary
package-list, permission, PIE, RELRO, runtime-path and work-reference gates.
All 18 runtime and 256 SDK entries match their installed sysroot bytes, modes,
links and registration. The native package retains the complete payload.
These installed-package results qualify the preceding revisions, before the
lifetime repair below.

Build resource fixtures with the matching native package on the development
host. Then build the consumer with the target SDK:

```sh
python3.15 -B profiles/common-build-tools/tests/icu-fixtures.py \
    --sdk-source /absolute/EmberBSD-SDK \
    --native-prefix /absolute/native-prefix --work /absolute/new-fixtures
sh profiles/common-build-tools/tests/icu-cross-consumer.sh \
    /absolute/cross-tools /absolute/sysroot /absolute/new-fixtures \
    /absolute/new-consumer
```

Copy the consumer directory to EmberBSD and run `sh run.sh .`. The target
runner requires the runtime package and rejects installed ICU SDK files and
generators. It checks conversion, collation and consumption of host-generated
resources. Native `genrb` and `pkgdata` fixture generation passes. The native
installed API consumer passes strict Memcheck with zero errors and zero live
allocations. This is a bounded API check, not the full upstream suite.

The preceding AArch64 nb2 runtime passes the runner in EmberBSD. UTF-8/UTF-16LE
conversion preserves its bytes, collation has the expected order, and the
host-generated resource returns 42. Its loader uses the common GCC16
`libstdc++.so.7` and `libgcc_s.so.1`. All 18 runtime file bytes and link targets
match the archive. The guest contains no ICU SDK or generators.
The target C consumer also passes with GCC16 UBSan traps. The packaged
provider remains uninstrumented; this does not replace whole-library memory tests.
Normal deletion makes the unchanged consumer fail to find `libicui18n.so.78`.
Normal reinstallation restores all checks and package integrity.
The [acceptance receipt](../tests/icu-installed-aarch64.json) records package
and consumer identities. amd64 execution and complete upstream tests remain
separate gates.

## Builder constructor lifetime

The original `DataBuilderCollationIterator` passes the address of its
`builderData` member to the `CollationIterator` base constructor. That
constructor reads `d->trie` before the member constructor starts. The later
member initialization does not make this read valid.

The repair retains the existing two-argument constructor. It delegates to a
protected constructor with an explicit initial trie. The builder passes
`nullptr`; this path stores the member address without dereferencing it.
Normal runtime iterators still read the trie from their constructed data.
No field or object layout changes. Native nb2 and target nb3 contain this
repair. The previous package acceptance does not qualify the new revisions.

Run the actual-source regression on the development host:

```sh
python3.15 -B profiles/common-build-tools/tests/icu-builder-lifetime.py \
    --sdk-source /absolute/EmberBSD-SDK \
    --archive /absolute/distfiles/icu4c-78.3-sources.tgz \
    --native-prefix /absolute/native-prefix --native-cxx /usr/bin/c++ \
    --cross-tools /absolute/gcc16-toolchain/bin --sysroot /absolute/sysroot \
    --patch /absolute/nbpatch --cppcheck /absolute/cppcheck \
    --clang /absolute/clang++ --memory asan-no-leaks --work /absolute/new-work
```

The controller verifies the source archive and every patch checksum. It
extracts the pinned baseline and applies the repair to an independent copy.
The native fixture compiles the complete real builder translation unit and
links the matching full native ICU static libraries. Its zero-filled control
passes before the repair. Four nonzero storage patterns expose the cached
unconstructed trie. The repaired constructor passes all five patterns.
Five Unicode strings compare builder collation elements with the real runtime
iterator. The fixture uses NFD input, as the upstream `CollationBuilder` does.
It also checks the existing constructor's trie and the three object sizes.
The controller requires the actual baseline GCC16 translation unit to fail
with `-Werror=uninitialized`; the repaired unit must compile for AArch64.
The [component receipt](../tests/icu-builder-lifetime.json) records the source
hashes, 16 executed cases and unchanged object sizes.

Cppcheck receives the actual GCC16-preprocessed target translation unit and
the LP64 data model and unsigned plain `char`, as selected by the common
AArch64 GCC16 predefined macros. Clang Static Analyzer uses the same source, implementation
macros, target headers and AArch64 NetBSD target, without producing target
objects. All diagnostics and command statuses remain in the result directory;
the controller does not turn unresolved analyzer findings into a clean result.
Cppcheck 2.22.0 cannot parse the complete GCC16 system-header input: it reports
an unmatched brace in `stdio.h`. Its Clang AST importer also fails on a built-in
source location with both Clang 21 and 23. A separate source pass uses the real
ICU headers, explicit target macros and standard-library models. That pass
compares findings without suppressions. System-header coverage remains a gap.
Clang Static Analyzer 23 removes the lifetime warning. Two previous null-base
paths remain in `addCE32()` and `getJamoCE32s()`. The common ICU port owns their
remaining contract review. They are not new findings from this repair.

On Darwin AArch64, Memcheck and LeakSanitizer are unavailable. The explicit
`asan-no-leaks` mode checks access and undefined behavior in the fixture and
builder translation unit. Linked ICU archives remain uninstrumented. This is
a bounded component regression; it does not qualify whole-library memory
behavior, package installation or a graphical session.

## Upstream test interpreter

The bootstrap recipe leaves configured Python empty to avoid a dependency
cycle. The upstream data test originally substituted that empty value into
its command, so `bmake test` tried to execute `-m`. The test-only repair adds
`ICU_TEST_PYTHON`, with the unchanged configured value as its default.
`TEST_MAKE_FLAGS` passes the explicit `EMBERBSD_CROSS_BUILD_PYTHON` input to
all recursive test make processes. Use the common Python 3.15 interpreter.
The normal source build still uses the prebuilt ICU data archive. No runtime
dependency or data test is removed.
