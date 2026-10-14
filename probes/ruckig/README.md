# Ruckig local motion generation

This profile installs the Ruckig 0.19.4 C++20 shared library for local
state-to-state trajectory generation with velocity, acceleration and jerk
limits. EmberBSD Ports owns the reproducible recipe and installed consumer.
The [pkgsrc recipe](../../pkgsrc/local-robotics/ruckig) provides a binary
package. This software generates trajectories; it is not a motor controller.

On 2026-10-14, Linux GCC16 cross compilation, real package installation and
numerical execution passed in EmberBSD AArch64 QEMU. All 15 upstream groups
also passed with the bounded 1,000-trajectory argument. See
[target validation](cross-validation.md) for hashes, memory checks and limits.

## Cross build and package

Use the [GCC16 compiler and EmberBSD sysroot](../../profiles/development-toolchain/cross/README.md).
The cross helper checks the source archive, installs the complete native
`PLIST`, and builds consumers against that staged installation:

```sh
sh probes/ruckig/cross-build.sh /absolute/gcc16 /absolute/ember-sysroot \
  /absolute/ruckig-0.19.4.tar.gz /absolute/new/ruckig-cross
```

The staging prefix is `ruckig-cross/stage/usr/pkg`. The package and cross
build use the same `features.cmake`. Upstream tests remain enabled. Transfer
the staging tree, recipe, consumer and upstream test to EmberBSD. Use
[package-cross-stage.sh](../../scripts/package-cross-stage.sh) with actual
target BUILD_INFO and one `REQUIRES` line for each required library.

Run the package check as an administrator in a disposable target system:

```sh
sh run-target.sh /packages/ruckig-0.19.4.tgz /tests/ruckig-contract \
  /tests/test-target /results/ruckig
```

It checks installed linkage, three numerical contracts, every upstream test
group, removal, the missing-library failure and reinstallation. It leaves
the package installed. The target needs matching GCC16 runtime libraries.
The ordinary pkgsrc recipe resolves compiler dependencies and runs the same
upstream tests through `make test`.

## Build

Use a C++20 compiler, CMake, Ninja, tar and sha256/shasum. There is no Python
dependency. The library has no extra runtime dependency beyond the C++ ABI.

```sh
export PATH=/usr/pkg/bin:/usr/bin:/bin:/usr/sbin:/sbin
export CC=/usr/bin/cc CXX=/usr/bin/c++
JOBS=1 ./build.sh /absolute/new/ruckig-work
./test.sh /absolute/new/ruckig-work
```

An optional second argument to `build.sh` supplies an offline archive cache.
The recipe checks the pinned SHA256 before extraction and rejects an existing
work directory. Builds inherit the caller's memory limits. An optional explicit
`BUILD_AS_KIB` sets a soft address-space limit on NetBSD/Linux. Logs remain in
`WORK/logs` and the library is installed in `WORK/install`. The source profile does not change system
packages, services, scheduling policy or hardware.

The upstream cloud client is explicitly disabled. Intermediate waypoint
requests are rejected; they never invoke a remote calculation service.
Python bindings, upstream examples and benchmarks are also disabled.

## Installed contract and limits

The separate consumer requires `find_package(ruckig 0.19.4 EXACT CONFIG)` and
links `ruckig::ruckig`. Three CTest cases check:

- An analytic one-axis, rest-to-rest move against its closed-form optimal
  duration and midpoint, then 1,001 samples against endpoint and jerk limits.
- Three axes at a simulated 10 ms control interval, a changed target that
  forces replanning, all derivative bounds and deterministic fresh restart.
- Negative jerk/acceleration limits, NaN input, an invalid target velocity
  and an unsupported intermediate waypoint.

On 2026-10-07, a macOS arm64 build with Apple Clang passed all three installed
CTest cases. The online restart check compares the complete position, velocity,
acceleration and jerk trace: 297 steps and 3,564 values in each fresh run.
This host result verifies the selected API and numerical fixtures, not EmberBSD.

Tests use simulated time. They do not establish control-loop deadlines,
physical actuator safety, model accuracy or real-time scheduling in a VM.
The target VM checks establish CPU numerical execution and package lifecycle.
Hardware actuation, scheduling deadlines and sustained control remain untested.
See [provenance](PROVENANCE.md) and [MIT license](LICENSE).
