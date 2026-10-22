# GDB 18.1nb1 package

The development profile replaces `devel/gdb` with the current
[canonical recipe](../../../pkgsrc/devel/gdb). Sources still come from the
upstream release server; the recipe verifies archive and patch checksums.
The export dereferences links to the shared Ports patches and helper.
It does not retain an older GDB recipe alongside this one.

## Build

Prepare a new pkgsrc tree using the development-toolchain or common-build-tools
profile, following the [profile instructions](../README.md). For macOS cross
builds, use the [common package cross environment](../../common-build-tools/cross/README.md)
with the accepted GCC16 compiler, complete NetBSD 11/AArch64 sysroot and
matching installed target dependencies.

```sh
sh scripts/prepare-pkgsrc.sh /absolute/new-pkgsrc common-build-tools
bmake -C /absolute/new-pkgsrc/devel/gdb \
    MAKECONF=/absolute/cross-mk.conf BATCH=yes package
```

The native target is NetBSD/AArch64. The package uses shared GCC16, GMP,
MPFR, Readline, Expat, zlib, liblzma, curses and zstd. Its `gstack` script
uses `/bin/sh`; Bash is not an additional runtime dependency. Python/Guile
scripting, debuginfod, Intel PT, Babeltrace, gdbserver and the simulator are
disabled. Package creation retains pkgsrc's file, interpreter, RPATH and
dependency checks.

The package includes the native backend, supplementary bounds and iconv
repairs described in [README.md](README.md), plus the
[expression and location-list repairs](dwarf-variants.md). The installed
ELF's runtime paths are `/usr/pkg/gcc16/lib:/usr/pkg/lib`.

## Install and accept

Keep a rollback copy of an existing standalone debugger outside PATH.
Install the archive and its complete dependency closure through `pkg_add`:

```sh
PKG_PATH=/absolute/packages pkg_add -U /absolute/packages/gdb-18.1nb1.tgz
pkg_admin check gdb-18.1nb1
/usr/pkg/bin/gdb -nx -nh -batch -ex 'show version'
```

Use the matching source revision to build the external-DWARF and live ABI
fixtures in [README.md](README.md), then run `test-target.sh` against the
installed executable. Run the expanded [DWARF matrix](dwarf-variants.md)
separately, including the agent-expression recursion checks. Record real
failures and unsupported cases; a valid expression rejected by the debugger
does not become conforming merely because its rejection is reproducible.

The OS repository owns the
[offline development-image builder](https://github.com/oxtech-ember/EmberBSD/tree/main/ember/image).
It selects `/usr/pkg/bin/gdb` through `/usr/bin/gdb`, removes the old base
`gdbtui` entry point, and installs a pinned, fully checksummed local package
closure on first boot. Ports owns the debugger package and acceptance;
the OS owns image assembly, boot and filesystem recovery.

Package checks alone do not establish a bootable image. Image acceptance
must finish first-boot installation, confirm package integrity and exercise
the installed debugger after a normal reboot. Neither this package nor the
bounded DWARF matrix establishes universal DWARF conformance.

## Installed revision nb1

On 2026-10-08, a clean macOS/GCC16 cross build produced `gdb-18.1nb1.tgz`.
Normal pkgsrc file, interpreter, permissions, PIE/RELRO, RPATH and work-reference
checks passed. The archive's 42 recorded MD5 values matched its payload.
Native `pkg_add -U` replaced the prior package in NetBSD 11/AArch64 UTM;
`pkg_admin check` passed all 42 files. The installed ELF, package ELF and
cross-build stage were byte-identical:
`f70bf959a177e413d511c02808bfd5485765e2e37800fe8ab33ca8341f4f0b42`.
Package SHA256:
`ad9ab3038745e541cd0c4a870e9ec0337347de86f7d278711f995f1230b0fb49`.

The installed `/usr/bin/gdb` passed all 32 compiler-produced format cases,
24 expression/location cases, 14 agent-expression checks and 72 entry-state
checks. There are no expected-gap exemptions in these runners. The separate
external/ABI suite passed eight split/supplementary objects, seven malformed
supplement rejections, Unicode, live FP registers and signal-frame unwinding
in both offset widths. Missing historical inputs remain unavailable.

The original revision's `gstack` live attachment remains earlier evidence.
The current OS image installs all eighteen GDB/LLVM closure packages offline.
Both first boot and a normal reboot pass the complete selected GDB matrix,
104 LLVM DWP checks and the OS CTF suites against installed tools. The linked
OS image guide records its source revisions, pristine image hash and limits.
