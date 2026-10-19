# fmt 12.2.0

The common graphics profile provides the current stable [fmt 12.2.0 release](https://github.com/fmtlib/fmt/releases/tag/12.2.0)
as `textproc/fmtlib`. The source manifest pins the original archive SHA256
`8b852bb5aa6e7d8564f9e81394055395dd1d1936d38dfd3a17792a02bebd7af0`.
The recipe retains upstream source without a portability patch and installs the
shared library, C API archive, CMake package, pkg-config file and public headers.

The [GCC16 probe](../../../probes/fmtlib/cross-build.sh) builds the pinned source
for AArch64 NetBSD, stages it outside the common sysroot, and links a CMake
consumer through the exported `fmt::fmt` target. The build uses GCC 16.2.0 and
the common cross profile's `/usr/pkg/gcc16/lib` runtime path. The 24 staged
files and links match `PLIST`; the library and consumer are AArch64 NetBSD ELF
files without build-host paths in their runtime metadata.

Cppcheck 2.22 analyzes the exact GCC16 compile database on both the pinned
upstream tree and the candidate. The candidate has no source patch, and all 58
upstream diagnostics are unchanged. They cover tagged union storage,
sub-views over one string buffer, the `back_insert_iterator` container accessor,
and deliberate arithmetic right shift guarded by an upstream static assertion.
The reports remain visible; no category is suppressed. Apple Clang 21.0.0
Static Analyzer reports no findings for the three target library translation
units or the CMake consumer, using the target sysroot, headers, macros and
optimization flags.

The native formatting consumer passes AddressSanitizer and UBSan. LeakSanitizer
is not supported by this macOS runtime, and Valgrind is unavailable on the host.
Target execution, the normal pkgsrc package lifecycle and integration with the
Kodi package remain separate acceptance steps.
