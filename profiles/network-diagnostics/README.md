# Network diagnostics profile

Cross-built CLI capture, analysis and load tools for EmberBSD boards.
This profile owns the first stage of the network diagnostics kit:
basic packet capture and analysis, a load generator and a native HCI
recorder. Scope and acceptance criteria live in the EmberBSD knowledge
base (registry item R10).

## Contents

- `mk.conf` — package options for the profile. Include it after the
  common build-tools cross profile and the private host bootstrap
  MAKECONF. Wireshark and lldpd use the pkgsrc suggested options:
  the Qt GUI, Lua and the lldpd SNMP subagent are on. For a light
  build, set `PKG_OPTIONS.wireshark=-qt6 -lua` and
  `PKG_OPTIONS.lldpd=-snmp`.
  The file also applies the common CMake cross settings to CMake
  consumers, pins `NATIVE_CC` for libgpg-error/libgcrypt build-time
  generators, and routes script interpreter/awk substitution to target
  base paths (`TOOLS_PLATFORM.sh=/bin/sh`, `TOOLS_PLATFORM.awk=/usr/bin/awk`).
- `src/hcisnoop.c` and `src/build-hcisnoop.sh` — a small C recorder for
  the native NetBSD netbt HCI socket tap. It writes BTSnoop files that
  Wireshark opens as "Bluetooth HCI H4". It has no Linux BlueZ
  dependency: packet direction comes from the `SCM_HCI_DIRECTION`
  control message and timestamps from `SO_TIMESTAMP`.
- `security/mozilla-rootcerts` comes from the common cross change
  (`profiles/common-build-tools/patches/mozilla-rootcerts-cross-tools.patch`).
  The shipped target script uses `/bin/sh` and `/usr/bin/awk`.
- `pkgsrc/net/wireshark` (shared overlay) — the upstream recipe plus EmberBSD cross
  additions: the lemon parser generator is taken from the host bootstrap
  prefix instead of being cross-compiled, and the libssh-based extcaps
  (sshdump, ciscodump, wifidump) are disabled until their cross link
  against the builtin heimdal GSS libraries is repaired.

## Packages

Built from the prepared pkgsrc export through the common cross profile:

| Package | Version | Purpose |
|---|---|---|
| libpcap | 1.10.7 | BPF capture library |
| tcpdump | 4.99.6 | capture and offline analysis |
| iperf3 | 3.21 | TCP/UDP load, throughput, loss and jitter |
| wireshark (Qt GUI and CLI: dumpcap, tshark, capinfos, editcap, mergecap) | 4.6.8nb1 | PCAPNG recording, dissection and trace processing |
| lldpd | 1.0.21nb1 | LLDP chassis advertisement and neighbor discovery, SNMP subagent |
| arp-scan | 1.9nb7 | ARP host discovery on the local network |
| mtr | 0.96nb1 | combined traceroute/latency reports |
| fping | 5.5 | parallel availability probing |

`pkgsrc/net/arp-scan` (shared overlay) additionally carries portability patches: the
bundled gnulib getopt header is dropped in favor of the NetBSD system
header, `getopt_long_only` (a glibc extension) is replaced with
`getopt_long`, the configure probe checks the function the tool now
uses, and the perl helper scripts stay out of the cross-built board kit.

- tcpreplay | 4.4.4 | pcap replay with rate control and loops
- libserialport | 0.1.2 | serial port access library with a new NetBSD backend
- libsigrok (demo driver) | 0.5.2 | signal acquisition library for instruments
- sigrok-cli | 0.7.2 | command-line acquisition client
- libzip | 1.12.1 | shared zip library and command-line tools
`pkgsrc/comms/libserialport` (shared overlay, in every export) is the first pkgsrc recipe for the
sigrok library, plus a NetBSD backend: the FreeBSD termios enumeration
lists dial-out (dty) devices, falls back to stat for DT_UNKNOWN dirents,
initializes the scan return code, and the FreeBSD libusb20 metadata path
compiles only where port metadata exists (on NetBSD NO_PORT_METADATA is
set, so `sp_list_ports` works without libusb). The `sp-list` helper in
`src/` enumerates ports through the public API.

`pkgsrc/devel/libsigrok` and `pkgsrc/misc/sigrok-cli` (shared overlay) are the first
pkgsrc recipes for the sigrok acquisition stack; the board kit builds
only the demo driver (no instrument hardware attached yet), with glib2
and the [common libzip recipe](../../pkgsrc/archivers/libzip).
The common profile exports this one recipe. It keeps the upstream regression
tests and their test dependencies. The former profile-only recipe is removed.

The tcpreplay recipe overlay carries three portability patches: the
bundled libopts headers must not redefine the false/true keywords
(present since C23), and configure must respect a preset POSIX_SHELL so
cross builds stop embedding the build-host bash into every binary.
libpcap is supplied through a private staging directory with the target
layout (EMBERBSD_NETDIAG_STAGELIBPCAP in the private MAKECONF); the
recipe's own --with-libpcap probes build-host paths and is filtered out
in cross builds. libnet is not needed by this release.

Private build products (packages, work directories, logs) stay outside
Git, in the private build directory of the development host.

## Cross support note

`security/mozilla-rootcerts` (a gnutls dependency) ships a script that
uses standard NetBSD base utilities at runtime. The common cross
profile's run-tool whitelist was extended for exactly these verified
base paths; see `profiles/common-build-tools/patches/pkgsrc-cross-packages.patch`.
The substituted utility paths inside the shipped `sbin/mozilla-rootcerts`
script still point at build-host wrappers, so re-extracting certificates
on the target with that script is not supported; the packaged
`cacert.pem` itself is generated at build time and ships normally.
Regenerate the pkgsrc export after picking up that patch change.

## Validation status

See the EmberBSD knowledge base for the current acceptance level of
each tool (VM versus board, wired Ethernet versus Wi-Fi/Bluetooth).
This profile was validated on the Raspberry Pi 5 stand with wired
`cemac0`; the first validation date and receipts are recorded there.
