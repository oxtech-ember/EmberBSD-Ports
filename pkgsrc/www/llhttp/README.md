# Common llhttp provider

The common native library and `www/llhttp-wasi` use the same generated
llhttp 9.4.4 source from `deps/llhttp` in the official Node.js 26.13.1 source
archive. The independent llhttp 9.4.4 release archive was not available when
this recipe was updated. The original llhttp MIT licenses remain in that
source directory; the WASI package installs `LICENSE-MIT`.

A Darwin host build of the shared library and plain and SIMD WASI reactors
succeeded with the selected SDK Clang 23.1.4. Undici 8.12.4 generated its
wrappers from these reactors, matched the upstream wrapper generator, and
passed a loopback HTTP smoke using the existing host Node 26.13.0. This is not
installed package, new Node runtime, or target acceptance.
