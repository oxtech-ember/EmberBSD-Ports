# Shared libzip recipe

This recipe selects libzip 1.12.1, released on 2026-10-14.
The common profile exports it as `archivers/libzip`.
It replaces the former network-diagnostics recipe.
The library, tools, examples, and upstream regression tests keep their upstream
build settings. Python and nihtest are test dependencies.

## Source and recipe provenance

- [Official release notes](https://libzip.org/news/#released-libzip-1121).
- [Official archive](https://libzip.org/download/libzip-1.12.1.tar.xz).
- SHA256: `c40062022a1963c80573d48f6070792297cecd7c6bffe3aefcac0d8b9bee8913`.
- Size: 813384 bytes.
- [GitHub release](https://github.com/nih-at/libzip/releases/tag/v1.12.1)
  publishes the same archive digest.
- The recipe files retain their NetBSD notices. They come from
  [pkgsrc commit 5b6bf30](https://github.com/NetBSD/pkgsrc/tree/5b6bf30e8833c26c5b1a7b047e1a2f778c3b5dd5/archivers/libzip).
- [FreeBSD commit 33dafb1](https://github.com/freebsd/freebsd-ports/tree/33dafb1516f2e73b6810d2ecf16bc7bf23e94986/archivers/libzip)
  also selects 1.12.1. Its disabled regression policy is not used here.

The source retains SONAME `libzip.so.5` and updates the library file to 5.6.
The install list removes `FindMbedTLS.cmake` and adds `zip_source_at_eof.3`.
The existing NetBSD test patch follows the upstream move to
`regress/support/nihtest.conf.in`. It preserves loader paths for uninstalled tests.

## Validation

Archive digests, the patch digest, zero-fuzz patch application, and the changed
install entries were checked against the official source archive.
The shell syntax and whitespace checks pass.
These source checks do not establish build or runtime acceptance.

Use a prepared common pkgsrc tree and an explicit native GCC16 MAKECONF for
upstream tests. Keep `BUILD_REGRESS` enabled and provide pkgsrc's nihtest test
dependency. The standard recipe sets `TEST_TARGET=test`:

```sh
bmake -C /absolute/pkgsrc/archivers/libzip \
    MAKECONF=/absolute/native-gcc16.mk USE_CROSS_COMPILE=no test
```

Confirm that CTest executed tests. Retain its passed, failed, and skipped counts.
A missing nihtest executable makes upstream CMake disable the regression suite;
that configuration does not establish a test pass.
Run target package builds separately with the selected complete EmberBSD sysroot.

For the installed consumer, check ZIP creation, append, replacement, extraction,
CRC failure, and truncated input against independent expected payloads.
Record the selected libzip path and version. Rebuild the selected dependent
package against that same library.

Run Cppcheck with the real compilation database for the original and patched
source. Add GCC16 `-fanalyzer` for the library's C compilation. Run the native
upstream tests and consumer under Valgrind on a supported host with a nonzero
error exit code. Target execution and package lifecycle checks remain separate.
