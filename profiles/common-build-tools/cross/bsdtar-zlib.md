# Bootstrap consumers and the common zlib provider

Both bsdtar 3.8.10nb2 and pkg_install 20260227nb5 use the registered zlib package.
This applies to ordinary bootstrap and common profiles. The common recipe
provides zlib 1.3.2nb2 with its complete patch set. Its API floor remains nb1.
Neither consumer copies `devel/zlib/files`, which contains packaging support
files rather than the distfile release sources. Archive formats remain enabled.

The old `EMBERBSD_BSDTAR_USE_COMMON_ZLIB` selector no longer changes the provider.
The [bsdtar patch](../patches/pkgsrc-bsdtar-common-zlib.patch) and
[pkg_install patch](../patches/pkgsrc-pkg-install-common-zlib.patch) apply through
the exporter. Both recipes use the common zlib buildlink dependency.
The exporter rejects a missing patch before creating its output.

The [metadata check](../tests/bsdtar-common-zlib.py) checks ordinary bootstrap,
legacy selector values, the common profile and pkg_install dependency ownership.
It also checks native compiler identity, target selection and recursive host roles.
Use `--native-only` to report an explicit cross-check omission on an initial host.
Metadata and source export checks do not accept a compiled package.

The initial pkgtools producer has its own finite source contract in
[`bootstrap/pkg-install.json`](../bootstrap/pkg-install.json).
It creates uncompressed packages before ordinary package dependencies are built.
Its limited compression configuration does not replace the full package recipe.

The following runtime evidence applies to the earlier bsdtar common-profile
integration. The ordinary bootstrap dependency change requires a separate build.

The ordinary native GCC16 package passes its existing package checks.
Its staged payload links the registered native zlib provider. Creating and
extracting a gzip archive preserves a 131072-byte payload and passes strict
Memcheck with zero errors and zero live allocations in each process.
Target package execution and the complete libarchive test suite are separate.

The gzip read/write modules are byte-identical to pinned pkgsrc sources.
Analysis uses their actual wrapper-expanded compiler flags. Clang 19 reports
no findings. GCC16 reports two ownership warnings at assignments to
`gzip->name` and `gzip->compressed`. Their release callbacks free these fields;
the reports do not model that retained filter ownership. No warning is suppressed.
Cppcheck 2.22 stops at the real Linux `types.h` signed-128-bit declaration.
This is an analyzer parser limit, not a completed Cppcheck result.
