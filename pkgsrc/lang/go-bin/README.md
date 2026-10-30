# go-bin

This recipe installs the official upstream binary release of Go
`${GO127_VERSION}` (1.27.3) for the build host. It is the bootstrap seed for
`lang/go127` when no native go127 is installed. It is not a second maintained
Go version: the version comes from `lang/go/version.mk`, and the recipe never
selects an older release. It retains the NetBSD pkgsrc attribution and the
upstream BSD license.

`distinfo` records one archive for each supported build host: Darwin, FreeBSD,
Linux and NetBSD on aarch64 and x86_64. `bmake distinfo` fetches all of them
through the ordinary pkgsrc fetch. Each fetched archive was compared with the
SHA-256 value published at https://go.dev/dl/ before `distinfo` was written.

## Regression

`tests/platform-seeds.py` checks the version against `lang/go127`, the
archive selected for each host platform, the `distinfo` entries, and the
`lang/go127` seed selection with and without an installed go127:

```sh
python3 -B pkgsrc/lang/go-bin/tests/platform-seeds.py --pkgsrc /absolute/export \
    --makeconf /absolute/mk.conf --bmake /absolute/prefix/bin/bmake \
    --shell /absolute/prefix/bin/mksh
```
