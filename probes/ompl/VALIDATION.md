# OMPL 2.0.2 validation

The GCC16 cross package and installed path-planning scenario passed in
EmberBSD AArch64 QEMU on 2026-10-15. This is CPU software acceptance, not
physical robot or board validation. [Build and use](README.md).

## Target and packages

The fork kernel and base/sysroot originate from EmberBSD commit
`267ee85eee1027198175809a8b7b0572df36ad1e`. GCC/G++ 16.2.0 targets
`aarch64--netbsd`. QEMU 10.0.13 uses TCG, Cortex-A72, two CPUs and 2 GiB RAM.
The application libraries share GCC16 `libstdc++.so.7` and `libgcc_s.so.1`.
Actual target `ldd` confirms the installed OMPL/Boost libraries and runtime;
host ELF inspection confirms AArch64 and target-only RPATHs.

Real target pkg_tools created, installed, checked, removed and reinstalled
all four packages. Deletion of Boost while OMPL depends on it is rejected.
The two final CSV outputs are byte-identical within the accepted build.

| Package | SHA256 |
| --- | --- |
| eigen3-5.0.1 | `f2893a8e9416f20984df0f3ed699fd66dec78e699f05394b4fb6ca2dd25ea3b1` |
| boost-headers-1.92.0 | `ea8fc2b14b99cba54059072528c1f95bdf462732fb8a427daa4a0430868b2d23` |
| boost-libs-1.92.0 | `310dd54c32c6fdb24692b6233ccfb817362f4759db50271f2539b616a4924906` |
| ompl-2.0.2 | `3bb29f6862a3f2a317567b6fcdebd65d5cf39d6513b03c6029d0f5ec2544c5ec` |

PLIST matches cover 611 Eigen files/links, 16,590 Boost header/support entries,
67 Boost library/export entries and 458 OMPL entries. Boost contains every
16,412 header path in the current common toolkit profile. Its compiled
subset does not establish all Boost library support.

The first disposable image exhausted free inodes while installing headers.
It was stopped cleanly. The corrected image reserves 32,768 free inodes and
passed the full package cycle. Its actual tar/gzip roundtrip and exported
result/package hashes were checked. Both guests unmounted cleanly.

## Behavior

The installed [Examples program](https://github.com/oxtech-ember/EmberBSD-Examples/tree/main/robotics/ompl-path)
finds an exact RRTConnect detour: 24 points, length `1.496893253146`, seed
`104729`. This is an observed path, not a cross-version expected coordinate
sequence. Independent C++ slab and Ruby edge-orientation checks accept all
complete segments, bounds, endpoints and length. File and stdout agree.

Both the invalid goal and separating wall produce no exact route. Negative
cases create no output. Invalid/incomplete options return 2; no exact route
returns 3; missing output directories and `/dev/full` return 4.
The installed library also passes dense/sparse Eigen residuals, Boost archive
roundtrip, valid/invalid program_options and caught DSO exceptions.
A consumer built only from the corrected pkg-config flags roundtrips OMPL
state and inline metadata. A strict link demonstrates the missing public
Boost dependency before the correction.

Thirteen unmodified upstream programs pass on AArch64 and native Linux:
`test_adjacency_list`, `test_heap`, `test_grid`, `test_gridb`, `test_pdf`,
`test_random`, `test_halton_sampling`, `test_state_operations`,
`test_state_spaces`, `test_state_storage`, `test_planner_data`, `test_ptc`
and `test_fmt_null_goal`. Other upstream planning benchmarks and optional
feature suites were compiled where enabled, but are not claimed executed.

The geometry regression reproduces a missed decimal corner tangent in the
old oracle. Both corrected headers pass direct fixtures, 10,000 corner
tangents and one million comparisons with integer edge orientations.
Source-helper guards reject corrupt input, missing manifests and zero/invalid
job limits while preserving existing work and symlinks.

## Memory and source analysis

Native Linux x86_64 GCC16 C++17 controls use the same pinned library sources.
They complement target execution; they do not run target AArch64 binaries.
Valgrind Memcheck 3.24.0 checks origins, invalid access and full leak reports;
definite/indirect/possible leaks are fatal. No suppressions are used.

- Seven Examples cases pass with expected statuses, zero errors and zero bytes
  at exit: path, wall, invalid goal, CLI error, missing directory, full device
  and the geometry fixture.
- The dependency consumer passes with 277 allocations/frees and zero errors.
- The pkg-config archive consumer passes with 117 allocations/frees and zero errors.
- Upstream planner-data tests pass all six cases, 164,455 allocations/frees,
  zero errors and zero bytes at exit.

Cppcheck 2.17.1 compares six upstream OMPL units and two Boost units before
and after packaging with actual GCC16 AArch64 macros, target headers and ABI.
Source/header hashes, macros and diagnostics are identical: no upstream C++
patch is claimed. Five final local C++17 units complete with style/performance
findings only. The inline archive fixture reaches a Boost concept-check parser
error; its Cppcheck analysis remains incomplete, including the bounded
preprocessed-input attempt. It is not claimed clean.

Clang Static Analyzer 19.1.7 completes all fourteen selected translation units
with zero diagnostics. Clang's target intrinsic headers adapt GCC16 NEON
builtin parsing; fork headers and GCC16 libstdc++ remain selected. This is
bounded path analysis, not proof of full frontend equivalence or whole-library
correctness. Static analysis does not replace execution.

Inherited Cppcheck findings remain visible: Boost archive writes are not
modeled in seven PlannerDataStorage reports; an empty Boost stream-buffer
constructor is flagged for null setg bounds without a dereference; Time.h
retains a localtime thread-safety concern. OMPL/Boost own these unchanged
findings. Concurrent formatting and arbitrary untrusted archives are not
validated. GCC16 also retains inlined Eigen aligned-free and upstream
virtual-overload warnings; the selected numerical consumer passes native
Memcheck and AArch64 execution without suppressing those warnings.

Native pkgsrc source builds, optional Python/VAMP/collision-library variants,
physical boards, robot-body clearance, moving obstacles, optimality and
real-time actuation remain outside this acceptance.
