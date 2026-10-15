# PCL 1.15.1 validation

Acceptance date: 2026-10-15. The build host is Linux x86_64 with GCC 16.2.0.
The target is EmberBSD AArch64, fork revision
`267ee85eee1027198175809a8b7b0572df36ad1e`, with the `aarch64--netbsd` ABI.
QEMU 10.0.13 uses TCG, two Cortex-A72 CPUs and 2 GiB RAM.
These results do not establish physical-board, sensor or real-time behavior.

## Installed target results

All eight actual packages pass creation or reuse, installation, integrity
checks, dependency-protected deletion, ordered removal and reinstallation.
The common Eigen and Boost packages retain their established payloads.

Range filtering removes a distant point and a NaN. VoxelGrid returns the
independent centroids `(0.2,0.2,0.2)` and `(1.2,0.2,0.2)` within `1e-6`.
Empty clouds remain empty. ICP aligns thirty asymmetric points using a known
Z rotation of `0.012` radians and translation `(0.04,-0.03,0.02)`.
Every transform coefficient and aligned point passes `1e-4`; fitness is
finite, nonnegative and below `1e-8`. Unmatched clouds do not converge.

The standalone Examples CLI exports independently checked CSV. Invalid
arguments return 64, unmatched clouds return 65, and output failures return
74. Rejected alignment preserves existing output. `/dev/full`, missing output
directories and output directories are checked. NaN, infinities and a wrong
matrix coefficient fail the independent checker. CSV before and after package
reinstallation is identical.

Twelve upstream programs execute all 172 selected GoogleTest cases:
`test_common`, `test_pointcloud`, `test_transforms`,
`test_filters_grid_minimum`, `test_morphological`, `test_filters_functor`,
`test_uniform_sampling`, `test_warps`, `test_correspondence_estimation`,
`test_registration`, `test_kdtree_search` and `test_flann_search`.
Registration uses upstream `bun0.pcd`, `bun4.pcd` and `milk_color.pcd`.
This is a bounded selection, separate from PCL's full test suite.

The installed LZ4 CLI, four compression round trips, repeated frame-info
queries, zero buffers, Boost compression/Random APIs and 256-byte generic
atomics also pass. Two atomic threads complete 2,000 checked updates.
Twenty-six ELF checks cover ten PCL DSOs, four installed consumers and the
twelve upstream programs. Their runtime paths use target installation paths.

## Native memory and source analysis

Linux GCC16 controls pass seven installed-consumer CTests, the same twelve
upstream programs and the Examples CLI CTest. Thirty final Memcheck runs
cover all twelve selected upstream programs, four PCL contracts, LZ4, Boost,
the CLI/checker cases and generic atomics.
Invalid memory accesses, uninitialized values and definite, indirect or
possible leaks are fatal. All thirty report zero errors and suppressions.
These are native controls, not Valgrind execution inside the target VM.

Cppcheck 2.17.1, Clang Static Analyzer 19.1.7 and GCC 16.2.0 `-fanalyzer`
use recorded target compilation commands, macros and included-header hashes.
Fourteen upstream units are compared before and after source adaptations;
seven contract/example units use actual cross compilation databases.
Clang reports no diagnostics in the final selected PCL/FLANN and consumer C++ paths.
Cppcheck reports no errors or warnings in the new consumer units.

Cppcheck cannot parse Boost.PP in six PCL library/test units. That is a coverage gap.
Existing FLANN findings affect unselected LSH/autotuned or serialization
paths; KissFFT has inherited allocation-failure findings outside filtering
and ICP. GCC analysis also reaches complexity limits in LZ4 and one regression
unit. These findings are retained with their upstream owners and scope;
this record does not claim the entire libraries are analyzer-clean.
Fatal native UBSan reproduces the original LZ4 null-pointer arithmetic and
accepts the patched zero-buffer/repeated-query regression.

The original FLANN search test loses five creator allocations, totaling
80 bytes under Memcheck. Seven raw creator pointers bind to the constructor's
leading boolean instead of its owning second parameter. The source patch
uses explicit sorting and managed creators. Clang's seven original leak
diagnostics disappear. All five test cases pass strict Memcheck with zero
remaining bytes and zero errors after the patch.
The patch changes the test fixture, not the installed library API or algorithms.

The source recipes retain licenses and AI-assisted patch provenance.
Source pins and adaptation details are in [PROVENANCE.md](PROVENANCE.md).
