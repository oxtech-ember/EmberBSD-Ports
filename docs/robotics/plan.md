# Zenoh and ROS 2 implementation plan

Execution: superpowers:executing-plans, inline implementation with one final
independent review. Project instructions authorize checks, commits and pushes.

Goal: install Zenoh-Pico on EmberBSD and exchange typed telemetry and commands
with ROS 2 Jazzy through an explicit C++ bridge.

Spec: [design.md](design.md). Stack: C11, C++17, CMake, pkgsrc, shell, rclcpp.
ROS upstream build tooling uses Python; no project-owned Python is introduced.

## Review focus

- A queued or repeated command must not change the controller after expiry.
- State and acknowledgements must not race with transport callbacks or teardown.
- Malformed, truncated, oversized and wrong-key payloads must not reach control.
- A failed build, lost peer or timeout must not produce a successful smoke result.
- The package overlay must preserve local-ai and reject upstream path collisions.

## Tasks

1. Native package: add pkgsrc/local-robotics/zenoh-pico with immutable source,
   distinfo, licenses and development files. Generalize prepare-pkgsrc.py to
   overlay each local category; extend its fixture test to cover both categories
   and collision rejection. Build, run upstream tests, package and install.
2. Device example: add robotics/zenoh-ros2 in Examples. Write failing C tests
   for the 44-byte codec and command acceptance rules; implement protocol and
   controller state. Add a C Zenoh transport wrapper and simulated controller.
   Compile against the installed package and exercise a real peer connection.
3. ROS bridge: add one ament package with typed State, Command and Ack messages,
   bridge.cpp and probe.cpp. Build on the isolated Ubuntu/Jazzy VM, verify
   discovery, state, valid/duplicate/expired commands, and reconnect. Bound
   test timeouts and preserve failures. Document exact supported topology/QoS.
4. Delivery: record versions and artifact hashes, write Ports/Examples usage,
   update the Russian wiki and R5 boundary, review once, fix findings and
   publish scoped commits. Keep VM assets and logs outside Git.

## Completed validation

All implementation tasks are complete. The native package passes 42 upstream
tests and three installed-example tests. pkg_tools install, remove, reinstall
and integrity checks pass. EmberBSD-to-Jazzy telemetry, command acknowledgement,
rejection and recovery pass on two independent VMs. An absent peer fails cleanly.
One final independent review identified ACK publication under the state mutex
and unbounded TCP send waiting. Both were fixed and exercised by real
filled-buffer regressions; the original library failed the timeout regression.
The profile and Examples README record versions and limits. Physical-device
acceptance and signed package distribution remain outside this first scenario.
