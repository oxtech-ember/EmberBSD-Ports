# uthash checks

Run `bmake test` in the prepared `devel/uthash` package directory.
The recipe preserves the upstream `tests_only` target and declares its C, GNU Make, and Perl tools.
Run target tests on EmberBSD after a cross build.

The header patch fixes a null member access in `HASH_SELECT`.
An empty destination is valid.
Compute the secondary handle offset from a source element after the source null check.

Run the focused regression on a host that supports ASan and UBSan:

```sh
CC=clang CXX=clang++ sh tests/run-hash-select.sh /path/to/uthash-source /path/to/new-work-dir
```

Use the unmodified 2.4.0 source to reproduce the UBSan failure.
Apply `patches/patch-src_uthash.h` to a separate source copy, then repeat with a new work directory.
The check covers empty input, a predicate that rejects all records, a function predicate, and a macro predicate.
It runs as C and C++, with and without `NO_DECLTYPE`.
The source is also usable with Valgrind on a supported host.
Compile it without sanitizer flags before that run.

The macOS arm64 validation used ASan and UBSan, not Valgrind.
The patched header passed the focused cases and all 101 upstream tests.
ASan on this host does not establish leak coverage.
The unchanged upstream tests include allocations that are retained until process exit.
This host check does not establish target-board or long-run acceptance.
