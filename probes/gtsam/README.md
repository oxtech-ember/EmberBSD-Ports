# GTSAM 4.3.0 with GCC16

GTSAM's shared CPU library is cross-built with GCC/G++ 16.2.0 for
EmberBSD AArch64. The installed package solves linear measurement fusion
and a nonlinear Pose2 graph with independently known answers. Acceptance
covers real target pkg_tools, external consumers and eleven selected
upstream programs in QEMU. See [validation](VALIDATION.md) for evidence
and limits, and [provenance](PROVENANCE.md) for source and licenses.

## Cross build

Use the existing GCC16 toolchain and common Eigen 5.0.1 sysroot from
[robotics foundations](../robotics-foundations/README.md) and
[OMPL dependencies](../ompl/README.md). No second Eigen installation is
built. Verify the pinned upstream archive in [sources.tsv](sources.tsv).

```sh
sh probes/gtsam/cross-build.sh \
  /absolute/gcc16/toolchain /absolute/common-sysroot \
  /absolute/archives/gtsam-4.3.0.tar.gz /absolute/new-gtsam-output
```

`CROSS_JOBS` defaults to three. All inputs must use simple absolute paths;
existing outputs and symlinks are preserved. The helper verifies the source
and compiler before extraction, installs into `OUTPUT/stage/usr/pkg`, builds
external installed consumers, checks AArch64 ELF/runtime metadata and compares
the complete payload with the package PLIST. Linux does not execute target
configuration probes. Source and all build logs remain in OUTPUT.

For the selected upstream acceptance suite, build these additional targets
in that same configured tree (the helper builds the library and external
Ports consumers):

```sh
cmake --build /absolute/new-gtsam-output/build --parallel 3 --target \
  testPose2 testOrdering testGaussianFactorGraph testJacobianFactor \
  testLinearExceptions testValues testPriorFactor testBetweenFactor \
  testNonlinearOptimizer testNonlinearFactorGraph testMarginals
```

The common [features.cmake](../../pkgsrc/local-robotics/gtsam/features.cmake)
selects C++17, shared libraries and external Eigen. It retains matrix rotations,
tangent IMU preintegration and upstream's private CCOLAMD, SuiteSparse_config,
Spectra and Cephes. Boost/serialization, TBB, MKL, CUDA, GeographicLib, CHOLMOD,
METIS, unstable modules, Python and MATLAB wrappers are excluded. Warnings as
errors remain enabled. Building stable modules is not acceptance of all APIs.

The profile supplies the base POSIX thread library through upstream's
`GTSAM_ADDITIONAL_LIBRARIES` interface, and caches `MATH_LIBRARY` as the linker
name `m`. These choices fix a reproduced missing-pthread link and prevent an
absolute build-sysroot libm path in installed CMake targets. No GTSAM source
is patched. `CppUnitLite` is built because upstream installs its exported
framework by default; the install step must not silently omit it.

## Packaging and installed use

The package recipe is [local-robotics/gtsam](../../pkgsrc/local-robotics/gtsam).
The accepted route is cross staging followed by actual target
`scripts/package-cross-stage.sh`. Native pkgsrc source compilation has not
been accepted by this task. The package depends on exactly `eigen3-5.0.1`;
target libraries use GCC16 `libstdc++.so.7` and `libgcc_s.so.1`.
RPATH contains `/usr/pkg/lib` and `/usr/pkg/gcc16/lib`.

An external CMake consumer uses:

```cmake
find_package(Eigen3 5.0.1 EXACT CONFIG REQUIRED)
find_package(GTSAM 4.3.0 EXACT CONFIG REQUIRED)
target_link_libraries(application PRIVATE gtsam Eigen3::Eigen)
```

The [standalone graph example](https://github.com/oxtech-ember/EmberBSD-Examples/tree/main/robotics/gtsam-graph)
exports both initial and optimized states to CSV. Its independent checker
rejects nonfinite numbers, wrong states/costs and invalid covariance.

`run-target.sh PACKAGES TESTS NEW_RESULTS` installs the two real packages,
checks their contents and loaded runtimes, executes numerical and error
contracts, rejects deletion of a required dependency, removes and reinstalls
both packages, and repeats the numerical checks. TESTS contains the installed
consumer binaries, both Examples binaries, and the eleven upstream programs
listed in the runner. Upstream tests require their original compiled-in
`examples/Data` location to be populated inside the guest.
The minimal guest also needs pkg_tools, tar/gzip, ldd and `/dev/full`.
No target compiler or Python runtime is required.

## Numerical contracts

| Case | Independent expected result |
| --- | --- |
| Linear fusion | Unit-variance factors `x0=0`, `x1-x0=2`, `x1=3` give `x0=1/3`, `x1=8/3`, cost `1/6` |
| Nonlinear Pose2 graph | A prior, two motions and a loop recover `(0,0,0)`, `(2,0,0)`, `(2,2,pi/2)`, cost below `1e-12`, anchor covariance `0.01 I` |
| Underconstrained graph | A lone relative measurement reports `IndeterminateSystemException` |
| Missing state | A factor referring to an absent pose reports `ValuesKeyDoesNotExist` |
| Numerical checker | Every coefficient is checked for finiteness before comparison; corrupted CSV, NaN and both infinities fail |

The graph example returns 64 for invalid CLI input, 65 for invalid graphs
and 74 for I/O errors, including deferred writes to `/dev/full`. Invalid
graphs leave existing output untouched. File and stdout output agree.

`tests/cross-guards.sh` checks corrupt archives and preservation of existing
outputs/symlinks. The older native `build.sh`/`test.sh` is retained as an
optional GCC16 source helper; the cross route owns current target acceptance.

Synthetic graphs do not validate real sensors, SLAM datasets, a physical board,
robot navigation, real-time deadlines or sustained operation.
