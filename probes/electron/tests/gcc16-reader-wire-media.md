# GCC 16 reader, wire and media checks

These AI-assisted patches follow the earlier Blink declaration, Dawn type and
dispatch, and tiling/AX patches. The checked source baseline is Chromium
`ec4c28c11a0719182091b640afe73a8abc3e3143` with Dawn
`33259aa3b76e443342339dd78cf666f90692b9fd`. The patches use strip 1 and fuzz 0
from the Chromium root. They change no build flags or public ABI.

The upstream pins remain those in the [Electron guide](../README.md).
The production comparisons use the same GCC 16.2 NetBSD AMD64 commands on both
sides. Generated inputs have separate provenance: the retained snapshot uses
Chromium overlay `97b386a0be6ae794068ed77313b7e9b0b6a9a3f3`. It is not a fresh
generation from the checked C++ baseline.

## Preserved contracts

| Patch | Change and boundary |
| --- | --- |
| `blink-ascii-codepoint-gcc16.patch` | Parentheses preserve both vector comparisons. A direct iterator header makes `CodePointIterator` complete before ranges checks. Two closed encoding switches gain fatal terminals. Constructors still select 8-bit or 16-bit strings. |
| `dawn-wire-and-single-word-ranges-gcc16.patch` | The generator writes `ObjectHandle.id` and then `generation` explicitly. Both volatile fields retain their types and order. The single-word bitset path uses unsigned scans and shifts after the existing empty/full checks. The wider bitset path is unchanged. |
| `gles2-scalar-cache-bounds-gcc16.patch` | Only the array-valued `GetIntegerv` cache path permits two/four writes. Scalar conversion helpers retain the service-query fallback for these names. All other cached states remain scalar. |
| `media-status-enum-noreturn-gcc16.patch` | Nine complete native switches gain fatal terminals. Existing unknown/error cases, CICP normalization and inbound IPC/Mojo validation remain unchanged. The aspect-ratio change affects only the private native-to-wire conversion. |
| `liburlpattern-enum-stream-endpaths-gcc16.patch` | The eight known diagnostic names remain byte-identical. Unrecognized representable enum values print their numeric value. Parsing, validation and wire conversions are unchanged. |

The Dawn wire audit covers all 37 generated assignments. Every expression is
a plain member access. There is no repeated call, index side effect or
increment. All generated outputs except `WireCmd_autogen.cpp` remain identical.
The original two-field assignment order is retained.

For the bitset path, the constructor handles all-set inputs before `Advance`.
`Advance` handles empty input before either bit scan. With at most 64 bits,
the first shift is below 64. The retained non-full invariant also bounds the
second shift below 64. Width zero never reaches a scan.

The GLES2 cache returns two values for `GL_MAX_VIEWPORT_DIMS` and four for
`GL_VIEWPORT`. The other public `Get*` implementations query the service and
copy the count returned by `GLGetNumValuesReturned` when the scalar cache
declines the name. See the [Khronos state-query reference](https://github.com/KhronosGroup/OpenGL-Refpages/blob/main/es3/glGet.xml).

## Production compiler checks

Export the affected commands with `ninja -C "$out" -t commands` from a
configured GCC 16 target graph. Replay each command with separate object and
dependency outputs. Retain its macros, target headers, include order,
optimization and diagnostics. A copied source needs its original directory
as an `-iquote` root. Keep generated input hashes separate from source pins.

| Production scope | Before | After |
| --- | --- | --- |
| Blink `string_view.cc`, `atomic_string_table.cc` | Vector-parentheses, incomplete iterator and return-path errors | Both compile |
| Dawn generated wire and `CommandBufferVk.cpp` | 37 assignment-reference and 96 array-bounds errors | Both compile |
| GLES2 `gles2_implementation.cc` | 64 scalar-cache array-bounds errors | Compiles |
| Five media consumers | Nine return-path errors across the four changed headers | All compile |
| liburlpattern `part.cc` | Two return-path errors | Compiles |

All corresponding GCC preprocessing calls succeed. The Blink header controls
cover 8-bit/16-bit reads and 32-bit/64-bit operations. Deliberately incomplete
iterator and unparenthesized vector controls still fail. Dawn controls retain
assignment return types and reject assignment to const-volatile destinations.
The production commands use Chromium's configured libc++.

## Functional target checks

The portable fixtures use the real production headers and implementations:

- [dawn-bitset-ranges.cc](dawn-bitset-ranges.cc) adapts the upstream Dawn tests.
  It checks 108 range calls with integer and scoped-enum index types at widths
  0, 1, 63, 64, 65, 127 and 128. It covers empty, full, sparse, alternating,
  high/low bit and word-boundary patterns.
- [liburlpattern-enum-stream.cc](liburlpattern-enum-stream.cc) checks all eight
  known strings and four literal unknown-value strings. Link it with the real
  patched `third_party/liburlpattern/part.cc`.

Cross-compile these fixtures with the common GCC 16 compiler and target
sysroot. Add the Chromium root, generated include root, Abseil root, Dawn root
and generated Dawn include root as applicable. Keep the configured target
`-B` runtime paths. Use `-std=gnu++23 -O2 -Wall -Werror -DNDEBUG
-fno-exceptions -fno-rtti`. The liburlpattern check also uses `-Wextra`.
The executed standalone checks use the common GCC
libstdc++ linked with `-static-libstdc++ -static-libgcc`; they do not replace
the separate production libc++ compiler checks. Run only on the target.

On physical NetBSD 11 AMD64, the original, patched and UBSan bitset fixtures
each pass 108 calls. A deliberate runtime shift by 64 terminates with SIGILL
under the same UBSan trap configuration. The normal and UBSan liburlpattern
fixtures each pass 12 cases. A mutant that omits the unknown PartType output
exits 1 and fails both literal PartType expectations.

The instrumented variants use `-fsanitize=undefined
-fsanitize-undefined-trap-on-error -fno-sanitize-recover=all`. This covers the
compiled fixture and selected source. It does not instrument prebuilt system
libraries. It does not establish a Valgrind or leak-check pass.

## Source analysis

Cppcheck 2.22 receives the actual GCC-preprocessed inputs with C++23 and a
64-bit Unix platform. Each production pair stops at the same inherited
libc++ parser limitation. No complete Cppcheck pass is claimed.

The standalone fixtures also receive GCC preprocessing, Cppcheck 2.22 and
Clang Static Analyzer 21 checks with the target's actual libstdc++ headers.
Clang analysis completes without findings. Cppcheck stops at the target GCC
fixed `stdio.h` parser limitation on line 165. The Dawn comparison has the
same limitation before and after the patch. No fixture Cppcheck pass is claimed.

All paired Clang Static Analyzer 21 production calls complete for the NetBSD
AMD64 target. Clang produces no target objects. GCC-only driver flags are
removed only from analyzer arguments. Target macros, headers and ABI remain.
The warning deltas are zero:

- Blink retains one `string_impl.h` dead-store finding in its affected pair.
- Dawn wire has no finding. The Vulkan consumer retains an Abseil forwarding
  reference warning and a CommandAllocator dead store.
- GLES2 retains six findings: two forwarding-reference warnings and four
  dead stores, including three in unchanged GLES2 code.
- The five media pairs retain respectively 3, 3, 0, 3 and 9 findings.
- liburlpattern has no finding on either side.

Inherited findings remain unconfirmed. Full browser linking, installed
package lifecycle, graphics/media behavior and browser sandbox acceptance are
separate gates. These focused checks do not establish a working Blanc browser.
