# libgit2 1.9.7 for KiCad

The pkgsrc `devel/libgit2` package provides the C Git API and `git2` utility
required by KiCad. The unmodified pkgsrc 1.9.7nb1 recipe cross-builds with
GCC16 for NetBSD/aarch64. Its required OpenSSL, PCRE2, zlib and libssh2
dependencies were resolved from the target package set; pkgsrc also records
curl, http-parser and Python as package dependencies.

The package archive is
`libgit2-1.9.7nb1.tgz`, SHA256
`5df85f0b900e5b52835b6a0278b4e413e4c9f453cde9a9a4f5957669484a96e9`.
It is installed in the AArch64 application sysroot. `libgit2.so.1.9`,
`git2`, and a standalone consumer that calls `git_libgit2_init()` were
verified as ELF64/AArch64. The consumer compiled and linked using the
installed `libgit2.pc` with `PKG_CONFIG_SYSROOT_DIR` set to the target
sysroot.

The package build compiled its test objects but did not execute target tests.
Runtime execution and full KiCad integration remain pending.
