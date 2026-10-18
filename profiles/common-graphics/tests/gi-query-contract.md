# GI launcher host contract

Run `ruby gi-query-contract.rb [--target aarch64|amd64] CROSS_TOOLS NEW_WORK`.
The cross-tools directory must provide the selected GCC16 compiler and readelf.
The test creates real target ELF fixtures with `-nostdlib`. It checks provider
and transport guards. Its injected SSH outcomes do not qualify target execution.
Use the real EmberBSD query guest for that separate acceptance boundary.

`EMBERBSD_TEST_RUBY` can select an absolute executable native Ruby launcher.
The default is `RbConfig.ruby`. The test records its path, SHA256 and version.
This input is only for the host test. It does not alter the production launcher.
The native launcher must support ordinary Ruby script arguments and `--version`.
It must run real Ruby and preserve the test's cleared `LD_LIBRARY_PATH` and
`LD_PRELOAD` environment. A private ELF loader `--library-path` can supply an
extracted Ruby runtime without adding host libraries to target provider searches.
