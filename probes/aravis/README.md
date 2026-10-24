# Aravis for GigE Vision cameras

Registry item E33 needs Aravis for GigE Vision cameras. The common recipe
`pkgsrc/multimedia/aravis` packages the current stable line, Aravis 0.8.36
(released 26 April 2026; archive SHA256
`246deaa0042a387ff1bc00332d0fb80537ce14abde2c28d1a54c91f17adc51bf`, as
published with the GitHub release). It builds the library, `arv-tool`,
`arv-camera-test`, `arv-test` and `arv-fake-gv-camera` with glib2, libxml2,
zlib and libusb1. The GTK viewer, the GStreamer plugin, introspection and
documentation are off; packet sockets are Linux-only. This record is
AI-assisted (Claude Code, Claude Opus 5.5).

## amd64 native GCC16 package

Built on 24 October 2026 in the shared native amd64 GCC16 package root of
the development host: `make package` and `make test`.

| Result | Value |
| --- | --- |
| Package | `aravis-0.8.36.tgz`, 94 entries, SHA256 `52402da35a9ba35c09ec9be073c57724b0f0b90001373892080bf1067c0f1fd2` |
| Declared dependencies | `gcc16`, `glib2>=2.90.1`, `libusb1`, `libxml2`, `zlib` |
| Upstream tests | 7: evaluator, buffer, misc, dom, genicam and fake pass; `fakegv` fails |

`fakegv` starts a simulated camera on 127.0.0.1 and discovers it by
broadcast. The simulated camera binds its global discovery socket to
255.255.255.255, which BSD sockets reject (`Can't assign requested
address`), and the loopback interface has no broadcast. Control by address
works: `arv-tool -a 127.0.0.1 control Width Height` reads the simulated
camera, and `arv_camera_new` accepts an address. Discovery of real cameras
on an Ethernet segment is not exercised by this test. A BSD-compatible
discovery socket for the simulator and the test remain open.

## Stream reception

`arv-camera-test` received 2048x1500 Mono8 frames at a requested 9 frame/s
from the simulated camera over loopback, 30 seconds per run:

| Host and receive buffers | frame/s | incomplete frames | missing packets |
| --- | --- | --- | --- |
| Build host, `kern.sbmax` 262144, `net.inet.udp.recvspace` 41600 | 0 to 4 | most | 137534 of 725556 |
| QEMU TCG guest, same defaults | 2.1 to 3.6 | 136 to 155 | 297 to 335 thousand |
| QEMU TCG guest, `kern.sbmax` 67108864, `recvspace` 33554432 | 7.9 | 0 | 0 |

With the default `kern.sbmax`, Aravis cannot even set its 256 KiB socket
buffer. GigE Vision reception at this rate needs a larger `kern.sbmax`
and UDP receive space. The guest values are not a hardware measurement;
its 7.9 frame/s is the emulated CPU limit.

An application linked in the package root also needs `gettext-lib`:
`libgio-2.0.so` there uses base `libintl.so.1`, while the link selects
`libintl.so.8`, and the linker reports a possible conflict.

## Remaining

- AArch64 package: the common cross profile and a qualified SDK toolset.
- Daheng ME2P-1230 on the board for 30 minutes without lost frames.
- The simulator discovery on BSD and the `fakegv` test.
