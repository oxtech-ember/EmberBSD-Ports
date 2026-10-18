# Check the gettext Go compiler candidate

Gettext 1.0 used the executable name alone to select a Go compiler.
An unrelated program named `go` could pass configuration and fail later
with unknown `mod` and `build` commands in the `lang-go` test.

The common gettext-tools 1.0nb3 patch checks each automatic candidate with
`version`. The command must succeed and its output must start with
`go version `. A rejected candidate does not hide a valid program later
in `PATH`. The original Go/GCC preference and version order stay intact.
An explicit `GO` override remains the caller's responsibility, as before.
No compiler language, test or diagnostic is disabled.

The patch changes `gnulib-m4/gocomp.m4` and the corresponding generated
`configure` code. The latter uses Autoconf 2.72. It does not change C/C++
sources, installed ABIs or the normal pkgsrc package split.
`prepare-pkgsrc.sh` applies the patch after the common cross-package delta.

## Discovery regression

Use the original and patched `gettext-tools/gnulib-m4/gocomp.m4` files from
the pinned gettext 1.0 source archive:

```sh
ruby profiles/common-build-tools/tests/gettext-go-detection.rb \
    /absolute/original/gocomp.m4 /absolute/patched/gocomp.m4 \
    /absolute/new-discovery-check
```

The host needs Ruby and a working native Autoconf installation.
Set `AUTOCONF` when its executable is outside `PATH`. A relocated Autoconf
installation can also require its normal `AUTOM4TE` and `M4` settings.

The test executes actual generated configure scripts. Seven cases check
the original name-only error, absent compilers, rejected output and exit
status, a later valid candidate, both implementation preferences and an
explicit override. Positive scripts are discovery fixtures. They do not
compile Go or serve as build providers. The result records input hashes,
Autoconf version, command statuses and the selected paths.

## Native validation and limits

The 2026-10-18 Linux bootstrap used GCC 16.2.0 and the official gettext 1.0
archive, SHA256
`85d99b79c981a404874c02e0342176cf75c7698e2b51fe41031cf6526d974f1a`.
Normal full build and installation retained upstream defaults. XML used
common libxml2 2.15.4 and zlib 1.3.2. The installed tool passed UTF-8,
context and plural MO catalog checks, plus the
[XML/ITS translation check](../tests/host-gettext-xml.sh).
Its runtime closure must select the newly built libtextstyle as well;
a prior host `LD_LIBRARY_PATH` can otherwise select an older provider.

Before the fix, the gettext-tools suite reported 637 passes, 34 skips and
one `lang-go` failure. The corrected configure found no actual Go compiler
on that host. The focused unchanged `lang-go` test then reported its normal
compiler-absent skip. The seven discovery regressions passed. The export
patch and source patch applied with zero fuzz and matching patch checksums.
This is native bootstrap evidence, not target package acceptance.

Separate strict Memcheck runs of the installed tool remain unsuccessful.
The catalog case retains 847 directly lost bytes, 140 indirectly lost
bytes and 372 reachable bytes. The XML case retains 151 directly lost
bytes, 65 indirectly lost bytes and 7,564 reachable bytes. Both runs use
all leak kinds, no suppressions and a nonzero error exit code. These are
inherited GNU gettext parser, catalog and CLI lifetime findings; GNU gettext
owns their upstream repair. The discovery patch does not repair them.
These counts describe the two small fixtures and depend on their path lengths.
No invalid-access error appeared in those two cases.
GCC16 `-fanalyzer` completed `msgfmt.c` and `write-xml.c` without diagnostics.
Cppcheck 2.22 stopped on a generated gnulib declaration in the actual
GCC16-preprocessed headers. That incomplete run is not a clean analysis.
