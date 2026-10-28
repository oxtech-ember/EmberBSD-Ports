# Byacc manual installation

The shared recipe uses upstream Byacc 20260126.
The `CF_INSTALL_MAN` patches keep its temporary directory under explicit
`TMPDIR`. They stop after failed or empty `mktemp` output and preserve the
command exit status through cleanup. The macro and generated configure
script carry the same change. The source patch also closes the manual
suffix substitution so uncompressed manual aliases keep their names.
The installer uses the transformed temporary for uncompressed pages too.
A directory operand receives only the final manual basename, including its
compression suffix. Absolute source and temporary paths are not appended.

Run the shell regression against a fresh patched source tree:

```sh
TEST_SHELL=/absolute/selected/sh /absolute/selected/sh \
  pkgsrc/devel/byacc/tests/install-man.sh /absolute/patched-byacc /absolute/new-check
```

The check emits the actual configure heredoc without running configure or a
compiler. It exercises manual installation, compression and name transforms,
manual aliases, removal, temporary-directory placement and failure cleanup.
Controlled external commands inject `mktemp`, copy and install failures.
They preserve the real installer control flow. All test writes stay in the
new check directory. Select the test utilities through an explicit `PATH`.
The ordinary `bmake test` target separately runs upstream parser-output checks.
Neither shell check establishes C compilation or target-runtime acceptance.

## Historical bootstrap profile

`bootstrap.json` and `bootstrap/` describe the retired GCC16 direct-source
bootstrap profile. The manifest is immutable historical data: its two patch
entries and patched-member hashes describe that original profile, not the
current Ports recipe. Existing SDK history readers use the original manifest
and source snapshot; do not use it to prepare or build current byacc.

The active package is built by the ordinary Ports recipe. Its `distinfo` and
`patches/` are the complete authoritative patch set. The shared
`scripts/source-inputs/byacc/source.py` prepares the same source for OS
consumers and checks the complete patch inventory and checksums. The normal
pkgsrc exporter checks the declared patch roster and checksums as well.
Initial SDK bootstrap uses the ordinary exported Ports recipes with explicitly
selected initial tools; it does not require a completed native prefix.
