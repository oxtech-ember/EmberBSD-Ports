# Robotics: native Zenoh-Pico and ROS 2 integration

This profile packages **Zenoh-Pico 1.10.1** for EmberBSD using pkgsrc.
The [independent Examples scenario](https://github.com/oxtech-ember/EmberBSD-Examples/tree/main/robotics/zenoh-ros2)
connects a simulated C controller to typed ROS 2 Jazzy messages on Ubuntu 24.04.
ROS 2 itself is not installed on EmberBSD.

The package provides the shared C library, headers, CMake and pkg-config
metadata, upstream license/notice and an installed provenance file. It does
not start a daemon. The example uses a TCP client-to-peer connection without
a separate router. Its ROS bridge uses `rclcpp` with `rmw_fastrtps_cpp`;
it does not emulate `rmw_zenoh` discovery or serialization.

## Additional native libraries

[OpenCV 5.0.0, Eigen 5.0.1 and gpsd 3.27.5](../../probes/robotics-foundations/README.md)
passed native installed-consumer checks for CPU vision, numerical computation
and a synthetic GNSS stream. These remain source probes, with a local OpenCV
AArch64 CPU-detection patch; they are not yet pkgsrc packages. Physical camera
and receiver support is not established by these tests.

## Source and patches

- Upstream: https://github.com/eclipse-zenoh/zenoh-pico, release 1.10.1.
- Revision: `e1ab223a28aaebb5dec1e70d98eab152332f777a`.
- Archive SHA256: `b662b7f6b9094684311a22748b3d45a595fad62d2f7793283f43e553b2175ddc`.
- pkgsrc pin: `fff4deb639a1a640476203c80f752fb77b6cb14b`, pkgsrc-2026Q3.
- Upstream BSD platform implementation; no new OS abstraction is introduced.
- The test harness uses explicit build parallelism because BSD make rejects
  the original bare `-j`. Its nested shared-library test selects its own library
  when pkgsrc suppresses build RPATH.
- The POSIX runtime patch applies the existing socket timeout to TCP sends
  on both outgoing and accepted sockets. DROP congestion control alone only
  avoids transmit-lock waiting. Examples includes filled-buffer regressions
  for both paths, with an independent two-second alarm.
- Local patches are AI-assisted, not submitted or accepted upstream.

Zenoh-Pico is dual-licensed EPL-2.0 OR Apache-2.0. The recipe selects the
Apache-2.0 alternative recognized by pkgsrc and preserves upstream notices.
No stable EmberBSD SDK ABI is promised by this third-party library package.
The example requires the exact selected version on both endpoints.

## Native build

On the target OS/architecture, install the C toolchain, Git, CMake, Ninja,
Bash and pkg_tools. pkgsrc resolves missing dependencies normally. The build
uses CMake/C; it does not require project-owned Python tooling.

```sh
git clone --recurse-submodules --shallow-submodules \
  https://github.com/oxtech-ember/EmberBSD-Ports.git
cd EmberBSD-Ports
work=/var/tmp/ember-robotics-build
mkdir "$work"
# Provide a verified source-data export at "$work/pkgsrc". See the root README.
mkdir "$work/work" "$work/distfiles" "$work/packages"
cat > "$work/mk.conf" <<CONF
.if defined(BSD_PKG_MK)
WRKOBJDIR= $work/work
DISTDIR= $work/distfiles
PACKAGES= $work/packages
MAKE_JOBS= 2
CMAKE_GENERATOR= ninja
.endif
CONF
make -C "$work/pkgsrc/local-robotics/zenoh-pico" \
  MAKECONF="$work/mk.conf" package
make -C "$work/pkgsrc/local-robotics/zenoh-pico" \
  MAKECONF="$work/mk.conf" test
```

Use an absolute unused directory without whitespace. The export helper adds
all local categories, including `local-ai` and `local-robotics`. It rejects an
existing destination, an unexpected submodule revision or an upstream category
collision. Keep settings in `mk.conf` so dependency builds retain them.
The recipe's test target selects its build library through `LD_LIBRARY_PATH`.
Run tests on an otherwise idle guest with an active loopback interface. The
suite runs serially because upstream timing assertions have narrow tolerances.

## Install, check and remove

An isolated installation uses the ordinary package tools:

```sh
mkdir "$work/runtime" "$work/pkgdb"
pkg_add -K "$work/pkgdb" -p "$work/runtime" \
  "$work/packages/All/zenoh-pico-1.10.1.tgz"
pkg_admin -K "$work/pkgdb" check zenoh-pico
```

Use `$work/runtime` as the example's `CMAKE_PREFIX_PATH` and its `lib` directory
in `LD_LIBRARY_PATH`. Remove the test installation with:

```sh
pkg_delete -K "$work/pkgdb" zenoh-pico-1.10.1
```

For system installation, an administrator uses `pkg_add` without the private
prefix/database flags. The default prefix is `/usr/pkg`. Packages must match
the target OS and architecture. This profile does not publish a signed pkgin
channel or install a controller service.

## Validation boundary

Verified on 2026-10-06: QEMU/HVF AArch64, EmberBSD EMBER64 kernel at
`b4f718dabd085ed117a24f84d8558e4a43091dc0`, NetBSD 11.0 userland, one
virtual CPU and 2 GiB RAM. GCC 12.5.0, CMake 4.3.3 and Ninja 1.13.2.
The final recipe passed all 42 upstream tests (111.14 seconds). The installed
package passed the protocol and both TCP send-timeout tests, removal,
reinstallation and `pkg_admin check` (188 files). Binary package SHA256:
`4b61b479310bee4d15526e97b612201dc7ce3d6f7129e52644b156a27c06cabd`.

The installed EmberBSD controller also passed the complete ROS exchange and
reconnection scenario against a separate Ubuntu 24.04.5 AArch64 / Jazzy VM.
That host used rclcpp 28.1.22 and rmw_fastrtps_cpp 8.4.4. The accepted-command
count went from 0 to 1 before the pause and to 2 after recovery; rejected
commands did not increment it. A missing peer separately produced failure
without a `SUCCESS` marker. No physical board was used.

The companion example checks serialization, rejection of stale/duplicate
commands, real ROS topic discovery and typed messages, acknowledgements and
state changes. Its reconnection test stalls the bridge for 22 seconds, resumes
the same process and requires fresh telemetry and a newly accepted command.
An old command must remain rejected. Publication success is not execution proof.

The demonstration uses simulated devices. It does not establish physical
sensor/actuator support, a multi-board analysis pipeline, real-time guarantees,
authentication/TLS, physical cable-disconnection recovery, other ROS
configurations or automatic Zenoh discovery. See Examples for the exact
message contract, QoS, test invocation and limits.
