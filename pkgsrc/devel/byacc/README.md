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
