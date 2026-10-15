# GTSAM 4.3.0 validation

The GCC16 cross package and installed known-solution graph scenario passed
in EmberBSD AArch64 QEMU on 2026-10-15. These are CPU software contracts;
physical hardware and real sensor navigation remain unverified.

## Target and packaging

The fork kernel and base/sysroot come from EmberBSD commit
`267ee85eee1027198175809a8b7b0572df36ad1e`. GCC/G++ 16.2.0 targets
`aarch64--netbsd`. QEMU 10.0.13 uses TCG, Cortex-A72, two CPUs and 2 GiB RAM.
GTSAM shares the existing Eigen 5.0.1 package and GCC16 runtime. Actual target
`ldd` resolves `libgtsam.so.4`, private `libcephes-gtsam.so.1`, base pthread/libm,
`libstdc++.so.7` and `libgcc_s.so.1`. AArch64 ELF checks cover the two libraries
and both installed Ports consumers; target RPATH contains no build-host path.

Actual pkg_tools created the GTSAM package, installed both packages, verified
registered contents, rejected deleting Eigen while GTSAM required it, removed
both and reinstalled them. Both numerical CSVs agree byte-for-byte before and
after reinstallation. The GTSAM PLIST matches all 507 files/symlinks.

| Retained accepted package | SHA256 |
| --- | --- |
| eigen3-5.0.1 | `f2893a8e9416f20984df0f3ed699fd66dec78e699f05394b4fb6ca2dd25ea3b1` |
| gtsam-4.3.0 | `e2f11c20acae746d932b7f1200da0b0f9bb0e2663f55c03e4adac48922b9f11a` |

The native pkgsrc source route has not been executed by this task. Cross
staging plus actual target package creation is the accepted delivery route.
The final public `cross-build.sh` also completes from a new empty output:
255 library/framework build steps, real installation, both external consumers,
four AArch64 ELF checks, portable imported targets and exact PLIST comparison.
The pinned original source, package hashes, compiler inputs, compile databases,
analysis and runtime logs are retained in the cloud task record.

## Numerical results and failures

The linear graph minimizes one half of the sum of squares of `x0`,
`x1-x0-2` and `x1-3`. Its normal equations are
`[[2,-1],[-1,2]] x = [-2,5]`, so the independent exact solution is
`[1/3,8/3]` with cost `1/6`.
The installed example reports `0.33333333333333365`, `2.6666666666666674`
and cost `0.16666666666666671`; the initial state `[-1,4]` has cost `5.5`.

The nonlinear Pose2 graph has a prior, two motions and a loop constraint.
Optimization recovers `(0,0,0)`, `(2,0,0)` and `(2,2,pi/2)` within `1e-7`.
The observed initial cost is `21.125103895132622`; the final cost is
`2.5685195574157304e-30`. Anchor covariance is `0.01 I` within `1e-8`.
Every matrix coefficient is finite; exported covariance is independently
checked for symmetry and positive definiteness.

Both Ports consumers and the standalone Examples application execute against
installed GTSAM. A separate C++ CSV checker links neither GTSAM nor Eigen.
File/stdout results agree. Counterfactual CSVs with a wrong finite solution,
NaN and either infinity are rejected. The matrix predicate regression checks
nonfinite coefficients before any `maxCoeff()` comparison.

A graph containing only a relative factor raises `IndeterminateSystemException`.
An incomplete pose map raises `ValuesKeyDoesNotExist`. The example returns 65
for these invalid graphs without creating or truncating output. Invalid CLI
returns 64. Missing directories, output directories, `/dev/full` file writes
and stdout redirected to `/dev/full` return 74.

Eleven unmodified upstream programs pass on AArch64:
`testPose2`, `testOrdering`, `testGaussianFactorGraph`, `testJacobianFactor`,
`testLinearExceptions`, `testValues`, `testPriorFactor`, `testBetweenFactor`,
`testNonlinearOptimizer`, `testNonlinearFactorGraph` and `testMarginals`.
This is the selected suite, not a claim that every upstream test ran.

## Reproduced integration defects

The initial install failed because upstream installs `CppUnitLite`, but the
bounded build requested only `gtsam`. The corrected package/helper builds
both targets and installs the real framework and headers.

The first upstream executable link failed on unresolved `pthread_create`.
The shared profile supplies `pthread` through upstream's existing
`GTSAM_ADDITIONAL_LIBRARIES` input. This records the dependency on the library
and its exported interface rather than hiding the missing symbol in consumers.

Initial installed CMake exports also exposed an absolute sysroot `libm.so`
path. Setting the existing `MATH_LIBRARY` cache input to STRING `m` preserves
explicit math linkage and exports a portable linker name. Original and final
metadata are retained. Checks reject host paths in effective imported targets.
An external consumer also builds from the promoted common sysroot.
No upstream C/C++ or vendor source is changed, and diagnostic categories are
not suppressed to obtain success. Warnings as errors stay enabled.

The first host result collector rejected the intentional `/dev/full` symlink
in the archive roundtrip fixture. The corrected collector accepts exactly the
two expected fixture links, validates paths/types and hashes, and completes
the collection. The actual guest run itself had passed; a fresh full replay
then passed collection and clean guest unmount. Control filenames, empty files,
symlinks and real gzip/tar archives are covered by the roundtrip.

## Native memory controls and bounded analysis

Native Linux x86_64 GCC16 C++17 uses the same pinned source, shared profile and
common Eigen headers. It complements AArch64 execution; Memcheck does not
execute target binaries. The five Ports CTests and eleven selected upstream
programs pass natively. The Examples CLI regression also passes.
Four real Ports contract runs and eleven Examples/checker runs use Valgrind
Memcheck 3.24.0 with origins, full leak reporting and fatal definite, indirect
or possible leaks. Expected error exits are checked independently of Valgrind's
error exit. No suppressions are added. All fifteen runs report zero errors.

Cppcheck 2.17.1 and Clang Static Analyzer 19.1.7 use the actual AArch64 GCC16
compilation database, target macros, ABI and include paths. Source, macros,
GCC/Clang included-header hashes and diagnostics are paired for five library
C++ units plus the CCOLAMD C wrapper. The link-only profile changes leave
these compilation contexts unchanged. Four own consumer/example units are
also analyzed. All fourteen Clang C++ runs complete with zero diagnostics;
Cppcheck reports only informational messages on the four own units.

Cppcheck retains inherited findings in upstream code. Its `missingReturn`
reports concern template aliases resolving to `void`; the vendor
`negativeIndex` report omits the producer invariant `Fsize >= -1` and a nonempty
child list. They are reviewed and retained, not hidden. Other inherited
constructor/style findings do not establish a whole-library clean result;
serialization/wrapper-only incomplete default objects are outside these tests.
GCC16 `-fanalyzer` on the actual vendor C unit reports one unused variable and
38 explicit complexity diagnostics, including bailout after 16,147 nodes.
Both paired runs agree. This partial result is not a clean GCC analyzer pass.
Clang's own target intrinsic headers adapt its frontend to GCC16 public headers;
production sources, compiler options and target headers are unchanged.

No real IMU/GNSS measurements, recorded SLAM dataset, physical board, sustained
operation or real-time deadline is accepted by these synthetic graph checks.
