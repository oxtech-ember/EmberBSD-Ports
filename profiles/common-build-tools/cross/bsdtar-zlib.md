# bsdtar and the common zlib provider

The common profile builds bsdtar 3.8.9nb1 against the normal zlib 1.3.2nb1
package. It does not copy obsolete zlib sources from `devel/zlib/files`.
The libarchive source, archive formats and existing bootstrap options stay intact.

`EMBERBSD_BSDTAR_USE_COMMON_ZLIB` defaults to `EMBERBSD_COMMON_TOOLS`.
A prepared host bootstrap can select `yes` explicitly before adopting the
common profile. pkgsrc resolves the real zlib buildlink dependency and records
its runtime ownership. The original bundled-source bootstrap remains the
default outside this opt-in. No builtin-package metadata is fabricated.

The [infrastructure patch](../patches/pkgsrc-bsdtar-common-zlib.patch) applies
through the exporter and has a missing-patch preflight control.
The [metadata check](../tests/bsdtar-common-zlib.py) verifies the bootstrap,
explicit native opt-in, common default, target and recursive host selections.

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
