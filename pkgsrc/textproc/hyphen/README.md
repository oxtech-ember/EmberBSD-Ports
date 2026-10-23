# Hyphen

This common recipe selects [Hyphen 2.8.9](https://github.com/hunspell/hyphen/releases/tag/v2.8.9).
The official release archive SHA256 is
`783743daf477de8c4d16e3c74b4d2827377017718d8e17e2d9440210246f6abe`.
The recipe retains the NetBSD pkgsrc attribution and upstream licenses.
It applies no C implementation patch. The API floor remains 2.8.6.
The package ABI floor is 2.8.9 for native and cross consumers.
Upstream adds `hnj_hyphen_load_data` and retains SONAME `libhyphen.so.0`.

Native dictionary generation uses host Gawk, patch and Perl.
The native package retains `substrings.pl` and its Perl runtime dependency.
The cross package retains its existing library and dictionary payload without
that script. A full target Perl helper role remains separate work.
Run `bmake test` for the 37 upstream fixtures. They need Bash and the built
`example` program. Cross fixtures need a target runner; package creation does
not establish test or target execution. Memory and consumer checks are separate.
