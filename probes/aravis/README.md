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
| Package | `aravis-0.8.36nb1.tgz`, 94 entries, SHA256 `a202c154478b6beb42374d12c8c5b5fc3c0185a66c46680a1ce71b18fcb86168` |
| Declared dependencies | `gcc16`, `glib2>=2.90.1`, `libusb1`, `libxml2`, `zlib` |
| Upstream tests | 7 of 7 pass, including `fakegv` |

## Discovery on an interface without broadcast

`fakegv` starts a simulated camera on 127.0.0.1 and finds it by discovery.
Aravis sends discovery to the limited broadcast 255.255.255.255 and uses
the interface broadcast address only when that send fails. The BSD
loopback has no broadcast: Aravis records its own address as broadcast
address, the send succeeds, and the packet never reaches the simulator.
`patch-src_arvgvinterface.c` sends discovery for such an interface to that
recorded address. Interfaces with a broadcast address keep the upstream
limited broadcast.

In an EmberBSD 1.0 amd64 `c5d396f` guest, `arv-tool` found a simulated
camera as follows (the simulator's 255.255.255.255 socket fails to bind on
BSD in both cases; its unicast GVCP socket on an Ethernet interface still
receives the broadcast):

| Package | Camera on `lo0` | Camera on `wm0` |
| --- | --- | --- |
| `aravis-0.8.36` | not found | found |
| `aravis-0.8.36nb1` | found | found |

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

## AArch64 Clang cross package

Built on 27 October 2026 on macOS arm64 with the common cross profile, the
native Clang/LLVM 23.1.4 Ports prefix and an SDK sysroot from EmberBSD
`b36583d38bf`. `gnome.mkenums_simple()` and `gnome.compile_resources()` run
build host programs. The target `glib-2.0.pc` names target programs in the
sysroot. In a cross build, the recipe adds native `glib2` and `glib2-tools`
as tool dependencies and gives their programs to Meson. Native builds are
unchanged.

| Result | Value |
| --- | --- |
| Package | `aravis-0.8.36nb1.tgz`, 94 entries, SHA256 `33e090994290984fcf2d52afb7c5418873a221595fb4c3b1c17340ee24c6bd13` |
| Declared dependencies | `glib2>=2.90.1`, `libusb1>=1.0.9`, `libxml2>=2.14.6nb2`, `zlib>=1.3.2nb1` |
| Programs | `arv-tool-0.8`, `arv-camera-test-0.8`, `arv-test-0.8`, `arv-fake-gv-camera-0.8`: AArch64 PIE; need `libaravis-0.8.so.0`, GLib libraries and `libc.so.12` |

The upstream tests were built but not run: they need the target. The
package was not run on a target.

## AArch64 target in the C locale

Built on 4 November 2026 from Ports `a05d15e5` with the common cross
profile on a sysroot from EmberBSD `77cc52ebd1c5`. Checked in an EmberBSD
aarch64 guest from the same sets (QEMU HVF, 2 vCPU, 2 GiB, full base with
shared libraries). The guest runs in the C locale: `locale charmap` gives
`646`.

Since `glib2` nb2, GLib uses the common GNU libiconv. GNU libiconv does not
know `646`. GLib 2.90.1 finds codeset aliases only in a `charset.alias`
file, and nothing installs this file. Each GLib program that parses
options then stops: "Option parsing failed: Conversion from character set
“646” to “UTF-8” is not supported". `glib2` nb3 resolves the NetBSD names
with the gnulib table (`patch-glib_libcharset_localcharset.c`).

| Packages | `arv-tool-0.8 --version` | `arv-fake-gv-camera-0.8 -i lo0` | `arv-camera-test-0.8` |
| --- | --- | --- | --- |
| `glib2-2.90.1nb2`, `aravis-0.8.36nb1` | 0.8.36 | stops at option parsing | stops at option parsing |
| `glib2-2.90.1nb3`, `aravis-0.8.36nb1` | 0.8.36 | starts | receives frames |

The 30-minute run used `arv-fake-gv-camera-0.8 -i 127.0.0.1` with its
default 512x512 Mono8 at 25 frame/s, and `arv-camera-test-0.8 -n 127.0.0.1
--duration=1800` in the same guest. `kern.sbmax` was 67108864 and
`net.inet.udp.recvspace` was 33554432. `arv-tool-0.8` found the simulator
and read its features before the run.

| Result | Value |
| --- | --- |
| `glib2-2.90.1nb3.tgz` | SHA256 `135bf8aa30a5bb8f51e326c153dac80865692ec5526cbb7bd816cd54eca912fd` |
| `aravis-0.8.36nb1.tgz` | SHA256 `a2e33e8d8aa6f2b3f581e9a859912a3998dca529708291bfad5cf6eb25313c83` |
| Completed frames | 44991 in 1800 s, 25.0 frame/s |
| Received packets | 8773245, 11866286268 bytes |
| Failures, missing frames, missing packets, resends | 0 |

The run used packages from a work tree that differed from `a05d15e5` only
in a patch comment. Their payload files are byte-identical to the packages
above.
The guest values are not a hardware measurement.

## Remaining

- Daheng ME2P-1230 on the board for 30 minutes without lost frames.
- Offering the discovery patch upstream.
