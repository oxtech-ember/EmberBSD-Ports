# PTPd for a GigE Vision PTP master

Registry item N37 needs a PTP master with software timestamps for a GigE
Vision camera. The common recipe `pkgsrc/net/ptpd` packages PTPd from the
head of the upstream 2.3.1 branch, commit
`d27a6e02c1191e07ce8dcdfa1d3f954e01f2d983` (5 September 2018; the
program reports 2.3.2). The recipe fetches the archive by the full commit
hash; its SHA256 is
`695e66545abfd418291fd3129f1615cdb6b71c652f4d910fd69b67dc1d4ad569`.
FreeBSD `net/ptpd2` fetches the short reference `d27a6e0`; its distinfo
records SHA256
`9384968100d40d49aa2cf923ea5da51dacf8270d8e6350d64f887e9f30976524`.
On 27 October 2026 GitHub resolved the short reference to the full hash
and named the top directory after it, so that archive changed. The two
archives differ only in the top directory name. Net-SNMP support is off.
This record is AI-assisted (Claude Code, Claude Opus 5.5).

## Patches

- `patch-configure.ac`: `test ... = ...` instead of the `==` bashism that
  the pkgsrc portability check rejects; `configure` is regenerated.
- `patch-src_dep_iniparser_iniparser.c`: ctype calls take an
  `unsigned char` value. A UTF-8 byte in a configuration comment is a
  negative `char`; on EmberBSD `ptpd2 -k` crashed with SIGSEGV on such a
  comment (exit 139) and accepts it after the patch.

## amd64 native GCC16 package

Built on 24 October 2026 in the shared native amd64 GCC16 package root of
the development host.

| Result | Value |
| --- | --- |
| Package | `ptpd-2.3.1nb1.tgz`, 9 files, SHA256 `706f046e9555e282bb10535812b6b86c07d7ab1110bad24e7af5f8d8c7b29fea` |
| Run-time requirements | base `libc`, `libm` and `libpcap`; declared `gcc16` |
| Compiler diagnostics | 36 inherited GCC16 warnings, including one `-Warray-bounds` (subscript 2 of `uint32_t[1]`) to review |
| Upstream tests | none in the release |

In an EmberBSD 1.0 amd64 `c5d396f` QEMU guest, `ptpd2 -k` accepted a
master-only configuration with timing ACLs, `clock:no_adjust` and log and
statistics files. Started on `lo0`, it entered the listening state and
then master after the announce timeout, and shut down on SIGTERM. No slave
was synchronised; this is not a timing measurement.

## AArch64 Clang cross package

Built on 27 October 2026 on macOS arm64 with the common cross profile, the
native Clang/LLVM 23.1.4 Ports prefix and an SDK sysroot from EmberBSD
`b36583d38bf`.

| Result | Value |
| --- | --- |
| Package | `ptpd-2.3.1nb1.tgz`, 9 files, SHA256 `9117c799ca18fe92120c6141ffbeec6fcf98c0017ff24a379cee33c1104235d1` |
| Program | `sbin/ptpd2`: AArch64 PIE, interpreter `/libexec/ld.elf_so`; needs `libpcap.so.10`, `libm.so.0` and `libc.so.12` |
| Compiler diagnostics | 20 Clang warnings, none treated as errors |

The package was not run on a target. The reduced CIX P1 root is static
and has no dynamic loader or shared libraries.

`ptpd-2.3.1nb2` was built on 3 November 2026 from an export of Ports
`6f749a30` on the sysroot of OS `77cc52ebd1c5`:

| Result | Value |
| --- | --- |
| Package | `ptpd-2.3.1nb2.tgz`, 9 files, SHA256 `87dbae5f552677a6b8468b46f89429ca0a03eca3f5ae1477cd2ab116a2006947` |
| Program | `sbin/ptpd2` needs `libpcap.so.12`, `libm.so.0` and `libc.so.12`; run path `/usr/pkg/lib` |
| Kernel NTP state | no write as `PTP_MASTER`, `PTP_PASSIVE` and `clock:no_adjust` `PTP_SLAVE` (`check-ntp-owner.sh`, below) |
| Service | the rc.d script starts it, it detaches and writes its PID to `/var/run/ptpd2.lock`; `status` and `stop` work |
| Removal | `pkg_delete` removes it and keeps `/usr/pkg/etc/ptpd2.conf` |

It was installed with `pkg_add` in two aarch64 guests booted from the
sets of that OS. The package installs nothing into `/usr/pkg/etc`, so on a
base with no other packages the directory is missing until the
configuration is written.

## Service

The package installs `share/examples/rc.d/ptpd2`. It reads
`ptpd2_config` from `/etc/rc.conf` (default `${PKG_SYSCONFDIR}/ptpd2.conf`)
and uses the default lock file `/var/run/ptpd2.lock` as its PID file, so the
configuration must not set `global:lock_file` or `global:auto_lockfile`.
In the same guest with `ptpd2=YES`, the script:

- refused to start without the configuration file;
- started the daemon and reported its PID with `status`;
- refused a second start while it ran;
- stopped it and removed the lock file;
- started it at boot after `NETWORKING`, and it entered `PTP_MASTER`.

Since nb2 the script requires `ntpd` and `chronyd`: a master starts after
the daemon that disciplines the clock, which may still be synchronising.
Without chrony, `rcorder(8)` warns that `chronyd` has no provider and exits
1 (`/etc/rc` records that status) and keeps the order of the other scripts.

## Kernel NTP state and the clock owner

On a host where chronyd disciplines the clock, ptpd2 serves that clock as a
PTP master and must leave the clock and the kernel NTP state to chronyd.
In PTPd 2.3.1 only these calls change them:

| Call | Path | Guard before the patch |
| --- | --- | --- |
| `ntp_adjtime` `MOD_FREQUENCY`, `adjtime`, `clock_settime` | servo, drift restore and clock step | `clock:no_adjust` (`adjFreq_wrapper`, `restoreDrift`, `updateClock`) |
| `ntp_adjtime` `MOD_TAI`, `MOD_MAXERROR`/`MOD_ESTERROR`, `MOD_STATUS` (`STA_UNSYNC`, `STA_INS`, `STA_DEL`) | clock status hook `ptpServiceClockUpdate` (`src/timingdomain.c`) | none: it runs whenever a status update is pending |

A status update becomes pending in a slave (servo update, UTC offset or
leap flags from the master) and in a master-only port that drops to
`PTP_PASSIVE` behind a better master announcing the PTP timescale. Both
happened with `clock:no_adjust` set. `patch-src_timingdomain.c` keeps
the update pending unless the port is a slave that may adjust the clock;
an adjusting slave behaves as before.

The check runs on the target, next to chronyd, with a second host that
drives ptpd2 into the state under test:

- `ntptrace.c` is an `LD_PRELOAD` shim. It logs every `ntp_adjtime` call
  with nonzero modes and every `adjtime`, `settimeofday` and
  `clock_settime` call, with the requested values, and counts the reads.
- `ntpstate.c` prints or sets the kernel NTP state (status, maxerror,
  esterror, TAI offset).
- `check-ntp-owner.sh SHIM CONFIG SECONDS WORKDIR STATE [PTPD2]` runs
  ptpd2 under the shim and fails when it made such a call. The run counts
  only if ptpd2 reached `STATE` and read the NTP state through the shim: a
  port that stays `PTP_MASTER` has nothing to write, patched or not.
- `check-ntp-markers.sh CONFIG SECONDS WORKDIR STATE [PTPD2]` is the check
  for a static ptpd2, which the shim cannot enter. It sets markers (TAI
  offset 11 s, esterror 4242 us, maxerror 100000 us) and fails when one
  changes; without writes the kernel only grows maxerror. It refuses to
  run next to chronyd or ntpd, which rewrite the markers.

Build the helpers with the cross compiler of the target SDK, for example
`aarch64--netbsd-clang --sysroot=SYSROOT -O2 -Wall -Wextra -Werror -o ntpstate ntpstate.c`
and `... -fPIC -shared -o ntptrace.so ntptrace.c`.

Run on 2 November 2026 (UTC) in two EmberBSD aarch64 guests (QEMU with
HVF on an Apple M-series host, 1 vCPU each, base `28f4d84`, kernel
`EMBER64`). The first guest ran chronyd 4.9 synchronised to public NTP
servers (leap status `Normal`); a QEMU `dgram` link joined the second
`vioif1` of both guests. The kernel TAI offset was set to 11 s before
each run, so a write is visible. Each run took 90 s. Both ptpd2 builds
come from the recipe work tree, configured and built with the SDK cross
compiler and sysroot of OS `2e5ec07` outside pkgsrc; the unpatched one has
`patch-src_timingdomain.c` reversed. The unpatched package
`ptpd-2.3.1nb1` for that sysroot made the same writes.

| ptpd2 on the chronyd host | Peer | State | Writes, unpatched | Writes, patched |
| --- | --- | --- | --- | --- |
| master-only, `clock:no_adjust` | slave | `PTP_MASTER` | 0 | 0 |
| master-only, `clock:no_adjust` | master, priority1 1, class 6, UTC offset 37 | `PTP_PASSIVE` | 2: TAI 37; maxerror 0, esterror 0 | 0 |
| slave-only, `clock:no_adjust` | the same master | `PTP_SLAVE` | 2: TAI; maxerror and esterror −3236 us | 0 |

The kernel TAI offset stayed 11 s with the patched build. With the
unpatched build the passive master set it to 37 s. A master-only port
announces clock class 13 and the arbitrary timescale, so behind such a
master a passive port has nothing to write. With `ptpengine:utc_offset=37`
and `ptpengine:utc_offset_valid=Y` on the master-only port, the same peer
caused no write even unpatched: only a changed UTC offset or leap flags
raise the update. The repeated runs with the final `check-ntp-owner.sh`
exited 0 for the patched build in both states, 1 for the unpatched
no_adjust slave, and 2 for a run that never reached the expected state.

### One hour next to chronyd

On 2 November 2026, 22:10 to 23:10 UTC, in the same pair of guests. The
first guest booted with `ptpd2=YES` and `chronyd=YES`: rc.d started
chronyd, then ptpd2 as a master-only port on `vioif1` with
`clock:no_adjust`, `ptpengine:utc_offset=37` and
`ptpengine:utc_offset_valid=Y`, under the `ntptrace.so` shim (patched build
as above). The second guest ran a slave-only ptpd2 that disciplined its
own clock and logged every offset. Software timestamps in QEMU guests: the
numbers bound this setup, not a board.

| Result | Value |
| --- | --- |
| chronyd | leap status `Normal` in 324 of 324 samples (every 10 s); kernel status 0, TAI 0, esterror 0.8 to 3.6 ms |
| ptpd2 master | `PTP_MASTER` throughout; no clock or NTP state write from boot to stop, 4560 reads |
| Slave state | `PTP_SLAVE` throughout, 6777 offsets |
| Slave offset, absolute | median 44 us, 95th percentile 0.73 ms, maximum 13 ms; 2.9 % above 1 ms |
| Same, without 120 s after each offset above 1 ms | median 29 us, 95th percentile 0.21 ms, maximum 0.96 ms |
| One-way delay | median 245 us, maximum 559 us; ping RTT 0.23 to 0.96 ms |

The offsets above 1 ms came in short bursts that the servo removed within
about a minute; at a 10 s resolution they did not follow the host load.
After the boot chronyd slewed 0.15 s at 500 ppm for 5 minutes and the
slave settled 12 minutes after its start.

### Static ptpd2 on a current base

A board root without shared libraries runs a static ptpd2 built from the
recipe archive and patches (`configure`, `-static`, lld). On 3 November
2026 (UTC) two such builds, with all recipe patches and without
`patch-src_timingdomain.c`, were made with Clang 23.1.4 on the sets of OS
`77cc52ebd1c5` (`libpcap.so.12` in the base; no `libgcc.a`, and the
static link needs none). They ran in two aarch64 guests booted from those
sets, set up as above but without chronyd, under `check-ntp-markers.sh`,
90 s per run:

| ptpd2 under test | Peer | State | Unpatched | Patched |
| --- | --- | --- | --- | --- |
| master-only, `clock:no_adjust`, UTC offset 37 valid | slave | `PTP_MASTER` | markers kept | markers kept |
| master-only, `clock:no_adjust` | master, priority1 1, class 6, UTC offset 37 | `PTP_PASSIVE` | written: TAI 37, esterror 0, maxerror 44500 us | markers kept |
| slave-only, `clock:no_adjust` | the same master | `PTP_SLAVE` | written: esterror 5706 us, maxerror 50206 us | markers kept |
| master-only, `clock:no_adjust`, UTC offset 37 valid | the same master | `PTP_PASSIVE` | not run | markers kept |

Without writes maxerror grew from 100000 to 150000 or 150500 us in each
run.

The package `ptpd-2.3.1nb2` for that base ran in the same guests under
`check-ntp-owner.sh` with the shim built for that base, 90 s per run.
With the configurations above it made no clock or NTP state write as
`PTP_MASTER`, `PTP_PASSIVE` (both master-only configurations) and
`no_adjust` `PTP_SLAVE`, with 85 to 174 reads per run. The unpatched build
of the same sources (SDK `2e5ec07`, outside pkgsrc) in `PTP_PASSIVE` wrote
TAI 37 and maxerror and esterror 0 in the same guest, and the check
exited 1. `rcorder` put the package rc.d script right after a stub
`chronyd` script (exit 0); without one it warned that `chronyd` has no
provider and exited 1, with ptpd2 still after `NETWORKING`.

## Remaining

- A Daheng camera as PTP slave on an `rge` port for one hour, offset at
  most 1 ms, with the measured accuracy recorded.
- Hardware timestamps on `rge` are a separate step (R10).
