# Shared @bufbuild/protobuf

This package installs the unbundled Protobuf-ES JavaScript runtime from the
upstream npm release. The original npm archive does not include license files:
`files/LICENSE` is the Apache-2.0 text from upstream protobuf-es tag v2.16.0;
`files/NOTICE.protobuf` reproduces the BSD notice carried by the distributed
`dist/commonjs/wire/varint.js`. Source headers remain intact.

Apache license source: `https://github.com/bufbuild/protobuf-es/blob/v2.16.0/LICENSE`
(SHA256 `c04b4216f1cd4c5a4f7fb2f2a1b0ae70d847e9e0cac7c9dee9bf8cc03177c449`).
The package has no runtime or peer dependencies. Upstream npm integrity is
checked alongside pkgsrc BLAKE2s and SHA512 before extracting the source.
