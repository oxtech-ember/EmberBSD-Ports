# Shared bmake 20260912 source

The existing `devel/bmake/files` owner supplies the ordinary package and
`bootstrap/bootstrap`. The export updates that owner to the complete official
[bmake 20260912 release](https://www.crufty.net/ftp/pub/sjg/).
It retains the recipe's `bootstrap-mk-files` dependency, host branches,
configuration, test target and install layout. It adds no second recipe.

## Source and local changes

The official dated archive and `bmake.tar.gz.sha1` identify the same release.
[sources.tsv](sources.tsv) pins the archive SHA256 and the complete import
patch. The dated archive has 905757 bytes. Its published SHA1 also matches.
Detached-signature validation remains a separate check.

The previous 20240909 archive is retained only for source-delta comparison.
Its mirror URL and SHA256 are recorded in the same manifest. All 957 previous
pkgsrc files match that archive after expanded RCS keyword normalization.
546 files have keyword-only differences. No source-code patch remains to merge.
The [NetBSD update](https://github.com/NetBSD/pkgsrc/commit/eaec492848d6c9eb3aea91d24af5b2e3230faa26)
retains the earlier source lineage. Earlier pkgsrc portability fixes had already
entered the upstream release.

The new payload retains every upstream byte, including licenses and original
authorship. It contains 985 files, including 822 unit-test files and 88 portable
makefile files. The sole pkgsrc override keeps `make-bootstrap.sh.in`
non-executable, as in the previous vendor tree. The packaging update and
regression are AI-assisted EmberBSD work, not submitted upstream.

## Shared entry points

Ordinary extraction still copies `${FILESDIR}` directly to `${WRKDIR}/bmake`.
Bootstrap still copies `devel/bmake/files` to its `bmake` work directory.
Both run `configure`, which creates `make-bootstrap.sh` from the template.
No extra `bmake/` directory belongs inside the copied payload.
The recipe keeps its existing configure and `make-bootstrap.sh` build route.
Upstream still disables the generated GNU-style `makefile` on Darwin.
The [initial make binding](bootstrap/README.md) retains explicit shell and
makefile-tree selection. A source update does not qualify an installed tool.

## Source check and remaining checks

```sh
python3 profiles/common-build-tools/tests/bmake-source.py \
    --sdk-source /absolute/EmberBSD-SDK \
    --pkgsrc /absolute/unchanged-baseline-pkgsrc \
    --archive /absolute/distfiles/bmake-20260912.tar.gz \
    --old-archive /absolute/distfiles/bmake-20240909.tar.gz \
    --git /absolute/git --version 20260912 --work /absolute/new-check
```

The version regression fails on the previous payload. The check verifies source
and patch hashes, Git replay, every source byte and executable bit, and both
shared entry points.
It also checks every previous file for an unmerged pkgsrc change.
It runs no configure command, compiler or newly built bmake.

Native GCC16 and cross builds, C source analysis, memory checks, upstream unit
tests, installed consumer behavior and package lifecycle checks remain separate.
No package or ordinary SDK tool acceptance follows from the source check.

## Darwin library objects

The Darwin `bsd.lib.mk` from `pkgtools/bootstrap-mk-files` compiled each
library object to a temporary file and relinked that single object with
`${LD} -r`. Without `-x`, the relink only copies the object. `ld64.lld`, the
GCC 16 Darwin bootstrap linker, does not implement `-r`. Every BSD-make library
then failed, starting with libfetch in `pkgtools/pkg_install`.
[The export patch](patches/pkgsrc-bootstrap-mk-files-darwin-objects.patch)
renames the temporary object instead. It changes only the Darwin rules.

```sh
python3 profiles/common-build-tools/tests/bootstrap-mk-files-darwin-objects.py \
    --pkgsrc /absolute/exported-pkgsrc --bmake /absolute/bin/bmake \
    --cc /absolute/bin/gcc --ld /absolute/bin/ld64.lld \
    --ar /absolute/bin/llvm-ar --ranlib /absolute/bin/llvm-ranlib \
    --nm /absolute/bin/llvm-nm --work-parent /absolute/work
```

The test builds a one-object static library with the exported mk files.
It fails with the unpatched rules.
