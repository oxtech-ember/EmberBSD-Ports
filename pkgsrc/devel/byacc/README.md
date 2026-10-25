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

## Initial native generator

`bootstrap.json` selects the same 20260126 source archive and both recipe patches.
The [upstream archive](https://invisible-island.net/archives/byacc/) and
[change log](https://invisible-island.net/byacc/CHANGES) identify this release.
The source preparation retains the complete archive tree, including licenses,
maintenance skeletons, tests, configure inputs and generated configure.
The two `patched_members` hashes identify the exact current patch results.
They do not replace the original archive, patches or patch command evidence.

The SDK `byacc-bootstrap` stage compiles all fourteen released C files.
It keeps `btyaccpar.c`, the upstream default `YYBTYACC=1`, and `YYPATCH` from `VERSION`.
It does not regenerate skeletons, run configure or require an existing yacc.
The ordinary package recipe and its configure/install/test behavior stay unchanged.

`bootstrap/capabilities.c` must compile, link and run with the selected native GCC16.
It checks native headers, getopt declarations and state, mkstemp creation,
vsnprintf output, C noreturn and GCC format/unused attributes.
Only successful observations permit the SDK to emit `bootstrap/config.h.in` as `config.h`.
The header defines only capabilities used by the released C closure and the default skeleton choice.
An unavailable capability stops this finite route. There are no host presets or fallback executables.
The header is not an ordinary configure result and must not be installed as one.

`bootstrap/grammar.y` is an independent test fixture, not a replacement generator.
It tests typed values, operator precedence, associativity, parentheses, empty input and errors.
The generator writes a parser and token header twice with identical names and arguments.
Both outputs must be byte-identical. The same GCC16 then compiles and links that parser.
Eight source-owned cases compare exact streams and exit statuses with independent arithmetic expectations.
All temporary files stay in the fresh private work directory through explicit `TMPDIR`.

Run the SDK `test_bootstrap_byacc` suite with explicit `EMBERBSD_TEST_PORTS_SOURCE`,
`EMBERBSD_TEST_BYACC_ARCHIVE` and `EMBERBSD_TEST_BYACC_SOURCE` paths.
The last path must contain the complete source with both current patches already applied.
These tests use synthetic children. Actual native compilation, upstream test coverage,
C analysis, memory checks, expr integration and ordinary package qualification remain separate.
