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

## Remaining

- AArch64 execution: a target with the full base set and its shared libraries.
- A Daheng camera as PTP slave on an `rge` port for one hour, offset at
  most 1 ms, with the measured accuracy recorded.
- Hardware timestamps on `rge` are a separate step (R10).
