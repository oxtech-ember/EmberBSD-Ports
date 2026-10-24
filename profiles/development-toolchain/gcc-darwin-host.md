# Native GCC16 on macOS AArch64

Build-host programs need a native GCC 16.
Upstream GCC 16.2.0 does not support `aarch64-apple-darwin`.

## Source and licence

The Darwin port is maintained by Iain Sandoe in the
[gcc-16-branch](https://github.com/iains/gcc-16-branch) repository.
Homebrew publishes the difference between that branch and the GCC 16.2.0
release as a source diff:

| Field | Value |
| --- | --- |
| Upstream branch | https://github.com/iains/gcc-16-branch |
| Published diff | homebrew-core commit `4a334d2f90f786c3fc86cbc9cf72b2f13961b078` ("gcc 16.2.0"), `Patches/gcc/gcc-16.2.0.diff` |
| Size | 205825 bytes, 73 files |
| SHA256 | `578a78ae0bc62a02f260b6a20c7f23e71deee16ed644e9cb5619247be4df5a71` |

The diff is GCC source. It has the GCC licence: GPLv3 or later with the GCC
Runtime Library Exception 3.1. Ports uses only this source diff. It does not
use Homebrew binaries or bottles. [sources.tsv](sources.tsv) pins the URL and
SHA256; the recipe `distinfo` pins BLAKE2s, SHA512 and the size.

## Recipe change

[gcc-darwin-host.patch](patches/gcc-darwin-host.patch) changes only Darwin
native builds of `lang/gcc16`:

- `PATCHFILES` applies the diff with `-p1` before the pkgsrc patches.
  The diff also adds Darwin COBOL support in `libgcobol/configure.tgt`. That
  hunk conflicts with `patch-libgcobol_configure.tgt`, and the recipe does not
  build COBOL. `PATCH_DIST_CAT` drops that one file section.
- pkgsrc disables the GCC bootstrap when Clang is the compiler. On Darwin the
  full bootstrap is enabled: Clang builds only stage 1, GCC rebuilds itself,
  and the build compares stages 2 and 3.

NetBSD and cross builds have `OPSYS=NetBSD` and are unchanged, so the binary
packages for EmberBSD do not change and `PKGREVISION` stays the same.

## Verification

The metadata regression needs no build. It checks the Darwin diff, its
checksums, the COBOL filter and the bootstrap setting, and that the cross
recipe does not get the diff:

```sh
BMAKE=/absolute/bmake sh profiles/development-toolchain/tests/darwin-host.sh \
    /absolute/prepared-pkgsrc /absolute/darwin-mk.conf \
    /absolute/cross-mk.conf /absolute/new-work
```

The build checks:

1. Export the recipes. `bmake -C lang/gcc16 patch` on macOS applies the diff
   and all pkgsrc patches without rejects.
2. Build the package on macOS AArch64. The build log shows `make bootstrap`
   with a successful stage 2/3 comparison.
3. The installed `gcc` and `g++` report 16.2.0, define `__GNUC__ 16` and no
   `__clang__`, and compile, link and run C and C++ test programs.
