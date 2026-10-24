# chrony on the common stack

This probe records the state of registry item E32: chrony 4.9 from the
unchanged pkgsrc `net/chrony` recipe (pkgsrc `fff4deb639a1`), for EmberBSD
amd64 and AArch64. No Ports overlay or patch is carried for it.
The record is AI-assisted (Claude Code, Claude Opus 5.5).

## amd64 native GCC16 package

Built on 24.10.2026 in the shared native amd64 GCC16 package root of the
development host (24 CPUs), with the root's own `mk.conf` and the pinned
export. The suggested `gnutls` option is kept, so NTS is enabled; the
`editline` dependency resolves to base libedit (`readline.h`).

```sh
cd /usr/pkgsrc/net/chrony
make MAKECONF=/etc/mk.conf MAKE_JOBS=24 package
make MAKECONF=/etc/mk.conf TEST_TARGET=check MAKE_JOBS=24 test
```

| Result | Value |
| --- | --- |
| Package | `chrony-4.9.tgz`, SHA256 `5d0b0dc49600c469390a1bf88d0280355172167a4b053440341f538a1129d2af` |
| Declared dependencies | `gcc16>=16.2.0nb1`, `gnutls>=3.8.13nb1`, `nettle>=4.0` |
| Features | `chronyd`: +CMDMON +REFCLOCK -RTC +PRIVDROP -SCFILTER -SIGND +NTS +SECHASH +IPV6 -DEBUG |
| Unit tests | 25 pass, 1 skipped (`hwclock`) |
| System tests | 17: 7 pass, 0 fail; 10 skipped (DEBUG, SCFILTER, destructive) |
| Simulation tests | 70 skipped: `clknetsim` is not available |

The system tests ran `chronyd` on the build host without the destructive
clock tests. Static analysis and Valgrind were not run for this probe.

## Installation on a clean amd64 system

Target: EmberBSD 1.0 amd64 `c5d396f` installed from its ISO in QEMU, with an
empty `/usr/pkg`. The chrony package and its 14 run-time dependencies came
from the same package root (163 MB, SHA256 checked).

- The chrony package itself requires only base libraries and `/usr/pkg/lib`.
- `gmp-6.3.0` and `gcc16-16.2.0nb5` from that root require `libgcc_s.so.1` and
  `libstdc++.so.7` under the bootstrap compiler prefix of the build host.
  Ordinary `pkg_add` refuses them, and chrony with them.
  This check used `pkg_add -f`; `libgmp.so.10` itself needs only libc.
  The defect belongs to that package set, not to chrony: those packages
  must be rebuilt with the package compiler before the set is installable.
- The run-time package depends on the full `gcc16` compiler package.
  The common rule keeps compilers out of target runtime dependencies.
- The packaged `rc.d` script starts and stops `chronyd`. The installed example
  configuration selects no source; with a pool source the daemon synchronized
  (stratum 3, leap status Normal) within a minute under QEMU TCG.
- `chronyc -c tracking` returns the 14-field CSV. A downstream time-policy
  consumer read it for 10 minutes and rejected no measurements for time.

## Remaining

- AArch64: the common cross profile needs a qualified SDK native toolset, an
  AArch64 sysroot with the GCC16 runtime (E34) and a target package database.
- The CIX P1 board root is a reduced static C cohort without shared libraries
  or pkgsrc; the package cannot run there until the board uses the common stack.
- PPS through RFC 2783 and `gpiopps` waits for GPIO017 interrupts (N36).
- An installable amd64 set needs the `gmp` and `gcc16` rebuilds above and a
  runtime-only GCC16 provider.
