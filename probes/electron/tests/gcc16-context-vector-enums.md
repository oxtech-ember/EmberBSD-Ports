# GCC 16 context, vector and enum checks

These AI-assisted patches follow the [reader, wire and media
changes](gcc16-reader-wire-media.md). The checked source baseline is Chromium
`2bc373d14b1b7befc5efc0ba225eff44136b6193`, with Dawn
`fc7a7206eaea67bab011878af20a3d7a4ffa89b2` and WebRTC
`03d95bd35f7c6f4b7d04fb4c070c799ae7aa9b1b`. The upstream pins remain those in
the [Electron guide](../README.md). Apply the four patches from the Chromium
root with strip 1 and fuzz 0, after the preceding patches in that guide.

The production comparisons use GCC 16.2 NetBSD AMD64 commands with unchanged
target flags. Generated inputs have separate provenance: the retained snapshot
uses Chromium overlay `ec4c28c11a0719182091b640afe73a8abc3e3143` and Dawn
`33259aa3b76e443342339dd78cf666f90692b9fd`. It is not fresh output from the
checked source baseline.

## Preserved contracts

| Patch | Change and boundary |
| --- | --- |
| `webrtc-unused-fragment-counters-gcc16.patch` | Parentheses retain the matched-filter grouping. Two H.264 counters and their increments are removed because no code reads them. NAL length checks, overflow checks, start-code assertions, copy order and output sizes remain unchanged. |
| `vector-insert-batch-construction-gcc16.patch` | The allocator constructs its inserted block from four saved scalar fields in member order. URL formatting assigns its two known adjustment records together in their original order. Block state, offset merging and caller-owned adjustments remain unchanged. |
| `chromium-shared-image-complete-type-gcc16.patch` | The backing owner initializes the context field where its type is complete. Field order, null initial state and special members remain unchanged. The complete native Skia dispatch gains a fatal terminal after all four cases. |
| `chromium-metrics-tracing-enum-gcc16.patch` | Seven closed or validated enum paths gain fatal terminals. Two open Perfetto outbound enums retain unknown numeric values for the existing closed Mojo validator. All named mappings and accepted wire values remain unchanged. |

The vector changes avoid GCC16/libc++ optimizer diagnostics without changing
the common libc++ implementation or disabling diagnostics. The allocator's
saved block does not alias vector storage. Its original block reference remains
unused after insertion. The URL branch starts with an empty local vector and
retains the records `(0, kWwwLength, 0)` and `(0, kMobilePrefixLength, 0)`.

Moving `AccessParams` initialization into its existing constructor avoids a
complete-type include cycle. The backing owner already includes the complete
context definition. `ProduceSkia` retains the null-context fallback, `kNone`
return, Ganesh calls and Graphite call. Its switch has no default. The native
context invariant does not replace inbound Mojo validation.

UKM's four type bits select exactly its sixteen named values. Restriction
preferences are validated and normalized before conversion. Study activation
is an open protobuf enum: `ProcessedStudy` validation rejects unsupported values
before both `ShouldActivate` calls. Its existing sentinel branches still return
false. The unwinder's named `kUnknown` case remains valid.

Perfetto configuration parsing can retain unknown numeric values. The two
outbound conversions must preserve these values rather than abort or map them
to a valid default. Native enum and Mojo wire values both use the signed
32-bit range, and their known sets are exactly 0, 1 and 2. Generated serializers
write the returned numeric value. Existing nonextensible Mojo validators reject
other numbers. The two inbound conversion terminals retain the validated
closed-enum contract. No parser, wire validator or accepted value set changes.

## Production compiler checks

Export the affected commands with `ninja -C "$out" -t commands` from a
configured GCC16 target graph. Replay each command with separate object and
dependency outputs. Retain macros, target headers, include order, optimization
and diagnostics. A copied source needs its original directory as an `-iquote`
root. Record generated-input hashes separately from source pins.

| Production scope | Before | After |
| --- | --- | --- |
| WebRTC matched filter and H.264 encoder | Grouping and unused-counter diagnostics | Both compile |
| Fenced allocator and URL formatter | Vector array-bounds diagnostics | Both compile |
| Shared-image header consumers: `buffer_manager.cc`, `dawn_gl_texture_representation.cc` | Incomplete context type | Both compile with the constructor change |
| Eight metrics, variations and tracing translation units | Nine return-path errors | All compile |

The shared-image owner uses staged comparisons. With only the constructor
change, its original and patched full-owner commands both fail at the inherited
missing return in `ProduceSkia` (status 1 on both sides). A separate pair keeps
the constructor change on both sides: the missing terminal fails with status 1,
and the final owner compiles with status 0. This qualifies both changes without
claiming a fresh combined three-translation-unit replay. Header-first checks
fail before and pass after the constructor change. A real incomplete-refcounted
type remains rejected; a complete refcounted type remains accepted. All four
actual special-member definitions compile on both sides with the complete type.

All corresponding GCC preprocessing calls succeed. The URL diagnostic reduction
uses the real `Adjustment` header: its baseline fails, the batched form compiles,
and a deliberate out-of-bounds read still fails. This is a diagnostic control,
not a functional replacement for the production algorithms. Separate upstream
vector regression drafts remain unbuilt and unexecuted.

## Perfetto enum target fixture

[perfetto-enum-wire-check.cc](perfetto-enum-wire-check.cc) uses the actual
`EnumTraits`, generated serializers and generated `IsKnownValue` functions.
It checks 0, 1, 2, -1, 3, 127, 123456789, `INT32_MIN` and `INT32_MAX` for each
of the two enums. Known-set expectations are literal and independent of the
conversion implementation. No production implementation is replaced by a stub.

Cross-compile the fixture with the common GCC16 compiler and target sysroot.
Take target macros, include roots, generated headers and warning flags from the
production `console_config_mojom_traits.cc` command. The standalone runtime
fixture uses the common GCC16 libstdc++: omit the production bundled-libc++
include roots and its configuration macros for this separate check. Keep the
configured target `-B` runtime paths. Use `-std=gnu++23 -O2 -fno-exceptions
-fno-rtti -ffunction-sections -fdata-sections`. Link the fixture object with
`-static-libstdc++ -static-libgcc -Wl,--gc-sections` and the target GCC16 runtime
paths. Run the executable only on the target. Expected status is zero.

Normal and UBSan-trap GCC16 binaries each pass all 18 checks on physical NetBSD
11 AMD64. A mutant that maps unknown outbound values to zero fails at -1 with
status 1. The instrumented compile uses `-fsanitize=undefined
-fsanitize-undefined-trap-on-error -fno-sanitize-recover=all`. Prebuilt system and
standard libraries are not instrumented. These checks cover numeric conversion,
serialization and known-value classification. Complete Mojo message dispatch
and malformed-message rejection are source-audited, not runtime-accepted.

## Source analysis and limits

Paired Clang Static Analyzer 21 production calls complete with no added finding
signatures. Clang is used for analysis only; GCC16 produces target objects.
The matched filter and URL formatter have no findings. H.264 retains one Abseil
forwarding-reference warning. The fenced allocator retains two inherited
Abseil/bind warnings. The two shared-image consumers retain four and two
findings; its staged owner pair retains two. The eight metrics/tracing pairs
retain respectively 3, 0, 4, 4, 4, 7, 7 and 10 findings. These include an
uninitialized-argument finding in the tracing profiler, which remains unresolved.
The fixture analysis with production Chromium libc++ headers completes and
retains the same seven findings on both sides.

Cppcheck 2.22 stops at unchanged dependency parser limitations in all these
pairs. It does not complete analysis. A separate fixture attempt with the exact
runtime GCC16 libstdc++ flags also passes both GCC preprocessing stages.
Cppcheck stops at the same GCC fixed `stdio.h` line 165 parser error. Apple
Clang 21 rejects GCC16 `bf16` and `_Float*` preprocessed constructs and crashes
on both sides. That attempt is a frontend limit, not a completed analysis.

The focused checks do not establish audio/codec operation, GPU behavior, URL
runtime behavior, an Electron link, package lifecycle or Blanc browser and
sandbox acceptance.
