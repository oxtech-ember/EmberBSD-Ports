# Potrace bitmap helpers

The common recipe retains [Potrace 1.16](https://potrace.sourceforge.net/),
its original source archive/checksums, CLI, libpotrace and zlib dependency.
The recipe and packaging originate in pkgsrc; their RCS identifiers remain.
Potrace and `src/bitmap.h` are copyright Peter Selinger and distributed under
the upstream GPL (see the archive's `COPYING`). No library source is copied
into this recipe or into a consumer.

Package revision 1 additionally installs the **unchanged** upstream
`src/bitmap.h` as `include/potrace/bitmap.h`. Upstream explicitly shares these
static inline bitmap helpers between the library and frontends. Consumers
include `<potrace/bitmap.h>` and link the same public libpotrace; the header
includes the existing `potracelib.h`. This is a namespaced header-delivery
change, not a library ABI change. The API dependency floor is 1.16nb1.

The helper owns bitmaps created with `bm_new`: release them with `bm_free`,
which finds the allocation base even after `bm_flip` changes the signed
stride and moves the map pointer. `potrace_trace` borrows the bitmap;
`potrace_state_free` releases its result. The original helper preconditions
remain: dimensions are nonnegative, and unchecked `BM_U*` operations require
in-bounds coordinates. This packaging change does not add input validation.

## Installed-provider check

Configure `tests/` with the selected SDK C compiler and `CMAKE_PREFIX_PATH`
pointing at the installed provider, build, then run CTest. For a cross build,
run the resulting `bitmap-contract` executable on the target. The fixture
uses the actual installed header and library: zero-dimension bitmaps,
bounds-checked pixels, a rectangle crossing the machine-word boundary,
negative-stride flip/duplicate/free, and real tracing with caller ownership
preserved. It does not replace the library with a mock or claim complete
KiCad bitmap conversion acceptance.

For native memory diagnostics, instrument both the library and fixture with
`-fsanitize=address,undefined -fno-sanitize-recover=all`, enable
`ASAN_OPTIONS=detect_leaks=1:halt_on_error=1` and
`UBSAN_OPTIONS=halt_on_error=1`, and use the selected SDK linker. Diagnostic
installation belongs in a disposable prefix, separate from the SDK and
package output.

The isolated Darwin arm64 check uses the selected Ports Clang/ld64.lld and
instruments the real library as well as the consumer. The original installed
layout fails to compile the fixture because the namespaced header is missing;
installing the byte-identical upstream header makes the strict ASan/UBSan
run with leak detection pass. Fixture CSA is clean. Cppcheck retains two
style suggestions in unchanged upstream `bitmap.h` (variable scope and a
const parameter); neither is suppressed or claimed as a clean result.
Target packaging and complete KiCad conversion runtime remain separate.
