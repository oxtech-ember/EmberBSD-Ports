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
