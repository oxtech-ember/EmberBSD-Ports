# MCAP source provenance

The probe uses these source releases.

- [MCAP C++ 2.1.3](https://github.com/foxglove/mcap/releases/tag/releases/cpp/v2.1.3),
  MIT, Foxglove Technologies Inc. The monorepo has independent language release tags;
  this probe selects the C++ release, not the Python or CLI release.
- [LZ4 1.11.1](https://github.com/lz4/lz4/releases/tag/v1.11.1),
  BSD-2-Clause library. The GPL CLI is not built.
- [Zstd 1.5.7](https://github.com/facebook/zstd/releases/tag/v1.5.7),
  dual BSD-3-Clause/GPL-2.0; this probe uses the BSD license.

[sources.tsv](sources.tsv) pins official tag archives and their SHA256.
The tags resolve to MCAP `1420296ffcfdcde4b6894c0c1aba0ad083f93dde`,
LZ4 `aa4647fad575d01a874aaaadcdbe8e6a40e072f5`, and Zstd
`f8745da6ff1ad1e7bab384bd1f9d742439278e99` (annotated tag peeled to commit).
The selected compression versions match the shared EmberBSD dependency baseline.
There are no source patches. MCAP is installed as upstream header-only C++17
code, with small local pkg-config metadata; consumers define `MCAP_IMPLEMENTATION`
in exactly one translation unit. LZ4 and Zstd are built as shared libraries into
that same private prefix. Conan, Docker and Python are unnecessary for this path.

The shell, CMake and C++ contract are original EmberBSD work, AI-assisted,
MIT-licensed. Upstream license texts are retained in the source archives and
copied to `install/share/ember-mcap/licenses`. Generated recordings and binaries
remain in the private work directory and are not committed.

The native validation VM booted a separately supplied QEMU `-kernel` Image
from EmberBSD revision `b4f718dabd085ed117a24f84d8558e4a43091dc0`.
Its SHA256 is `49395ea85b1c31e8c9eb41dce5bb29c2636ecc1c17785370375a7fb517cc8d2a`;
the matching ELF SHA256 is `fe0fe339059cc1d820c381a8553904e4163a33af8d3cc7fa25348ae75eae3b82`.
The guest's `/netbsd` file hash is inventory only and does not identify the booted kernel.
