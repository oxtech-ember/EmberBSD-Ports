# Zenoh and ROS 2 integration

Provide a native Zenoh-Pico package and an independent device-to-ROS example.
The device side runs C on EmberBSD; the ROS side uses C++ on Ubuntu 24.04
with ROS 2 Jazzy. This does not port ROS 2 or rmw_zenoh to EmberBSD.

Use the Zenoh-Pico revision recorded in the [Ports recipe](../../pkgsrc/local-robotics/zenoh-pico/files/SOURCE).
Both sides use the same version. A direct TCP client-to-peer connection avoids a router
dependency for this two-participant demonstration. Discovery is an explicitly
configured listener and endpoint; multicast discovery is not an acceptance claim.
The device listens as a peer; the bridge connects as a client, which enables
the upstream automatic reconnect path. The ROS bridge uses rclcpp and the supported ROS middleware on its own host.
It translates application messages, not rmw_zenoh wire conventions.

Ports owns the pkgsrc library recipe and profile. Examples owns the shared C
wire format, simulated controller, typed ROS messages, C++ bridge, ROS test
client, build instructions and checks. No code is placed in the private wiki.

## Contract

Use three fixed Zenoh keys under ember/robotics/v1/demo: state, command, ack.
Each message is exactly 44 bytes, big-endian: magic EBR1, kind, status, two
zero reserved bytes, boot ID, device monotonic milliseconds, command ID,
measured temperature, setpoint, applied-command count. Integer fields are
64, 64, 64, signed 32, signed 32, unsigned 32 bits respectively.
Device state is published every 250 ms; temperature is explicitly simulated.
The only command changes a simulated setpoint in [0, 100000] millidegrees.
No actuator or privileged device operation is present.

Commands echo a recent device timestamp and boot ID. The device rejects a
wrong boot ID, a future timestamp, age over 1000 ms, a non-increasing command
ID, or an out-of-range setpoint without changing state. Repeated commands
receive a rejection acknowledgement. Counter exhaustion rejects further
commands instead of wrapping. A restart chooses a new boot ID; commands
from an earlier process cannot be applied to the new controller.

The ROS side exposes typed state, command, and acknowledgement messages.
Use reliable, volatile KeepLast(10) ROS QoS, no retained command history.
Zenoh puts use drop congestion control over TCP. A Ports patch also applies
the existing socket timeout to TCP writes; DROP alone only avoids TX-lock waiting.
Acknowledgements are sent after releasing the controller state mutex. Publication
success is not proof of application: only the device acknowledgement and
updated count prove that. No automatic command retry or exactly-once promise.
After disconnect, restore telemetry and send a newly constructed command.
An old command must still be rejected after reconnect.

## Evidence and limits

Require native package build/install, protocol regression tests, real Zenoh
traffic between EmberBSD and Linux, ROS discovery and type checks, command
acknowledgement, duplicate/expired command rejection, and reconnect exercise.
Pin upstream sources and record package hashes and actual ROS environment.
Keep logs and VM images outside Git. Existing desktops remain unchanged.

This establishes simulated-device integration on the tested VMs. Physical
controllers, multi-device analysis, authentication/TLS, hard real-time,
hardware safety, other ROS distributions/RMWs and automatic discovery require
separate evidence. The documented TCP endpoint is for a trusted test network.
