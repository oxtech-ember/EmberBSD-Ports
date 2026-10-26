# GCC 16 C++ modules allocation on NetBSD

The GCC 16.2.0 candidate can crash while writing a C++ module CMI on a
filesystem that rejects `posix_fallocate`. NetBSD returns `EOPNOTSUPP` (45),
while its `ENOTSUP` is 86. GCC's original `elf_out::create_mapping` falls back
to `ftruncate` only for `EINVAL`; its upstream `ENOTSUP` repair alone does
not cover the observed NetBSD return value.

`patches/gcc-modules-fallocate.patch` packages Rainer Orth's accepted GCC
commit `a94156b8ee7165c32f73f9cd11c9b8f3b8687d3b` (2026-05-05) and adds an
AI-assisted local `EOPNOTSUPP` extension. The original patch URL/SHA256 is
pinned in `sources.tsv`. The extension has not been submitted or accepted
upstream. GCC's GPLv3+ license, authorship and identifiers remain intact.
The allocation fallback still rejects other errors, including `ENOSPC`,
`EACCES`, `EBADF` and `EIO`, and preserves failures returned by `ftruncate`.

The compiler source changes, so the exported package is
`gcc16-16.2.0nb1`. Its companion recipe is `gcc16-libs-16.2.0nb2`, preserving
pkgsrc's required higher libs revision. The repair does not change runtime
library code or require installing a second runtime provider. The separate
`gcc16-libjit` recipe retains its revision because this C++ frontend change
does not alter libgccjit.

## Source regression

Download the original pinned GCC archive and upstream patch, then run:

```sh
sh profiles/development-toolchain/tests/modules-fallocate.sh \
    /absolute/gcc-16.2.0.tar.xz /absolute/upstream.patch /absolute/new-output
sh profiles/development-toolchain/tests/source-profile.sh
```

The regression verifies both downloaded hashes, applies the actual exported
pkgsrc patch to the actual GCC source, checks pkgsrc's patch checksum, and
extracts the allocation lambda from baseline, upstream-only and final sources.
It compiles the extracted lambda with controlled allocation/truncation calls
and explicitly distinct NetBSD error constants. Baseline and upstream-only
must reject 45; the final branch must pass unsupported-operation cases while
rejecting unrelated allocation errors. Stale `errno`, offset/length arguments,
failed truncation and the `HAVE_POSIX_FALLOCATE`-absent branch are covered.
Duplicate/missing extraction shapes, corrupt checksums and repeated patch
application are rejected. These are production-function source contracts;
they do not establish a rebuilt native frontend or installable package.

## Native acceptance boundary

Use the committed source delta with the retained configured native GCC build.
Preserve the original source, `cp/module.o`, `cc1plus`, command lines and hashes
before replacing owned outputs. Recompile only `cp/module.o` and relink
`cc1plus`, refreshing its generated checksum object. Do not rebuild unchanged
GCC objects or modify original suite logs.
Test with the existing installed GCC driver and a private `-B` frontend prefix,
starting with the unchanged upstream `atom-pragma-1.C`, then export/import/link
and run a small module consumer. Keep the ordinary loader and existing runtime.

A private frontend proof and pkgsrc staging/package validation are separate
levels. Keep the original package for rollback. Do not infer that this repair
resolves all failures in the original full module suite. Common consumer
selection must require the repaired package revision while retaining the valid
`GCC_REQD=16.2` major/minor floor; that policy update needs its own real pkgsrc
metadata validation. The common profile uses the standard
`BUILDLINK_API_DEPENDS.gcc16+=gcc16>=16.2.0nb1` dependency.

## Validation status

The private repaired frontend and the exact stripped frontend extracted from
the repaired package pass the unchanged upstream `atom-pragma-1.C` and a small
module export/import/link/run check on Orange Pi Zero 3W A733 with the updated
EmberBSD kernel/libc. All five compile/link/run statuses are zero; the consumer
prints 42. Native production-extracted tests reproduce baseline/upstream-only
failures for 45 and pass all 16 final allocation cases plus 16 ftruncate-only
cases. These bounded checks do not establish complete C++ modules support.

Normal pkgsrc fresh check-files and package creation pass for
`gcc16-16.2.0nb1`, SHA256
`9137c8f5460b1421ce453690ba330755967022fac2967b493c4428adb4cd09f9`.
The package identity is checked inside `+CONTENTS`; only the staged C++
frontend differs from the original payload. Drivers/runtime libraries remain
byte-identical. The original package is retained for rollback. The final package
installs
with normal `pkg_add -u` and passes verification of all 1,633 installed files.
Installed-mode atom and module export/import/link/run pass without `-B`;
the updated native common-consumer fixture passes through `/etc/mk.conf`.

Real exported C/C++ recipe metadata preserves the repaired revision dependency,
`GCC_REQD=16.2`, the full compiler package and no separate runtime. Package
matching rejects 16.2.0 and accepts nb1/nb2. Run the focused revision check with
an actual native make/pkg_admin or the documented host metadata boundary.
The make wrapper must supply the current [native-prefix inputs](../common-build-tools/cross/native-toolset.md)
for the explicitly selected GCC family:

```sh
sh profiles/common-build-tools/tests/gcc16-revision.sh \
    EXPORTED_PKGSRC MAKE_WRAPPER PKG_ADMIN NEW_OUTPUT
```

## Package metadata path repair

The earlier unpublished nb1 candidate, SHA256
`0dd92fa4b006bd66d61841ef6401f193b2950fa96809a5193ea46aab5af4a433`,
passed staged payload checks but failed installation. Its generated metadata
recorded its own `/usr/pkg/gcc16/lib/./libgcc_s.so.1` as an external requirement.
pkgsrc subtracts package-owned files by exact spelling; pkg_add checks the
remaining requirements before extraction and after deleting an older package.
The original package was restored normally while this defect was repaired.

`gcc-package-requires.patch` normalizes repeated `/./` in ELF loader paths
before that subtraction. Parent-spelled aliases are excluded only if the
canonical path is explicitly owned by the package and both paths identify the
same staged file. External, unlisted and symlink-distinct requirements remain
checked. The regression covers both native and DESTDIR staging. This is a local AI-assisted pkgsrc adaptation, not
submitted upstream. The actual metadata rule regression is RED before the
repair and GREEN after it; an isolated pkg_add still rejects a missing external
library. Run it with the actual exported file and BSD make:

```sh
sh profiles/development-toolchain/tests/package-requires.sh \
    EXPORTED_PKGSRC/mk/pkgformat/pkg/metadata.mk BSD_MAKE NEW_OUTPUT
```

Normal metadata/package regeneration from retained staging produces the final
hash above. Every payload byte, mode, owner and symlink matches the earlier
reviewed candidate. No GCC object or runtime was rebuilt for this metadata fix.
