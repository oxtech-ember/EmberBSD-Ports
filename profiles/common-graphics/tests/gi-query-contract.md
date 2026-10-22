# GI launcher host contract

Run `python3.15 gi-query-contract.py [--target aarch64|amd64] CROSS_TOOLS NEW_WORK`.
The cross-tools directory must provide the selected GCC16 compiler and readelf.
The test creates real target ELF fixtures with `-nostdlib`. It checks provider
and transport guards. Its injected SSH outcomes do not qualify target execution.
Use the real EmberBSD query guest for that separate acceptance boundary.

`EMBERBSD_TEST_PYTHON` can select an absolute executable native Python launcher.
The default is `sys.executable`. The test records its path, SHA256 and version.
This input is only for the host test. It does not alter the production launcher.
The native launcher must support Python script arguments and `--version`.
It must run real Python and preserve the cleared `LD_LIBRARY_PATH` and
`LD_PRELOAD` environment. The helper and tests use the standard library only.
`--recipe /absolute/gobject-introspection` selects an explicit recipe for
prepublication checks. The default is the adjacent canonical recipe.
The receipt checks that production inputs do not change during the test.

The Python port passes the AArch64 host contract on macOS with real GCC16 ELF
fixtures. Both architecture metadata sets are checked by native BSD make.
An EmberBSD AArch64 VM separately passes 21 SSH, PTY, provider-hash, literal
argument, negative-status and cleanup checks against the same Python launcher.
AArch64 execution does not establish amd64 runtime acceptance.
