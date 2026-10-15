# OpenVINS offline estimator source probe

Prepare OpenVINS **v2.7** with current common Eigen 5.0.1, OpenCV 5.0.0,
Boost 1.92.0 and Ceres 2.2.0. The recipe builds the upstream ROS-free shared
estimator and installed headers. It preserves the
accepted upstream Ceres Manifold backport and local dependency adaptations.
See [provenance](PROVENANCE.md), [archive pin](sources.tsv) and [license](LICENSE).

**Source preparation only.** Archive integrity, patch application and portable
shell guards were checked on the host. Native compilation, installation,
API compatibility and the numerical consumer remain unverified. This is not
a working port, packaged VIO service or physical-camera claim.

## Prerequisites and build

Use the shared [media OpenCV provider](../media/README.md), including `video`
for KLT, and common [Ceres](../ceres/README.md). The compiler is native C++17;
CMake, Ninja, curl, tar, patch and SHA256 tools are required. ROS, Python,
GUI, ArUco, external datasets and sensor hardware are not required by this
profile. No older parallel dependency installation is permitted.

```sh
EIGEN_PREFIX=/absolute/foundations/install \
OPENCV_PREFIX=/absolute/media/install \
CERES_PREFIX=/absolute/ceres/install \
JOBS=1 sh probes/openvins/build.sh /absolute/new-openvins-work /absolute/archive-cache
sh probes/openvins/test.sh /absolute/new-openvins-work
```

Omit the final cache argument to download the pinned archive. Set `BOOST_PREFIX`
to an absolute Boost 1.92.0 installation only when a private prefix replaces
the common cross sysroot copy; the consumer records and reuses that prefix. A new absolute
work path is required. The archive is hashed before extraction; the large
unused `ov_data` dataset is excluded. Build/install files stay under that work
path. `JOBS=1` is the default. No address-space limit is imposed by default.
An explicit positive `BUILD_AS_KIB` requests a verified soft limit; inherited
hard limits and VM-wide settings remain unchanged.
The recipe retains CMake's normal Release optimization flags.

## Cross flow

The primary flow is cross: compile on the developer machine, accept on the
EmberBSD target. Set `CROSS_TOOLCHAIN_CMAKE` to a cmake toolchain file with
the common GCC16 cross driver and `CROSS_SYSROOT` to the matching sysroot.
The build then skips the NetBSD host check, configures both the estimator and
the consumer through the toolchain file, and stages `$work/accept` with the
built consumer, the shared libraries and `accept.sh`. No target binary runs
on the host. On the EmberBSD device run:

```sh
sh /path/to/accept.sh /path/to/accept
```

The script verifies that every dependency resolves, that exactly one C++
runtime (the target GCC16 library) is loaded, and then runs the analytic
contract. The native flow (`test.sh` on a NetBSD host) remains available for
a host that compiles natively, but the cross flow is the default.

## Prepared installed contract

The C++ consumer supplies an independent analytic eight-second trajectory,
200 Hz acceleration/angular-rate measurements and 20 Hz pinhole projections
of a fixed 3D scene. Only the initial pose/velocity are provided as ground
truth. A small unknown accelerometer bias creates inertial-only drift an
order of magnitude above the accepted position error.
Tracks end regularly so MSCKF triangulation and visual updates are required.
The test requires accepted visual features and bounded position, velocity and
attitude error under the unmodelled bias; the filter's convergence on the
bias value itself stays outside this contract.
A stale camera timestamp must not rewind state.

This exercises the real installed filter through its simulated-observation
interface. It does not validate image feature tracking, automatic initialization,
real IMU calibration or real-time performance. The acceptance limits are
prospective until the first native run. The upstream simulator is built but
is not used as the numerical oracle. Tests also check installed library and
C++ runtime linkage, with a 180-second deadline and the same optional soft-limit control.
