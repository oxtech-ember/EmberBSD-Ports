# GNU sed multibyte state initialization

GNU sed 4.10 uses four automatic `mbstate_t` objects initialized with `{ 0, }`.
GCC 15 and later initialize only the first member of a union for this syntax.
See the [GCC migration note](https://gcc.gnu.org/gcc-15/changes.html).
NetBSD defines `mbstate_t` as a 128-byte union whose first member is an
8-byte alignment scalar. The remaining bytes can therefore be indeterminate.
Citrus `mbsinit` then reports a noninitial state for an ASCII delimiter.
GNU sed rejects ordinary address and substitution commands in UTF-8 locales.
The byte-oriented C locale does not enter that multibyte path.

`patches/gsed-mbstate-zero.patch` adds two ordinary pkgsrc source patches.
They explicitly clear each complete state before first use in `match_slash`,
multibyte transliteration compilation, `normalize_text`, and `translate_mb`.
Existing reset operations, locale handling and invalid-delimiter checks remain.
The delta selects `gsed-4.10nb1` in every prepared development/common profile.
It does not change the pinned upstream pkgsrc checkout or upstream archives.
This is an AI-assisted EmberBSD repair, not an accepted upstream patch.
The original GNU licenses and source attribution remain unchanged.

The upstream source is `https://ftp.gnu.org/gnu/sed/sed-4.10.tar.xz`.
Its SHA256 is
`b8e72182b2ec96a3574e2998c47b7aaa64cc20ce000d8e9ac313cc07cecf28c7`.
The recipe keeps its original BLAKE2s, SHA512 and size checks.
Pkgsrc verifies both new patch SHA1 values using its normal RCS-ID filter.

Run the source integration and actual executable regression with:

```sh
sh profiles/development-toolchain/tests/source-profile.sh
python3 profiles/development-toolchain/tests/gsed-mbstate.py \
    /absolute/path/to/gsed /absolute/new/results
```

The executable check has thirteen independently specified cases. They cover
C and UTF-8 address/substitution commands, patch-byte filtering with a fixed
SHA1, character matching, transliteration, escaped replacement, case conversion,
invalid input and rejection of a multibyte delimiter. The default UTF-8 locale
is `en_US.UTF-8`; set `UTF8_LOCALE` to another installed UTF-8 locale if needed.
Missing locale functionality must fail the positive multibyte cases.
Full GNU sed and Gnulib tests, installed consumers and package lifecycle checks
remain necessary in addition to this bounded regression.

## Native GCC16 validation and limits

On NetBSD 11/amd64, both versions were built from the pinned archive with
GCC16.2.0, `-O2 -g`, and one build worker. The original executable passed
4/13 local cases and failed nine UTF-8 cases. Its main upstream suite had
59 passes, eleven skips and five failures: `mb-match-slash`, `mb-y-translate`,
`badenc`, `utf8-ru` and `word-delim`.

The repaired executable passed all thirteen local cases. Full `make check`
returned zero: the sed suite had 64 passes and eleven skips; Gnulib had
237 passes and 49 skips. No test failed or errored. The same thirteen cases
passed after isolated source installation and after uninstall/reinstall.
These source lifecycle checks do not establish pkgsrc package acceptance.

Static analysis covers the two changed translation units with matching
NetBSD target headers and configured Gnulib macros. GCC16 `-fanalyzer`
returned zero with seven inherited compiler warnings in each version.
Clang21 Static Analyzer reported the same five warnings before and after.
Neither analyzer introduced a new warning signature.

Cppcheck2.22 could not analyze these configured sources reliably. Its native
parser rejected a generated Gnulib header in both versions. It also rejected
GCC16-preprocessed input; its experimental Clang frontend aborted in both
versions while parsing a source location. This is an analysis gap, not a
Cppcheck pass. No warning suppressions were introduced.

Valgrind is not installed on the checked native platform, and the accepted
compiler seed was built without sanitizer runtimes. No Memcheck, ASan or
UBSan success is claimed. Package staging/check-files, installed pkgsrc
consumers, cross builds and dynamic memory checks remain separate gates.
