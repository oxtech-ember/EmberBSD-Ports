# PFFFT validation boundary

The 1.1.0 source is used with the common NetBSD alloca and NEON alignment
patches. The library's NEON float transform requires 16-byte-aligned FFT
buffers, as documented in its header. The Qt consumer uses 64-byte-aligned
buffers. A checked build rejects a deliberately misaligned input; release
builds do not promise to check this precondition.

On native Darwin arm64, the upstream CTest suite (7 tests), float and double
FFT programs and both C++ FFT programs passed. The FFT programs and float and
double SIMD self-checks passed with ASan and UBSan. Scalar FFT programs also
passed with UBSan. An installed CMake consumer passed its known-spectrum and
round-trip test. On EmberBSD amd64, the package and CMake consumer built, and
the ordinary round-trip consumer passed on the target. The target DSO and
consumer have no external `alloca` symbol. A non-x86, non-ARM 64-bit target
build was not available for this validation.

Clang Static Analyzer reported no diagnostics for the affected native float
translation unit. Cppcheck could not parse the unprocessed upstream SIMD macro
configuration (`unknownMacro`). On the same translation unit preprocessed by
the selected Clang, Cppcheck reported 210 diagnostics; each matched the
upstream 1.1.0 baseline by source location, severity and message with NEON
selected. These results do not claim a clean upstream Cppcheck run.
