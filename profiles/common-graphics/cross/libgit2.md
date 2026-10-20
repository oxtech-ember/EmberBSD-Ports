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

## git-base 2.55.0

KiCad's pkgsrc recipe also requires `git-base`. The GCC16 AArch64
`git-base-2.55.0nb1` package was built and installed in the same sysroot. Its
archive SHA256 is
`aa810f190ff8ff36df200f82c903244afd5cebfdbac767789ae65e7832c35c4e`.
`git`, `git-shell`, `git-remote-http` and `git-remote-https` are ELF64/AArch64.

The pkgsrc profile's cross-only Makefile adjustment makes Git select
`${OPSYS}` (`NetBSD`) instead of inferring Linux from the build host. This
prevents Git from enabling Linux-only `sys/sysinfo.h`. It also omits the
target `sh:run` tool dependency during cross builds: the build uses the host
shell supplied by `devel/git/Makefile.common`, while NetBSD provides `/bin/sh`
at runtime. Native builds retain the original `sh:run` declaration. The full
common-graphics export test applies this adjustment to its pinned pkgsrc
snapshot.

The Git command has not been run here because it is an AArch64 NetBSD binary.
Target execution and full KiCad integration remain pending.
