# Common Node24 recipe

The canonical recipe is `lang/nodejs24` in the prepared pkgsrc tree.
The ordered `pkgsrc-nodejs24-current.patch` updates its source to
[Node.js 24.22.1 LTS](https://nodejs.org/en/blog/release/v24.22.1).
It uses the official `node-v24.22.1.tar.xz` release archive.
The official SHA256 is recorded in `sources.tsv`.
The recipe `distinfo` records BLAKE2s, SHA512 and archive size.

This is the 2026-10-21 security release.
Keep consumers on this common Node24 recipe.
The update retains all 25 pkgsrc portability patches and their checksums.
It retains the shared dependency configuration, supported platforms, package
file list and upstream `check` target. Compiler and target ABI selection stay
with the consumer.
The recipe requires shared Brotli 1.2.1 or newer and c-ares 1.34.9 or newer.
These constraints keep the shared dependencies at the security fixes used by
this release. A source update alone does not qualify those dependencies.

After the native GCC16 SDK is qualified, build and test the normal package.
Check the installed `node --version` result, upstream tests, package contents
and complete native runtime closure. Cross packages must retain separate
build-host tools and target outputs. Do not execute a target Node on the host.
Source checksum and patch-context checks do not establish that acceptance.

The Blanc package controller requires exactly host Node.js 24.22.1.
Chromium keeps its separate upstream host-Node pin. Selecting this common
provider for Chromium requires an explicit source-owned executable route and
JavaScript compatibility checks. This recipe update does not change that route.
