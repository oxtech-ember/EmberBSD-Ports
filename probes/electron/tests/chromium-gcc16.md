# Chromium GCC16 portability checks

Apply the carried patches after the exact Electron DEPS sources and the NetBSD
overlay. The NASM follow-up requires pkgsrc's
`patch-third__party_nasm_BUILD.gn`. That patch derives from the OpenBSD Chromium
and pkgsrc Qt WebEngine adaptations. The follow-up preserves its Linux host
probe and selects the macOS SDK headers on a Mac host.

The base patches retain `-Werror`. Invalid enum paths call `NOTREACHED()` after
the exhaustive switch. The switch has no default, so new enum cases still
receive compiler diagnostics. Clang availability pragmas remain Clang-only.
The mkdir condition uses a boolean value for its boolean fallback.

The Glib controller uses a weak pointer across the write callback. This keeps
the outer dispatch safe when a nested callback deletes or replaces the
controller. Five tests in `message_pump_glib_unittest.cc` cover persistent
read/write, deletion on either callback, nested deletion, and replacement at
the same address. The replacement test detects a stale notification without
relying on allocator address reuse or ASan.

The placeholder tests use reordered and repeated parameters for both character
widths. They check the formatted string and stable parameter offsets. The
WriteInto tests retain copying, zero padding, string length, empty-buffer, and
copy independence assertions.

The libc++ pair patch includes an incomplete-element compile regression and
ordinary pair assignment controls. The allocation patch extends
`allocate.size.pass.cpp` with counts above the byte object-size limit. Its
allocation guard requires rejection before `operator new`, including an
over-aligned element type. A separate compile regression checks that an active
`max(a, b)` macro does not affect the allocator header.

## Verified scope

The exact failed production commands compile with GCC 16.2 for NetBSD amd64
after the patches. The pair regression fails before lazy constraints and
compiles after them. The delayed-priority-queue production unit fails with the
original allocation-size diagnostic before the allocation guard and compiles
after it. Both changed Chromium unit-test translation units compile with the
production GCC16 flags. The allocator runtime regression compiles with
exceptions and assertions enabled. These are compile checks, not test execution.

Clang Static Analyzer 21 checks of the 19 affected production translation units
introduce no findings relative to their baseline. Existing forwarding-reference
and dead-store findings remain visible. Clang is used only for analysis.
Cppcheck 2.18 cannot complete analysis of these inputs. Direct source analysis
stops at unsupported libc++ compiler traits. GCC-preprocessed Glib and string
inputs stop at the same unchanged `safe_conversions_impl.h` syntax error before
and after the patch. No clean Cppcheck result is claimed.

Build the two test objects with the same GN output configuration:

```sh
ninja -C /absolute/output obj/base/base_unittests/message_pump_glib_unittest.o
ninja -C /absolute/output obj/base/base_unittests/string_util_unittest.o
```

Execute the corresponding upstream tests on an ABI-matching target after its
runtime is available. Complete Electron linking, upstream test execution,
ASan/UBSan or Valgrind execution, and application acceptance remain pending.

## Network and generated code checks

The network follow-ups retain fatal enum paths in DNS, ipcz, and WebRTC.
ScenarioState retains fatal padding diagnostics with both supported compilers.
QUICHE checks the zlib output-size and received-handshake prerequisites before
use. Its Settings handling uses the existing frame visitor. The selected
WebTransport subprotocol is converted only after the negative-index check.

Abseil splits leaf and internal B-tree nodes through separate template
instantiations. Both kinds use the existing allocation sizes. The added
`Btree.map_uint64` case uses the existing MapTest differential checks against
`std::map` and exercises deep splits. All five affected production units compile
with their original GCC16 flags. Runtime execution of this test remains pending.

The ipcz checked-cast patch rejects signed underflow and negative-to-unsigned
conversions that the original upper-bound comparison accepted. Constant-expression
boundary checks pass in C++20 and C++23. Invalid lower and upper boundaries are
rejected. The upstream runtime and death-test source compiles with GCC16.
Typed API object release preserves the same reference counter and virtual
destruction. Size/alignment probes for APIObject, its typed implementation,
DriverTransport, and Node match before and after. Two upstream ownership tests
compile for typed and erased final references, including a private derived
destructor. Runtime execution remains pending.

The Dawn patch changes the generator template. Regenerate `proc` outputs with
the pinned dawn_json_generator.py and dependencies. The baseline output matches
the production generated file. GCC16 rejects its unsupported CFI selector before
the patch and compiles the regenerated output after it. Clang retains the CFI
exclusion. Generic sanitizer annotations remain available to other compilers.

All 35 previously failed production commands compile with GCC16 after these
follow-ups. Apple Clang 21 analysis completes on the patched translation units.
Completed baseline comparisons introduce no findings. The baseline
host_resolver_system.cc analysis crashes the Clang frontend, so that pair is
not a complete comparison. Existing dead-store, forwarding-reference, and ipcz
callback diagnostics remain visible. The callback is moved only on a path with
a nonempty local broker vector; that path returns before its direct invocation.
The pinned Chromium Clang does not provide the static analyzer backend.
Cppcheck still cannot complete these modern dependency inputs. GCC-preprocessed
ipcz and Dawn variants reach the same dependency syntax errors before and after;
these checks do not establish a clean Cppcheck result.

## SIMD validation and scratch-buffer moves

`pffft-simd-debug-validation-gcc16.patch` applies with `-p1 -F 0` from the
Chromium source root. It retains `validate_pffft_simd()` in release builds and
compiles its assert-only calculations when assertions are enabled. The release
production unit fails before the patch and compiles after it with GCC 16.2.
Both assertion-enabled variants compile. Preprocessing retains all 14 SIMD
assertions. GCC16 `-fanalyzer` completes both assertion-enabled variants without
findings.

The standalone [PFFFT fixture](pffft-correctness.c) calls SIMD validation and
compares real FFT sizes 32/96/160 and complex sizes 16/48/80 against an independent
double-precision DFT. It also checks the inverse scale and rejects NaN/Inf.
Use the common GCC16 amd64 cross driver and an EmberBSD sysroot:

```sh
GCC=/absolute/cross-tools/bin/x86_64--netbsd-gcc
SYSROOT=/absolute/emberbsd-amd64-sysroot
CHROMIUM=/absolute/chromium/src
PORTS=/absolute/Ports
OUTPUT=/absolute/new-check-output
mkdir -p "$OUTPUT"
"$GCC" --sysroot="$SYSROOT" \
  -B"$SYSROOT/usr/pkg/gcc16/lib/gcc/x86_64--netbsd/16.2.0/" \
  -B"$SYSROOT/usr/pkg/gcc16/lib/" \
  -std=gnu11 -O2 -msse3 -fno-strict-aliasing -Wall -Werror -UNDEBUG \
  -I"$CHROMIUM/third_party/pffft/src" \
  "$PORTS/probes/electron/tests/pffft-correctness.c" \
  "$CHROMIUM/third_party/pffft/src/pffft.c" -lm \
  -o "$OUTPUT/pffft-correctness"
```

Run the resulting ELF on an ABI-matching target. The cross-built fixture passed
on an amd64 target with the NetBSD 11 ABI and reported `SIMD=4`. This verifies
six forward DFT/inverse cases and enabled SIMD assertions. It does not verify
all FFT sizes, architectures, or browser media paths. The tested fixture source
SHA256 is `18dba92738f1292c600e00d6cdb30a4531453ea0075f7a1a5d849aca3bd643e8`.

Cppcheck 2.18 analyzes PFFFT with the production defines, target headers, and
Unix64 data model. Both variants retain 14 inherited allocation-failure
warnings in `pffft_new_setup`, 15 style findings, and the normal-check branch
limit notice. No new findings appear. Clang Static Analyzer 21 retains the same
single dead-store finding in `pffft_transform_internal`. These are comparisons,
not clean analysis results.

`angle-scratch-move-gcc16.patch` applies with `-p1 -F 0` from
`third_party/angle`, at DEPS revision
`54ebf19ed818ac14bd3daee1f5ceb0644f6b64d6`. The delegating constructor initializes
lifetime, countdown, and empty storage before move assignment swaps them.
The production unit fails with an uninitialized-value diagnostic before the
patch and compiles after it. The changed upstream test translation unit also
compiles with GCC16. Run ANGLE's `angle_unittests` with
`--gtest_filter=ScratchBuffer.MoveConstruction*` on the target; these two tests
have not been executed yet.

Clang Static Analyzer 21 completes both ANGLE variants without findings.
Cppcheck 2.18 stops at the same inherited `angleutils.h` syntax error in the
GCC-preprocessed variants. That parser limit prevents a complete comparison;
no clean Cppcheck result is claimed. Target objects use GCC16 throughout.

## BSD platform inputs

The Opus GN patch retains `USE_ALLOCA`. BSD builds select the existing
`stdlib.h` fallback instead of the unavailable `alloca.h` header. The first
failed production command reproduces the missing-header error before the
change. It compiles after removing only the incorrect feature define. The
real target headers provide the `alloca` declaration. GCC16 `-fanalyzer` and
Cppcheck 2.18 complete that corrected C translation unit without code findings.

A full production GN generation retains stack allocation and removes
`HAVE_ALLOCA_H` for NetBSD. All 42 affected C commands compile with GCC16 after
their defines are checked against the regenerated Ninja files.

The ANGLE PCI patch changes the default selection only for NetBSD. Its existing
Mesa/GLX path does not call the Linux pciutils implementation. That implementation
requires a different PCI API and Linux sysfs; a header from another PCI library
cannot satisfy it. The corrected graph retains the Linux, X11, and Vulkan system
information sources and excludes only `SystemInfo_libpci.cpp` on NetBSD.
All four retained production translation units compile with GCC16. The
preprocessed NetBSD `GetSystemInfo` body is unchanged. A GN evaluation of 160
platform/graphics combinations leaves all other operating systems unchanged.
These source and graph checks do not establish target GPU runtime acceptance.


## Electron entrypoint selection

NetBSD must select its entrypoint before the GN Linux alias, which includes
BSD targets. The main-selector regression now executes the real Chromium
platform definitions and Electron condition chain with host GN. Independent
source-list expectations reject the original glibc selection and the former
late NetBSD branch. The corrected selector retains the POSIX main and stdio
helper. Linux, Windows, macOS, and other platform source lists stay unchanged.
See the [test commands and scope](README.md) for the 27 planning cases.
The POSIX main and stdio helper compile with the production GCC16 target flags.
The main uses headers produced by the unchanged upstream fuse and buildflag
generators. Complete linking and runtime startup remain separate checks.


The selected C++ source files are unchanged by the GN patch. Their target
hashes match the compiler pilot. Apple Clang Static Analyzer 21 reports no
stdio-helper findings and two existing forwarding-reference findings in
Abseil and base headers for the main unit. No entrypoint findings appear.
GCC16 preprocessing completes both units. Cppcheck 2.18 stops at dependency
syntax errors in both preprocessed inputs; it does not complete this analysis.

## WebRTC, geometry, and Skia GCC16 checks

The WebRTC follow-up retains fatal invalid-enum paths after exhaustive switches.
Its Clang diagnostic scopes remain Clang-only. GCC receives no replacement
suppression. The valid constexpr mappings, TLS/DTLS version defaults, packet
validation, callback results, and codec selection remain unchanged.

The cipher-group value parameter cannot alias its vector. `emplace` constructs
it in place after the existing deduplication. A private STUN helper retains the
fresh integrity attribute's concrete hierarchy during virtual owner assignment.
The public `AddAttribute` entry point, validation order, ownership callbacks,
message length accounting, object layout, and virtual interfaces stay unchanged.
Tests cover empty and repeated cipher groups, erased derived attributes,
remove/re-add callbacks, clear, and virtual destruction. Existing RFC5769
integrity and XOR-address ownership tests remain in place.

The H264 formatter validates its level against the existing declared-level
table before conversion to one byte. Invalid levels return `std::nullopt`.
The regression includes negative, undefined, and oversized levels. H265 uses
a 64-bit unsigned shift operand for counts from 1 through 32. Geometry retains
bitwise SIMD-mask operations with explicit comparison parentheses. Skia retains
`clang::reinitializes` when the compiler supports that attribute.

All 42 observed failing production commands compile with GCC16 after these
patches. The three changed upstream test translation units also compile with
the production target flags and real GoogleTest/GoogleMock include roots.
This does not establish test execution or complete Electron linking.

Paired analysis covers 26 production translation units. Apple Clang 21 Static
Analyzer retains the same 23 inherited diagnostic instances in each state.
It introduces no finding. Clang emits no target object. Cppcheck 2.18 consumes
GCC-preprocessed target inputs. Fifty of 52 cases stop at dependency parser
errors. The remaining pair retains the same warnings and branch limit notice.
Expanded-header locations in that pair do not map to valid statistics-header
lines. No Cppcheck pass or confirmed statistics-structure defect is claimed.
The checks retain real target defines, include paths, and the NetBSD x86_64
model without fake builtins or new warning suppressions.

## WebRTC media return paths

The AI-assisted `webrtc-media-enum-paths-gcc16.patch` preserves valid enum
branches and adds `RTC_CHECK_NOTREACHED()` at 21 non-void exits. It keeps
Clang deprecation scopes unchanged and excludes those pragmas from GCC.
The two changed public headers export `rtc_base:checks` through `public_deps`.
Their GN declarations retain the embedder's common public dependencies.

All 22 observed failing production commands fail before the source changes
and compile afterward with GCC16 and the original diagnostics. Both variants
use the same completed generated headers and target sysroot. Clang Static
Analyzer completes all 44 cases with the same 47 inherited findings per
variant. Cppcheck stops at dependency parser errors in all 44 cases. This
comparison does not establish a clean Cppcheck result.

A bounded GN fixture uses the pinned `rtc_library` template and its defaults.
The public dependency passes header checking for standalone, Chromium static,
and Chromium component modes. Missing and private dependency controls fail
header checking in each mode. This is nine GN contract cases; it does not
replace full-project generation or target runtime execution.

## UI identifiers, network enums, and X509 names

The AI-assisted identifier patch gives each type's class-name string one inline
static storage entity. Namespace and nested-class declarations keep the same
pointer layout, constexpr operations, strong types, and PassKey access. The
[identifier fixture](identifier-linkage/README.md) compiles and links two
translation units. Its address, name, and access checks pass on physical NetBSD
amd64. The baseline namespace declaration fails `-Werror=subobject-linkage`;
the patched forbidden-access control still fails its PassKey constraint.
The upstream identifier and X509 unit-test translation units also compile.

The Net/UI and HTTP enum patches preserve valid branches and add 36 fatal
terminals. All 25 affected production translation units compile with GCC16
after these patches. The interaction-sequence check also uses the identifier
patch above. Clang Static Analyzer completes all 50 before/after enum cases
with unchanged diagnostic signatures. Cppcheck reaches the same dependency
parser limits in every pair. These results do not establish a clean Cppcheck
result or target execution of the upstream unit tests.

The X509 change replaces trailing-dot `resize(length() - 1)` with `pop_back()`
after the existing nonempty check. It keeps hostname canonicalization, wildcard
rules, and matching behavior. Five test inputs cover uppercase absolute names,
dot-only names, two trailing dots, and a single-label mismatch. The production
unit fails with the original GCC16 object-size diagnostic and compiles after
the change. Paired identifier and X509 analysis completes with the same three
inherited findings. All four Cppcheck cases stop at the same dependency parser
error. Full browser linking and runtime acceptance remain separate checks.

## Graphics enum exits

The AI-assisted graphics patch adds 28 fatal exits after exhaustive switches
in ten source files. It keeps plane formats, byte and channel counts, alpha
policy, Skia type selection, default/gainmap dispatch, filter thresholds,
shadow styles, and paint operation dispatch unchanged. Valid unknown-format
branches and existing sentinel failures remain.

All ten observed production inputs fail before the patch and compile after
it with their GCC16 flags. Paired Clang Static Analyzer checks complete all
20 cases with the same 20 messages per variant. Source review of the three
inherited pointer/lifetime paths finds incompatible path assumptions: a null
flags pointer derived from a live operation, and a sole Skia reference while
a converting temporary still owns a second reference. These traces do not
justify source changes. This review is not GPU or sanitizer execution.
Cppcheck stops at unchanged dependency parser errors in all 20 cases. Full
browser execution and graphics acceptance remain separate checks.
