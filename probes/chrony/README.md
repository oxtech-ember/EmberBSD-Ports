# chrony on the common stack

This probe records the state of registry item E32: chrony 4.9 from the
pkgsrc `net/chrony` recipe (pkgsrc `fff4deb639a1`), for EmberBSD
amd64 and AArch64. Native builds use the recipe unchanged; cross builds
apply `profiles/common-build-tools/patches/pkgsrc-chrony-cross.patch`.
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

## AArch64 Clang cross package

The package was rebuilt on 28 October 2026 on macOS arm64 from the Ports
`68484dee` export. The build used the common cross profile and the native
Clang/LLVM 23.1.4 Ports prefix. The SDK sysroot came from EmberBSD
`b36583d38bf`. The cross patch names the target system for chrony's own
configure; without it, configure selected `sys_macosx.c` from the build host. The [built-in package root](../../profiles/common-build-tools/cross/builtin-prefix.md)
and the cwrapper include mapping give the cross configure the base
`readline.h`, so `chronyc` has line editing.

| Result | Value |
| --- | --- |
| Package | `chrony-4.9.tgz`, SHA256 `178aceb9726f22ea2ad58d1cf2a6cff970930bb00deae934e05b5e02f80a8d93` |
| Programs | `sbin/chronyd`, `bin/chronyc`: AArch64 PIE; both need `libgnutls.so.30`, `libnettle.so.9`, `libm.so.0`, `libpthread.so.1` and `libc.so.12`; `chronyc` also needs `libedit.so.3` |
| Features | `chronyc`: +READLINE +SECHASH +IPV6 -DEBUG |
| System driver | `sys_netbsd.c` |
| Built dependencies | gnutls 3.8.13nb1, nettle 4.0, gmp, libtasn1, p11-kit, libunistring, libffi, zlib, mozilla-rootcerts, bash 5.3.20nb1; from earlier exports, gnutls and bash with the built-in package root fix |
| Compiler diagnostics | Only `-Wunused-command-line-argument`: the cross wrapper passes `-pie` and `-Wl,-zrelro` to compile-only commands; no warning from the chrony sources |

The package was not run on a target.

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

## Installation on AArch64

Target: an EmberBSD AArch64 VM under QEMU HVF on macOS arm64, on 29 October
2026. It has the full base set of release `6dd5714` with shared libraries,
the EMBER64 kernel from OS `fd21f1a2d71` and no chrony, gmp or LLVM runtime
packages. The disk ran in snapshot mode.

- The `gmp-6.3.0` package of 28 October requires `libc++.so.1`,
  `libc++abi.so.1` and `libunwind.so.1` in `/usr/pkg/llvm/lib`. It declares
  no dependency on their packages, so `pkg_add chrony` stopped at gmp.
  Since Ports `877d0a56`, cross C++ packages depend on `libcxx`, `libcxxabi`
  and `libunwind`.
- The LLVM runtime packages 23.1.4nb2 come from the full AArch64 runtime stage
  of OS `c93e0f475bf`, built from the Ports `b14cc37b` sources. The cross tools
  select it with `--runtime-stage` and `--runtime-base` (Ports `aa892eeb`).
- gmp was rebuilt from Ports `d52a59e2`. Before that change, its install
  scripts named the coreutils of the build host instead of the target tools.
- `PKG_RCD_SCRIPTS=YES pkg_add chrony-4.9.tgz` installed chrony and its
  11 dependencies without `-f` and without errors; `pkg_admin check` passed.
- With `chronyd=YES`, the packaged `rc.d` script starts `chronyd` at boot.
  The test clock was set 3 s ahead. With pool sources and `makestep 1.0 3`,
  `chronyd` selected a source after 5 s and stepped the clock by -1.39 s.
  Then the system time was 31 us from NTP time, stratum 4, leap status Normal.
  After a reboot, `chronyd` read its drift file and selected a source after 11 s.
- `chronyc -c tracking` returns the 14-field CSV.

| Package | SHA256 |
| --- | --- |
| `chrony-4.9.tgz` | `cf154f9e1c5b5e5d604ea160278197aeb885119db8f6345bd5bb5aa40dfe2272` |
| `gmp-6.3.0.tgz` | `3cdd1e10ee68c1f952f05fc888e73c2084ac1ff451d44014fcbfc14cb0e44cd9` |
| `libcxx-23.1.4nb2.tgz` | `35d852bc3a22adc0a3d77d7fdce1c0499760ff57e109805cbfd7b9b42b13b9b4` |
| `libcxxabi-23.1.4nb2.tgz` | `9d5ae1b0d63f34db00e07b1d9eada56adbc327b13f0b3f002a7c46792e33c692` |
| `libunwind-23.1.4nb2.tgz` | `f69f172de17faea68e9ca7f789c72a18aedbfbd3f2024a0f4a397ccd3462c53e` |

The chrony package is a later 28 October rebuild of the package above, so its
hash differs. The other dependencies are the 28 October packages listed above.

## On the CIX P1 board

Target: the Orange Pi 6 Plus on 30 October 2026, with the
`EMBER64_CIX_PERIPHERALS` kernel from OS `6373585bb9a`. Its root is the reduced
static cohort; it was not written. The test tree lives in a separate 1 GB
tmpfs and is lost on reboot.

- The `6dd5714` base set and the `c5d396f` etc set were unpacked into the
  tmpfs (280 MB). The board root has no `tar`, `pax`, `chroot` or `xz`, so the
  sets were decompressed on the build host and unpacked with static `pax`;
  the packages run under a static `chroot`. Both tools were built from OS
  `7cd7fe340fe`.
- In the chroot, `pkg_add chrony-4.9.tgz` installed chrony and the same
  packages as in the VM, 15 in total, without `-f`; `pkg_admin check` passed.
- With `server 192.168.10.1 iburst` (the ARM) and `makestep 1.0 3`, `chronyd`
  selected the ARM after 4 s: stratum 5, leap status Normal. Two polls later,
  the system time was 0.15 us from NTP time and the last offset +67 us.
- The board clock started 0.906 s slow, below the `makestep` threshold. On
  NetBSD, chrony slews offsets below 1 s through the frequency, at most
  500 ppm (`sys_netbsd.c`: `MAX_FREQ`, `MIN_FASTSLEW_OFFSET`). The offset fell
  by about 0.8 ms per second, so it would have taken about 20 minutes, while
  `chronyc` reported leap status Normal. `chronyc makestep` removed the rest.
  Since then the board configuration uses `makestep 0.01 3`, so such offsets
  are stepped at start; it takes effect at the next `chronyd` start.

## Remaining

- AArch64 execution on the base sets of OS `c93e0f475bf`, which also supply
  the runtime packages above. The VM used the older `6dd5714` base.
- A persistent CIX P1 board root from the common base sets. The test above
  ran in a tmpfs tree; the board root itself is still the reduced static
  cohort without shared libraries or pkgsrc.
- PPS through RFC 2783 and `gpiopps` waits for GPIO017 interrupts (N36).
- An installable amd64 set needs the `gmp` and `gcc16` rebuilds above and a
  runtime-only GCC16 provider.
