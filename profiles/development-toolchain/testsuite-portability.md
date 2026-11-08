# GCC testsuite portability

The GCC 16.2 candidate is already built and installed. A testsuite portability
repair does not require rebuilding unchanged compiler binaries or overwriting
the results of an in-progress upstream suite.

## TSVC aligned allocation

The completed C part of the original AArch64 run contains 302 TSVC compilation
failures and 604 unresolved dependent checks. Its saved s000 non-LTO/LTO commands
both diagnose an undeclared `memalign` in the shared test header. NetBSD provides
`posix_memalign`; treating this as a missing compiler feature would be incorrect.

GCC upstream already accepted Rainer Orth's
[19888932d149c9df18306544d5b0ad0e38f2a6fe](https://github.com/gcc-mirror/gcc/commit/19888932d149c9df18306544d5b0ad0e38f2a6fe)
on July 16, 2026. The one-line change selects the existing POSIX allocator branch
on NetBSD. Ports packages that exact change in `patches/gcc-tsvc-netbsd.patch`;
[sources.tsv](sources.tsv) pins the original patch URL and SHA256. Its authorship
and the TSVC University of Illinois license remain intact. The compiler sources,
runtime ABI, test expectations and optimization flags are unchanged.

Both `development-toolchain` and `common-build-tools` exports include the patch.
The pkgsrc patch checksum is verified by pkgsrc's own checksum machinery.
Keep the source tree unchanged while its original tests run.
Apply the patch to private copies for a focused check:

```sh
CC=/usr/pkg/gcc16/bin/gcc sh profiles/development-toolchain/tests/tsvc-netbsd.sh \
  /absolute/pristine-gcc-16.2.0 /absolute/exported-pkgsrc /absolute/new-tsvc-check
```

On NetBSD 11/AArch64 with the installed GCC 16.2 candidate, both baseline
compilations failed for the expected undeclared `memalign`. Both patched builds
passed the unchanged upstream runtime checksum and the expected single vectorized
loop scan. The two modes are ordinary `-O2` vectorization and LTO with fat objects.
The guarded native run completed with status 0 in three seconds. The original
header hash and ongoing full-suite process were unchanged.

This accepts the allocator backport and those two representative checks. It
does not reclassify all 302 original failures as passes or accept the full suite.
The complete TSVC set must run after the original suite, using the repaired export;
other platform, generated-code and runtime failures remain separate work.
