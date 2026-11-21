# MCAP C++ source probe

Record and replay timestamped robot data using MCAP C++ 2.1.3, including
LZ4 1.11.1 and Zstd 1.5.7 compression. This Ports-owned source probe supplies
the installed header-only C++ library and its shared compression dependencies.
It is not an installable pkgsrc package or a robot recording service.

## Build and test

Use a C/C++17 compiler, CMake 3.18 or newer, Ninja, tar, and `sha256` (or
`shasum`). curl is needed unless the second argument supplies every archive
named in [sources.tsv](sources.tsv). No Conan, Docker or Python is required.

```sh
JOBS=1 sh probes/mcap/build.sh /var/tmp/ember-mcap
sh probes/mcap/test.sh /var/tmp/ember-mcap
sh probes/mcap/tests/build-guards.sh
```

The build path must be absolute and absent. An optional absolute archive-cache
path follows it. All hashes are verified before extraction. Build commands
preserve failures and keep logs under `WORK/logs`; the installation is
`WORK/install`. No system packages, devices or running services are modified.
Temporary validation copies use the same shared dependency versions rather
than introducing an application-specific older version.

Consumers include `mcap/reader.hpp` and `mcap/writer.hpp`, define
`MCAP_IMPLEMENTATION` in one C++ translation unit, and link LZ4 and Zstd.
The private `mcap.pc` exports the headers and exact compression dependency
versions. [The consumer](tests/contract.cpp) and its [CMake setup](tests/CMakeLists.txt)
show explicit discovery from the installed prefix, without source build targets.

## Contract and limits

Three bounded CTests write and read real files with no compression, LZ4 and
Zstd. Each verifies 12 binary payloads, two channels, schema contents,
metadata, nanosecond log/publish timestamps and sequence numbers. It requires
multiple indexed chunks and the actual requested compression, then checks
file-order replay, indexed time ordering, a half-open time window, topic
filtering and reverse replay. Runtime library versions and resolved private
library paths are checked to prevent silently using a system library.

Each mode requires actual reader errors for invalid magic, a truncated footer,
a truncated chunk and corrupted chunk structure/compression framing. Shorter
output alone cannot pass. These checks do not establish general integrity
validation: upstream C++ reading does not verify all MCAP CRC fields, and this
probe does not claim detection of arbitrary payload bit flips. The files are
removed on success or a caught test failure. CTest limits each case to 30 seconds.

Build guards reject an existing work directory, relative path, invalid `JOBS`
and a corrupt archive before extraction. The C++ tests remain active in
Release builds and do not rely on disabled `assert` calls.

## Validation

On 2026-10-07 the source build and all three installed contracts passed on
EmberBSD AArch64 in an isolated VM: EMBER64 kernel `b4f718d`, NetBSD 11.0
userland, base GCC 12.5, CMake 4.3.3 and Ninja 1.13.2. The installed consumer
resolved both compression libraries from its own prefix and used the base
C++ runtime. Kernel identity refers to the separately supplied QEMU boot image,
not the guest's `/netbsd` file. The same workflow and build guards also passed on Darwin arm64
with AppleClang 21.0.0. These are software recording/replay checks, without
camera, sensor, live ROS transport, throughput or physical-board validation.

[Provenance and licensing](PROVENANCE.md) records the source pins and local work.
