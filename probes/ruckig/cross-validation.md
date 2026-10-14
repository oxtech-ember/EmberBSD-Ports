# Ruckig GCC16 target validation

Validated on 2026-10-14. The Linux host cross-builds the library and two
test programs. The EmberBSD guest creates, installs, removes and reinstalls
a real pkg_tools package. This validates simulated numerical execution.
It does not establish physical actuator behavior or control-loop deadlines.

| Input | Identity |
| --- | --- |
| Ruckig | 0.19.4, `a8db97a4e9c55e5160a3855f739fa3b270df8e4c` |
| Archive SHA256 | `4f57caa350770ce162aed92285fc07ac23e83b89bf802f5f500fb4bc8b2a1905` |
| Ports build recipe | `8474f28` |
| EmberBSD kernel, headers and base libraries | `267ee85eee1027198175809a8b7b0572df36ad1e` |
| GCC/G++ | 16.2.0, `aarch64--netbsd` |
| Tools | CMake 3.31.6, Ninja 1.12.1, base pkgtools 20260227 |
| Target | EmberBSD/NetBSD11 AArch64, QEMU10.0.13 TCG, Cortex-A72, two CPUs, 2 GiB RAM |
| Accepted package SHA256 | `d687f38e9269c037f697f3950fe3e520ed92f831bcaa92a7084b04571670dc2f` |

No upstream source patch is applied. The shared library retains the upstream
unversioned `libruckig.so` ABI. The dependency contract fixes this release.
Cloud calculations and language bindings remain outside the local profile.

## Target results

The package contains all 24 canonical `PLIST` files: headers, shared library,
CMake export, package metadata, license and source identity. ELF checks reject
host runtime paths. Target `ldd` resolves `/usr/pkg/lib/libruckig.so` and the
matching GCC16 `libstdc++.so.7`. `pkg_admin check` verifies the installed files.

The separate installed consumer passes three cases:

- Analytic one-axis motion: 1,001 samples and duration 2.51984 seconds, with
  independent endpoint, midpoint and derivative-bound checks.
- Three-axis online motion: 297 simulated steps, one target replan and an
  identical fresh restart of all 3,564 position/derivative values.
- Five invalid inputs rejected, including NaN, negative bounds and an
  unsupported cloud waypoint.

The real upstream `test-target 1000 42` passes all 15 test cases and 5,688
assertions, with zero skipped cases. The trajectory-count and seed are
upstream command-line arguments. This is a bounded run of every test group.

Removal deletes the library and its package record. The consumer then fails
to load that missing library. Reinstallation restores integrity and the
analytic result. These checks use the real target loader and package database.

## Source and memory evidence

Cppcheck 2.17.1 checks 11 library translation units, the upstream test and
included headers from native and target compilation databases. Both report
zero errors, 28 warnings, 97 style and 18 performance diagnostics. The port
does not add source changes or suppress diagnostic categories.

Review identifies template-parameter assignments and derivative-loop output
as analyzer false positives. `PositiveSet::insert` intentionally filters
negative values before calling its base implementation. Several members use
deferred initialization. In particular, a zero-limit interval leaves its
unused profile indeterminate; finite synchronization does not select that
profile. This remains an initialization concern, not a claim that the object
is safe for arbitrary copying or use. Output values before successful
calculation remain outside the accepted consumer lifecycle.

Clang Static Analyzer 19.1.7 analyzes all 11 library units with native GCC16
compile arguments and reports no diagnostics. This checks host paths, not the
target ABI. Native GCC16 controls run the three consumers and the complete
bounded upstream suite under Valgrind Memcheck 3.24.0. All four runs report
zero errors and free every allocation. No suppressions are used. The target
ELF files run separately in EmberBSD; host Memcheck does not instrument them.

GCC16 retains upstream and consumer possible-uninitialized warnings. Passing
numerical and memory tests does not prove every input or algorithm path safe.
The warning records remain part of the source evidence.

## Reproduction

Use [cross-build.sh](cross-build.sh), [run-target.sh](run-target.sh) and the
[ordinary recipe](../../pkgsrc/local-robotics/ruckig). Preserve configure/build
logs, compilation databases, ELF reports, target serial output, package
SHA256, integrity reports, consumer output, upstream assertions and analyzer
logs. Use the same source hash and simulated fixtures for each comparison.
