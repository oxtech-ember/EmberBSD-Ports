# PTPd for a GigE Vision PTP master

Registry item N37 needs a PTP master with software timestamps for a GigE
Vision camera. The common recipe `pkgsrc/net/ptpd` packages PTPd from the
head of the upstream 2.3.1 branch, commit
`d27a6e02c1191e07ce8dcdfa1d3f954e01f2d983` (5 September 2018; the
program reports 2.3.2). The archive is fetched by the short reference
`d27a6e0`, as FreeBSD `net/ptpd2` does; its SHA256
`9384968100d40d49aa2cf923ea5da51dacf8270d8e6350d64f887e9f30976524`
matches the FreeBSD distinfo. The archive of the full commit hash differs
only in its top directory name. Net-SNMP support is off. This record is
AI-assisted (Claude Code, Claude Opus 5.5).

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
| Package | `ptpd-2.3.1.tgz`, 8 files, SHA256 `78054315bdc8d3997e27aebb52485f645ff3ad917810c279bb4e9347f817e2cc` |
| Run-time requirements | base `libc`, `libm` and `libpcap`; declared `gcc16` |
| Compiler diagnostics | 36 inherited GCC16 warnings, including one `-Warray-bounds` (subscript 2 of `uint32_t[1]`) to review |
| Upstream tests | none in the release |

In an EmberBSD 1.0 amd64 `c5d396f` QEMU guest, `ptpd2 -k` accepted a
master-only configuration with timing ACLs, `clock:no_adjust` and log and
statistics files. Started on `lo0`, it entered the listening state and
then master after the announce timeout, and shut down on SIGTERM. No slave
was synchronised; this is not a timing measurement.

## Remaining

- AArch64 package: the common cross profile and a qualified SDK toolset.
- A Daheng camera as PTP slave on an `rge` port for one hour, offset at
  most 1 ms, with the measured accuracy recorded.
- Hardware timestamps on `rge` are a separate step (R10).
