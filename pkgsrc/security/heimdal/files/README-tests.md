# Focused Heimdal checks

`test-heim-find-prime.c` exercises the private prime-search adapter against the
selected common LibTomMath. `test-roken-errno.py` runs the actual header
generator with the selected Perl and checks the resulting target errno guards
with the selected target Clang; pass `--help` for its input paths.
`tests/make-proto.py` runs the patched prototype generator against conditional
static functions and checks that a following public prototype is retained.

The target provider preference is checked through pkgsrc itself:

```sh
/absolute/sdk/bin/python3.15 -B \
    pkgsrc/security/heimdal/tests/openssl-selection.py
```

Set `BMAKE`, `PKGSRCDIR`, `PORTS_SOURCE`, `CROSS_MAKECONF` and
`OPENSSL_BASE_VERSION` to the selected native bmake, prepared pkgsrc tree,
Ports checkout, target cross configuration and base OpenSSL version. Keep
`PREFER.openssl` unset in `CROSS_MAKECONF` for the default case. The check uses
the recipe Makefile from `PORTS_SOURCE` and supporting framework from
`PKGSRCDIR`. It covers the cross default, explicit native and pkgsrc choices,
the provider-specific physical root passed to configure, the base library path
under the target sysroot, and native-mode preference preservation.

The cross default remains pkgsrc. A caller may select `PREFER.openssl=native`
only after verifying the base provider's provenance and complete common Ports
patch set; version equality alone is not sufficient. Pkgsrc's normal built-in
OpenSSL checks remain enabled.

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
