# Codec source provenance

Source selection was checked on 2026-10-15 against the official
[libpng index](https://libpng.org/pub/png/libpng.html) and
[libjpeg-turbo release](https://github.com/libjpeg-turbo/libjpeg-turbo/releases/tag/3.2.0).
The libpng index names 1.6.59, released on 2026-09-30, as the current public
release. GitHub identifies libjpeg-turbo 3.2.0, published on 2026-06-30 UTC,
as its current stable release.

The JPEG recipe comes from pkgsrc commit
[`fff4deb639a1a640476203c80f752fb77b6cb14b`](https://github.com/NetBSD/pkgsrc/tree/fff4deb639a1a640476203c80f752fb77b6cb14b/graphics/libjpeg-turbo),
matching the Ports submodule and the export's `EMBERBSD-PKGSRC-REVISION`.

The PNG archive's SHA512 matches the common graphics recipe:
`e7d9d1b5f7648213ff5daf20789eda9400da7a23af9c9b0a6668e72dae69bd8944fc71c76a5ff2ed70dcb2cb74bb680020763a0a5914120ee5a3910df575fbf6`.
The JPEG tag archive's SHA512 matches pinned pkgsrc:
`1ce063e9e126d55019385da3a6ff4521a9a3958edeab15e2465ae3435026dac6e598277eea066173ada47da37159d0f7812b2227869c10dd141dcfe2ddeab720`.
[sources.tsv](sources.tsv) records SHA256 and the exact download locations.

GitHub's separately uploaded JPEG release asset is another archive boundary.
It has SHA256
`6f30092cef9fb839779646608f4ee14ae3cbac989c47fa05e841b0841f09878e`,
which matches the release API's asset digest. It does not match the canonical
pkgsrc tag-archive hash, despite both archives having 2,537,858 bytes.
This helper uses the canonical tag archive and does not replace the expected
pkgsrc digest with the release-asset digest.

The helper applies both canonical PNG patches and all five canonical JPEG
patches. pkgsrc patch SHA1 values exclude expanded NetBSD RCS identifier
lines; the helper uses that same algorithm. PNG's config-script rpath token
receives the canonical `-Wl,-rpath,` substitution. Its manual directory is
`${PREFIX}/man`, as required by the canonical PLIST. These are build-system
adaptations, with no new library source patch.

The JPEG recipe retains the NetBSD ARM32 CPU-detection patch. This profile
builds AArch64; it does not establish ARM32 execution correctness. The other
JPEG patches preserve platform CPU naming, system-zlib CMake dependencies,
and the public stdio header inclusion. The AArch64 build retains normal
upstream NEON support. PNG keeps the canonical non-x86 assembler exclusion.

The tested target uses EmberBSD's base zlib 1.3.1 from the pinned fork sysroot.
The canonical pkgsrc zlib builtin rules accept this base provider. No second
zlib package or embedded compression implementation is introduced. The native
controls use the host's system zlib through the same system-zlib option.

libpng retains its PNG Reference Library license and copyright notices.
libjpeg-turbo retains the original IJG, modified BSD, and zlib notices.
The canonical JPEG package installs its upstream license and documentation.
The test bundle includes the original PNG license, JPEG license, and JPEG
fixture license. Source archives retain the full original notices.
