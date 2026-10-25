# Common Brotli and c-ares

Origin: NetBSD pkgsrc and the upstream projects. EmberBSD integration is AI-assisted.

The common export selects Brotli 1.2.1 and c-ares 1.34.9 in the existing
`archivers/brotli` and `net/libcares` recipes. Both are security releases.
There is no second recipe or private library version for Node.

The unmodified pkgsrc imports are
[`8ae58096be02cf9a5f730ccc07b8c6839402dda2`](https://github.com/NetBSD/pkgsrc/commit/8ae58096be02cf9a5f730ccc07b8c6839402dda2)
and
[`676776ac665ea86ec6d356c3f661f34b29b9e47b`](https://github.com/NetBSD/pkgsrc/commit/676776ac665ea86ec6d356c3f661f34b29b9e47b).
The ordered infrastructure patches retain their authors and upstream IDs.
They update recipe versions, distinfo and the c-ares library PLIST entry.
The existing CMake, cross, static-library and pkgconfig settings remain intact.
Both recipes have no carried source patch to rebase for these updates.

The official [Brotli release](https://github.com/google/brotli/releases/tag/v1.2.1)
fixes CVE-2026-111497. Tag `v1.2.1` resolves to
`db24a98aed38a16de78cc05ca15cdd8dc2a0d92d`.
The official [c-ares changelog](https://c-ares.org/changelog.html) lists its
1.34.9 security fixes and callback constraints. Tag `v1.34.9` resolves to
`bc91829cce983a35ec01f5dbc05465858a3df469`.

`sources.tsv` records the actual official archive SHA256 values.
Both archives also match every pkgsrc distinfo BLAKE2s, SHA512 and size field.
The c-ares archive SHA256 matches the GitHub release asset digest.
This is source verification. Detached-signature and build-provenance
authentication are separate checks.

Brotli's version source retains ABI compatibility number 1 and advances
its revision to 1. Its PLIST already uses `${PKGVERSION}`.
The decoder adds error code -17 in a previously reserved slot.
c-ares retains SONAME 2 and advances its complete library version to 2.19.8.
Its public API headers change only the version header in this release.
These source facts do not replace binary ABI or consumer checks.
Both packages retain their MIT license and upstream notices.

Strict source replay passes all six imported hunks on the pinned pkgsrc
recipe files. Native and cross package builds, installed PLIST and loader
checks, Node consumers, upstream execution tests and memory checks remain
pending. Keep those checks enabled when building the common providers.
