# FreeImage system-JPEG transform contract

`check-source.py` uses Python's standard library. It requires native Linux
GCC16, the GCC16-built common libjpeg-turbo 3.2.0 provider, CMake, pkg-config,
Clang19 for analysis, Cppcheck and Valgrind. It verifies the original archive
SHA256 before extracting the real translation unit and its original headers.
It applies the recipe's exact JPEG and CMake patches with zero fuzz.

```sh
python3.15 profiles/common-graphics/tests/freeimage-jpeg/check-source.py \
  /absolute/FreeImage-3.19.25-linux-source.tar.gz \
  /absolute/native-g++ /absolute/native-codec-prefix /absolute/new-work
```

For cross builds, add `--target`, supply the common NetBSD GCC16 C++ compiler,
and use the codec prefix inside its configured sysroot. This mode builds both
executables and records `BUILT_UNRUN`. Run `before/contract` on EmberBSD and
expect status 1 with the unsupported-transform diagnostic. Run `after/contract`
and expect status 0 with all 335 cases complete. Target mode does not run native
analyzers or claim execution. Its RPATH selects the target codec prefix and
the common `/usr/pkg/gcc16/lib` runtime. It selects that library at link time
and verifies the executable's `NEEDED` entry against its actual SONAME.
It never writes to the sysroot.

The original system-provider implementation fails a valid perfect vertical
flip. The repaired implementation passes 335 cases. The oracle checks actual
DCT coefficients, quantization tables and APP1/COM markers. It covers all eight
operations, crop expansion, rectangle normalization, edge-relative positions,
perfect-transform refusals and trimming. It exercises 4:4:4, 4:2:2, 4:2:0,
4:4:0, 4:1:1, 4:4:1, 4:1:0, 4:2:4 and grayscale sampling.

The same-handle case starts at a nonzero stream position. Other cases exercise
short reads, short writes, failed and throwing callbacks, malformed input,
and a real `std::bad_alloc` from the source input buffer. GNU ld wraps the
allocation call; it preserves the allocator and Memcheck's ownership tracking.
Every assertion stays active, including CMake Release builds.

The system libjpeg header callback uses `setjmp` recovery inside a plain
helper. Its state is allocated on the heap. The error path does not throw
through codec C frames or cross a C++ object's lifetime with `longjmp`.
The AArch64 common libjpeg has no C++ unwind tables. A matched GCC16 control
with the former throwing callback aborts on malformed input. The repaired
callback passes the same 335 cases on EmberBSD with the common C++ runtime.
These source contracts do not establish installed FreeImage package behavior.

TurboJPEG's public API rejects crops for unknown sampling types. The contract
checks exact uncropped transforms of a 3:1 sample and consistent crop/query
refusals. It does not substitute a private jpegtran implementation.

Both source versions receive Cppcheck and Clang Static Analyzer checks.
Clang uses the selected GCC16 C++ headers. Cppcheck receives the real
GCC16-preprocessed input and an additional pass with its modeled system
headers and the actual codec headers. The JSON result retains all findings,
including parser limitations. Check the diagnostics before reporting a clean
analysis result. No warning categories or test assertions are disabled.

Strict Memcheck runs the repaired source contract with every leak kind treated
as an error. A small CMake project compiles and links the actual patched
system-JPEG branch and runs the same coefficient contract. These checks cover
the real source function. Complete FreeImage/FreeImagePlus packages, their
upstream suites, target execution and installed application behavior require
separate acceptance.

The work directory records commands, exit statuses, source/provider hashes,
diagnostics and results. Preserve these files before cleaning build outputs.
