# ncnn port patch provenance

These patches are local EmberBSD adaptations against Tencent ncnn release
20260526, commit `e54f7b1f88434e1d844ea0551b880a1cfb079ce1`.
They retain upstream's BSD-3-Clause copyright and license.
The original source is <https://github.com/Tencent/ncnn>.
These patches were prepared with an AI coding agent. They are not claimed
as accepted upstream changes.

`pkgsrc/local-ai/ncnn/patches/patch-netbsd-cpu-count` uses the real NetBSD
`sysconf(_SC_NPROCESSORS_ONLN)` result. Without OpenMP, upstream's generic
fallback reports one CPU on every NetBSD machine. The patch accepts only a
positive result representable by `int` and retains the one-CPU fallback for
query failure or an unrepresentable result. It does not infer CPU IDs from
the count or implement affinity or heterogeneous core classification.

`pkgsrc/local-ai/ncnn/patches/patch-posix-cpu-once` fixes simultaneous first
access to cached CPU information. An ordinary integer flag does not publish
the cached values safely. Two callers can also write the same fields together.
The threaded POSIX path now uses `pthread_once` to initialize and publish all
fields once. The initializer uses internal helpers and does not recurse
through a public CPU query on the accepted NetBSD or Linux profiles.
The source-linked first-use control detects the original defect under
Valgrind DRD. No application-level mutex or prewarming hides the race.

Patch checksums are recorded in the package `distinfo`. The runtime source
archive and immutable revision are recorded in the owning probe manifests.

`pkgsrc/local-ai/ncnn/patches/patch-c-api-allocations` checks all 13 C wrapper
allocations before member access. Handle constructors return null on wrapper
allocation failure. The two layer factories release their already-created
C++ layer. The two void custom-registration functions log allocation failure
and leave the registry unchanged. Later C++ `new` exceptions retain their
upstream policy. The source-linked allocation control fails each direct
wrapper allocation once and checks rejection, cleanup and registration retry.

`pkgsrc/local-ai/ncnn/patches/patch-c-api-mat-array` gives the C API matrix
array adapter ownership of its reference-counted matrices. Upstream retains a
pointer to a local vector that is destroyed before the first model load.
The adapter now derives from `ModelBin`, owns the copied vector and checks
its read index. The C structs and callback signatures retain their layouts.
The lifetime control checks released original handles, 1D/2D/3D loading,
empty/exhausted input and user callback dispatch. Memcheck exposes the
baseline use-after-free and checks the fixed path.

`pkgsrc/local-ai/ncnn/patches/patch-c-api-callback-failures` preserves a custom
layer callback's nonzero status before reading its outputs. It releases any
partial returned handles and keeps destination outputs unchanged on failure.
A successful callback that omits a required output returns `-100`.
All six ModelBin callback load methods return an empty matrix for a null result.
Zero-sized forward and inplace arrays pass null pointers. These changes keep
the public C layouts and callback signatures. The source-linked callback
controls check failure, partial outputs, normal output, null weights and
zero-sized arrays. Their baseline controls expose crashes or changed outputs.

`pkgsrc/local-ai/ncnn/patches/patch-c-api-type-visibility` keeps visibility
attributes on the original four C++ type declarations and on all exported
functions. C structure declarations omit the ignored type attribute.
The [header controls](../c-api-header/README.md) compile through ordinary
installed pkg-config includes with strict GCC16 C11 and C++17 diagnostics.
They compare size, alignment and every field offset for the four structures.
The original and repaired C++ headers and repaired C header retain identical
layout bytes. Function export checks retain public dynamic symbols.
