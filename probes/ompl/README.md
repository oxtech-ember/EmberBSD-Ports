# OMPL 2.0.2 path planning

This profile supplies a shared C++ motion-planning library for EmberBSD.
It uses GCC 16.2.0, Eigen 5.0.1 and Boost 1.92.0. RRTConnect routes a point
around a closed rectangle. An independent checker validates complete edges.
Ports owns the library and packages. The [CSV application](https://github.com/oxtech-ember/EmberBSD-Examples/tree/main/robotics/ompl-path)
belongs to Examples. See [validation](VALIDATION.md) and [provenance](PROVENANCE.md).

## GCC16 cross build

Use a coherent EmberBSD AArch64 sysroot with GCC16 headers, startup objects
and its matching `libstdc++.so.7`. Do not substitute upstream NetBSD sets.
The compiler must report `16.2.0` and `aarch64--netbsd`. Linux CMake, Ninja,
patch, pkg-config and SHA256 tools are required. Python is not required.

Install the common `math/eigen3`, `devel/boost-headers` and `devel/boost-libs`
packages in the sysroot first; the build rejects a sysroot without them.
Download [OMPL](sources.tsv). The build verifies SHA256 before extraction and
requires a new output path.
Run these commands from this profile directory:

```sh
compiler=/absolute/gcc16-prefix
sysroot=/absolute/isolated-emberbsd-sysroot
cache=/absolute/source-cache
output=/absolute/new/ompl-cross
CROSS_JOBS=4 sh cross-build.sh "$compiler" "$sysroot" \
  "$cache/ompl-2.0.2.tar.gz" "$output"
sh tests/pkgconfig-build.sh "$compiler" "$sysroot" \
  "$output/stage/usr/pkg" /absolute/new/ompl-pkgconfig-consumer
```

Outputs contain the staging tree, toolchain, compile database, upstream tests
and installed consumers. Staged files must match each package PLIST.
ELF checks reject host runtime paths. Target RPATH uses `/usr/pkg/lib` and
`/usr/pkg/gcc16/lib`. Linux never executes a target configure probe.

OMPL uses the Boost serialization, program_options and unit test libraries
from the common `devel/boost-libs` package.

## Packages and acceptance

The recipes are `math/eigen3`, the common `devel/boost-headers` and
`devel/boost-libs`, and `local-robotics/ompl`. Cross staging is the accepted build route. Native
pkgsrc source recipes/buildlinks are provided; native pkgsrc compilation
has not been accepted by this task.

Create actual packages on the target with `scripts/package-cross-stage.sh`.
Build-info must record exact dependencies. Boost libraries depend on
`boost-headers-1.92.0`. OMPL depends on `eigen3-5.0.1`,
`boost-headers-1.92.0` and `boost-libs-1.92.0`.
Licenses and source receipts remain inside each package.

`run-target.sh PACKAGES TESTS NEW_RESULTS` checks installation, registered
contents, loaded runtimes, planning, errors, dependency deletion rejection,
removal and reinstallation. TESTS contains the planner/geometry contracts,
Examples executable and geometry test, dependency/pkg-config consumers,
and the thirteen upstream executables named by the runner. Upstream tests
also need their compiled-in resource paths.

The minimal target needs pkg_tools, tar/gzip, ldd, shell utilities and
`/dev/full`. Reserve enough inodes for staged and installed headers.
The accepted FFS image reserves 32,768 free inodes. No target compiler
or Python runtime is needed for this acceptance.

## Planning and limits

The world is `[0,1] × [0,1]`. Start and goal are `(0.1,0.5)` and `(0.9,0.5)`.
The closed obstacle is `[0.4,0.6] × [0.15,0.85]`; seed is `104729`.
Every coordinate must be finite and bounded. The independent slab checker
checks complete segments and treats tangency as collision. It expands faces
by `32 × double epsilon` to handle floating-point roundoff conservatively.
A decimal corner fixture detects the original missed tangency.
`tests/check-path.rb` independently validates CSV using edge orientations.
Ruby is a host validation tool, not an application runtime dependency.

An invalid goal lies inside the obstacle. A closed wall joins opposite world
boundaries in the blocked case. Neither may produce an exact solution.
Approximate results remain approximate and are never exported as successful
routes. The Ports contract also checks any approximate polyline for collision.

`tests/cross-guards.sh` checks rejection and work preservation. `tests/pkgconfig-contract.sh` checks metadata; its archive
consumer exposes public Boost symbols through OMPL templates.

A seed does not promise identical paths across versions or architectures.
This model is a zero-radius point with static obstacles. It does not establish
path optimality, body clearance, sensing accuracy, physical actuation,
dynamic collision safety or real-time deadlines.

VAMP, Python bindings, compiled demos, Triangle, FLANN, Spot and yaml-cpp
are excluded. Upstream still installs demo sources and benchmark-statistics
scripts. Running those Python scripts requires Python separately.
The selected shared metadata fix does not validate other configurations.
The older native `build.sh`/`test.sh` remains available with explicit common
prefixes; the cross route above owns current AArch64 acceptance.
