# Validation scope

The restored source archive has SHA256
`6297cc55a1720523a437c54d07dc16b9da8c5f5ab5800da3c6ebded568d53c18`.
The official `V8.0.1` tag resolves to `b8f597c677811d1f9f4d8a97f5ae2825c0353a42`.
The public preparation script verified the archive and all recorded patch hashes.
All four patches applied to a fresh extraction with zero fuzz.

## Actual source regression

Host GCC 14.2.0 compiled the original and patched `Standard_StackTrace.cxx`.
The test used real OCCT headers and the actual upstream implementation.
It did not replace the implementation with a model or stub.
Flags included C++17, `-O1 -g`, AddressSanitizer, UndefinedBehaviorSanitizer,
`-fno-omit-frame-pointer`, and `-fno-sanitize-recover=all`.

The original implementation failed these five cases:

| Input | Observed failure |
| --- | --- |
| Unterminated eight-byte allocation | ASan heap-buffer-overflow in `strlen` |
| Declared capacity shorter than the initial string | Changed buffer despite the invalid capacity |
| `INT_MAX` requested frames | UBSan signed integer overflow |
| `INT_MAX` skipped frames | UBSan signed integer overflow |
| Skip beyond the captured frames | ASan negative-size argument to `backtrace_symbols` |

All five rejected-input cases and a valid trace passed after the patch.
A second run used the source produced by the public preparation script.
Valgrind 3.24.0 checked all six patched cases without sanitizer instrumentation.
It used origins, full leak checks, all leak kinds, and a nonzero error exit.
Every run had zero errors, zero live heap blocks, and no suppressions.

## Static analysis

Clang Static Analyzer 19.1.7 checked four native translation units before and after the patch:
`Standard_CLocaleSentry`, `Standard_CString`, `OSD_Path`, and `Standard_StackTrace`.
The flags came from the actual CMake compilation database.
Both passes completed without findings.
The baseline selected the original changed headers before generated headers.
This native analysis does not exercise NetBSD-only preprocessor branches.
Both new consumers also passed Clang analysis with their actual compilation flags.

Cppcheck 2.22.0 checked the same four modules through their compilation database.
It used the actual GCC14 predefines, Unix64 sizes, and upstream standard/POSIX models.
The baseline had 205 findings; the patched source had 200.
The patch removed three `OSD_Path` uninitialized-member findings, an `alloca` warning,
and one C-style cast finding. It added no diagnostic category.
The remaining 200 findings comprise 22 warnings, 163 style findings, and 15 performance findings.
They include unchanged reference-count assignment, copy-constructor, virtual-destructor,
inherited-member, and legacy-cast diagnostics in OCCT headers.
These findings remain visible and belong to the wider OCCT audit; this is not a clean whole-library claim.
Both new consumer translation units had zero Cppcheck findings.
No diagnostic category or source location was suppressed.

The initial fully preprocessed analysis could not parse GCC14's standard-library `array` header.
That failed parser pass remains separate from the successful normal compilation-database analysis.
The later target GCC16 source analysis is recorded below.

## Installed native core

Host GCC14 built and installed TKernel and TKMath with release exceptions enabled.
The installed core API passed in `C` and the real `de_DE.utf8` locale.
The latter preserved the process's `12,50` while OCCT formatted `12.50`.
Path round trips, exception text, and the checked array bound passed.
All six stack-trace cases also passed through the installed DSO.

Strict installed-library Memcheck differs from the standalone module check.
All eight runs retained 24 reachable bytes in two allocations.
Both stacks belong to `NCollection_BaseAllocator::CommonBaseAllocator`:
an eight-byte handle and its sixteen-byte allocator.
Upstream explicitly retains this singleton for destructors in other toolkits.
There were no lost allocations, invalid accesses, or suppressions.
The strict command still exited 1 for the two reachable contexts.
This is a classified lifetime allocation, not a zero-error Memcheck gate.

The native TKMath build retains upstream GCC14 optimization warnings in
`PLib::RationalDerivative`, `PLib::RationalDerivatives`, and `Poly_MergeNodesTool`.
The latter explicitly restricts the node count to three or four before sorting its Vec4.
These untouched modules are outside the four-module static-analysis scope.
Their diagnostics remain visible for the target GCC16 build and geometry review.

## Remaining acceptance

No full EmberBSD OCCT execution, complete STEP dependency, or KiCad GUI result is claimed here.

## GCC16 source checkpoint

The common AArch64 GCC16.2 compiler compiled six actual modules with the
coherent E34 sysroot and common GCC16 headers: the four modules above,
`OSD_MemInfo` and `Standard_Failure`. Before repair, `Standard_CString` fails
its unsupported-locale diagnostic and `OSD_Path` uses an incomplete `utsname`.
All six repaired objects compile. This is source compilation, not a linked
or executed target OCCT package.

Clang Static Analyzer 19.1.7 analyzed the same six repaired target modules
with AArch64/NetBSD, the real target sysroot and GCC16 include search paths.
All six completed without diagnostics. The original locale and path modules
fail configuration checks in that analysis too; the other four complete.
Cppcheck 2.22 received actual GCC16-preprocessed target sources. Its parser
rejects the GCC16 `__extension__ template<>` declarations in five modules.
The locale-sentry module completes with the same 85 style findings before
and after: 83 unused members in base header structures and two C-style casts.
The failed parser runs are incomplete and are not clean analyses. No macro
or diagnostic suppression was introduced.
The new exception consumer also passes target Clang analysis. Cppcheck rejects
the same GCC16 standard-library declaration in its fully preprocessed source.

An additional native GCC16/UBSan run compiles the actual `Standard_Failure`
module. The original constructor overflows `INT_MAX * 200` before its clamp.
The repair compares the frame count before multiplication. Negative, zero,
one-frame, 327-frame, 328-frame and `INT_MAX` cases pass afterward, preserving
exception messages and expected trace presence. The native helper TKernel
is the earlier GCC14 library; this test does not claim a full GCC16 rebuild.

Strict Memcheck of all six unsanitized exception cases reports the same
24 reachable bytes in the two documented `CommonBaseAllocator` allocations.
There are no lost blocks or invalid accesses. Every strict command exits 1;
no suppression converts these lifetime allocations into a clean gate.

The actual CMake 4.4.4 source-fragment regression reproduces an omitted
package `custom.sh` with an existing installation, then passes after repair.
It checks the complete small installed payload and preserves the existing
prefix. A canonical older `file(INSTALL)` DESTDIR addition was rejected before
publication because it double-prefixes the stage with current CMake.

The KiCad adapter applies with zero fuzz to the two pristine release files.
The resulting text differs only in the 12 `GetMessageString()` to `what()`
replacements. An actual AArch64 GCC16 compile with OCCT8 headers rejects the
old deprecated API under `-Werror=deprecated-declarations` and accepts `what()`.
Full KiCad compilation remains pending.
