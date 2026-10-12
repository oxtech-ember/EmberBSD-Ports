# TDB and libdaemon cross packages

The complete TDB 1.4.15nb1 and libdaemon 0.14nb3 packages cross-build on macOS
for EmberBSD/AArch64. They unblock the normal PulseAudio dependency closure.
The original archives, SHA256 and complete inherited recipes are in
[sources.tsv](sources.tsv). TDB 1.4.15 is the current published Samba release;
libdaemon 0.14 remains its upstream's final feature-complete release.
No older parallel dependency was introduced.

TDB's Waf runs with host Python, while compiled configure probes use the
[shared target executor](../common-graphics/cross/introspection.md#compiled-configure-probes).
Actual target execution supplies the feature results; they are not guessed
from the build host. Configure uses pkgsrc's target Python sysconfig environment
and runs the target `python-config` script with the host interpreter. This
removes macOS headers and `-ldl` from target extension flags. Native DocBook/XSLT
tools generate all four manual pages. The C library, all four installed tools,
Python extension, text wrapper, development files and manuals remain packaged.

libdaemon's cross recipe records the BSD `setpgrp(pid_t, pid_t)` signature
from the target header. Its original configure test cannot execute during a
cross build. The target C regression checks that signature and exercises a
private child-process return channel and signal pipe. No service is started.

These are AI-assisted EmberBSD adaptations of pkgsrc and upstream sources.
Original copyright, licences and RCS identifiers remain. No upstream submission
or acceptance is claimed.

## Reproduce

Build the normal `databases/tdb` and `devel/libdaemon` packages in an exported
common-media or plasma-mobile tree. Supply the shared executor configuration
and matching host Ruby as documented in the introspection guide.

```sh
BMAKE=/absolute/native-bmake MAKECONF=/absolute/cross-mk.conf \
  sh profiles/common-media/tests/tdb-cross.sh PREPARED_PKGSRC NEW_CHECK
```

The check inspects actual Waf flags, host generators, target Python ABI,
native-mode selection and every file from the package list. It also injects a
transport-failure marker into the real post-configure hook and checks refusal.

For TDB runtime acceptance, copy the unchanged extracted `test/` directory,
`python/tests/simple.py`, all 37 built `bin/tdb1-*` programs and `bin/tdbtorture`
into the same relative layout on a board with the complete package installed.
Run `tests/tdb-runtime.sh TEST_BUNDLE NEW_RESULTS`. It runs the original backup
and dump shell suites, all C test programs, deterministic three-process torture
and the Python suite against the installed module. Each process has a finite
timeout. Scratch databases, including the large sparse-file test, are removed.

Compile `tests/libdaemon-runtime.c` with the target compiler, `_NETBSD_SOURCE`,
C11 and warnings-as-errors, linking the sysroot's `libdaemon` with the ordinary
`/usr/pkg/lib` RPATH. Execute it on the installed board.

## Accepted bounded run

On 2026-10-12 CM5 Rev 1.0, BCM2712 D0, 4 GiB, Waveshare CM5-NANO-B passed:

- 37 TDB C programs exit successfully. Two deadlock suites explicitly skip
  their robust-mutex variants because that capability is absent.
- Both upstream CLI suites pass; torture uses three processes, 5,000 loops
  and seed 1. All 55 Python binding tests pass.
- The libdaemon child returns 42 through its return pipe, and the signal pipe
  delivers exactly one self-directed SIGUSR1 within the bounded wait.
- Complete package payloads match the shared sysroot before transfer.
  Installed checks cover 15 TDB and 16 libdaemon regular files.
- Kernel `EMBERV3DRENDER #0`, source
  `ab6f88f04ca73c6958adb39d0e1c717f629e7901`, stays unchanged. Firmware revision
  is unknown. [The media receipt](ffmpeg-runtime.md) records its kernel hash.

Cppcheck 2.22 processes six libdaemon and sixteen TDB implementation units
after preprocessing with the real target GCC16 headers and definitions.
It reports inherited style diagnostics and TDB format warnings; this is not a
clean static audit. Initial attempts without target compiler definitions were
incomplete and are not counted. The new libdaemon regression passes Cppcheck.
Valgrind was unavailable. These bounded tests do not establish a long soak,
physical audio or a complete Plasma session.

| Artifact | SHA256 |
|---|---|
| libdaemon 0.14nb3 | `5f98ab36559d8b3dc1c5f5d17e8fe44a330a3d6ce7e8c49dcb70b74aee2c1ff3` |
| TDB 1.4.15nb1 | `c291b8c437bee81a7e77354c5153672e4266236249877ca71a8894a5b6b6d3b6` |
| TDB results | `4656804e036f13304bf23a65f07a1bfab2a0b2ee0608df9ffb116d9445024725` |
