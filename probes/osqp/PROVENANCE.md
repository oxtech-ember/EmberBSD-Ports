# OSQP source provenance

[OSQP 1.0.0](https://github.com/osqp/osqp/releases/tag/v1.0.0) is pinned at
commit `236713ce9a56c182ac3230d52108f952afce1523`.
[QDLDL 0.1.9](https://github.com/osqp/qdldl/releases/tag/v0.1.9) is pinned at
commit `af62a6f2c62725b9bc09811177006de037a1e800`.
[sources.tsv](sources.tsv) records the upstream tag archives and SHA256 hashes.
These are the selected current stable versions checked on 2026-10-14.

OSQP and QDLDL retain their Apache-2.0 licenses and upstream copyright notices.
The AMD ordering code bundled with OSQP retains its BSD-3-Clause license and
Timothy A. Davis, Patrick R. Amestoy and Iain S. Duff copyright. The installer
copies all three licenses and the unchanged OSQP `NOTICE`, including its
Stanford/Oxford and bundled-component attribution, alongside the source receipts.

OSQP's FetchContent declaration names QDLDL 0.1.8. This profile overrides it
with the hash-verified 0.1.9 source through `FETCHCONTENT_SOURCE_DIR_QDLDL`.
Fully disconnected FetchContent prevents unpinned git fetches. QDLDL's object
library is included in libosqp; a separate QDLDL library is not installed.
The installed numerical consumer checks their compatibility rather than
assuming a successful configuration proves it.

`netbsd-interrupt.patch` is an original AI-assisted EmberBSD change to
`src/CMakeLists.txt`, pinned by [patches.tsv](patches.tsv). It adds NetBSD to
the existing POSIX listener source-selection condition. It does not define
`IS_LINUX`, disable interrupts, replace the listener, or modify timing.
Upstream's non-Windows/non-macOS timer already uses POSIX `clock_gettime`.
The patch retains OSQP's Apache-2.0 licensing and has not been submitted upstream.

The source-selection fixture evaluates the real source-list branch on the host;
its original-source failure and patched-source success are not a native build.
GCC16 cross compilation, real packaging and installed AArch64 numerical,
derivative and interrupt checks now pass. The original source-selection failure
and patched success remain separate host fixture evidence. Earlier macOS
contracts remain their original host record.

The ordinary recipe also checks two QDLDL constructor allocations. The unchanged
numeric algorithm now reports those failures before dereferencing NULL. A separate
upstream allocator-hook control proves both original SIGSEGV failures and patched
error returns/cleanup. It does not certify all allocation-failure paths.

The upstream test harness uses current Catch2 3.16.1 (MIT). Its compatibility
patch updates includes, namespaced Approx/Clara APIs and one malformed tag.
It does not alter numeric assertions. Production packages omit Catch2 and test
archives. Upstream test-data generation uses Python 3.13.5, NumPy 2.5.4 and
SciPy 1.18.1 on the accepted Linux host; these are not target dependencies.

The shell helpers, CMake fixtures and C contracts are original AI-assisted
EmberBSD work under the accompanying MIT license. No project-owned Python is
introduced. The selected production C library does not invoke Python; the
separate upstream test-data generator does.
