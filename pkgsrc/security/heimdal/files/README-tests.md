# Focused Heimdal checks

`test-heim-find-prime.c` exercises the private prime-search adapter against the
selected common LibTomMath. `test-roken-errno.py` runs the actual header
generator with the selected Perl and checks the resulting target errno guards
with the selected target Clang; pass `--help` for its input paths.

The `test-openssl-*.c` programs exercise the OpenSSL provider bridge. Link
`test-openssl-fallback.c` against the candidate hcrypto and OpenSSL libraries,
run with the matching OpenSSL module directory, and check its exit status.
It checks fallback, an existing error, concurrent lookups, restricted property
queries, and loading the legacy provider after the first lookup. Compile
`test-openssl-fake-fetch.c` as a test-only shared library and preload it for
`test-openssl-errors.c`: its arguments are `single`, `single-mark`, `stale`,
`mixed`, and `empty-mixed`. Each must exit zero. For
`test-openssl-fallback0.c`, build the bridge with `HCRYPTO_FALLBACK=0` and
verify both unavailable algorithms return NULL. `test-openssl-default.c`
checks the normal SHA-256 path, including its hcrypto self-validation.

The fake fetch library and any instrumented bridge are diagnostic artifacts;
they are not installed in a package or the sysroot. Run the upstream RSA, DH
and cipher checks against the final package as well.
