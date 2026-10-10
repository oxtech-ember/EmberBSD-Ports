# Network diagnostics profile

Cross-built CLI capture, analysis and load tools for EmberBSD boards.
This profile owns the first stage of the network diagnostics kit:
basic packet capture and analysis, a load generator and a native HCI
recorder. Scope and acceptance criteria live in the EmberBSD knowledge
base (registry item R10).

## Contents

- `mk.conf` — package options for the profile. Include it after the
  common build-tools cross profile and the private host bootstrap
  MAKECONF. Wireshark is reduced to the CLI kit: HTTP/2 dissection is
  kept; the Qt GUI, Lua, HTTP/3, iLBC, spandsp and documentation are
  disabled. pkgsrc options are additive, so each suggested option is
  negated explicitly to keep Qt and X11 out of the dependency closure.
  The file also applies the common CMake cross settings to CMake
  consumers, pins `NATIVE_CC` for libgpg-error/libgcrypt build-time
  generators, and routes script interpreter/awk substitution to target
  base paths (`TOOLS_PLATFORM.sh=/bin/sh`, `TOOLS_PLATFORM.awk=/usr/bin/awk`).
- `src/hcisnoop.c` and `src/build-hcisnoop.sh` — a small C recorder for
  the native NetBSD netbt HCI socket tap. It writes BTSnoop files that
  Wireshark opens as "Bluetooth HCI H4". It has no Linux BlueZ
  dependency: packet direction comes from the `SCM_HCI_DIRECTION`
  control message and timestamps from `SO_TIMESTAMP`.
- `recipes/security/mozilla-rootcerts` — the upstream recipe plus an
  EmberBSD SUBST that keeps `/bin/sh` and `/usr/bin/awk` in the shipped
  target script instead of build-host interpreter paths.
- `recipes/net/wireshark` — the upstream recipe plus EmberBSD cross
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
| wireshark (CLI: dumpcap, tshark, capinfos, editcap, mergecap) | 4.6.8nb1 | PCAPNG recording, dissection and trace processing |

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
