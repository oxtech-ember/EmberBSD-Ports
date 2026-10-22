# NNG 1.12.3 package

The common-graphics profile provides the current `net/nng` recipe for KiCad IPC.
It keeps ABI major 1, public headers, compatibility APIs, protocol implementations,
statistics, HTTP and upstream transport defaults. It explicitly builds `nngcat`
in cross mode. Native upstream tests remain enabled by their normal default.
Cross builds retain the upstream test default for cross compilation.
The `static` option selects the static library instead of the shared library.

The recipe uses the pinned [NNG source and lifecycle repairs](../../../probes/kicad/nng/PROVENANCE.md).
Two exact recipe links share the reviewed lifecycle and required-docs patches.
The exporter checks their origins and checksums. It materializes regular files
so an exported source tree does not depend on the original checkout.
The earlier NetBSD `pthread_setname_np` repair is already in NNG 1.12.3.

Documentation remains enabled by default. Both manual pages and HTML pages use
the real upstream Asciidoctor formatter on the build host. The normal dependency
is `textproc/ruby-asciidoctor`, with Asciidoctor 2.0.26 or later in the 2.x series.
The cross recipe uses `TOOLBASE` for the formatter path.

An existing host formatter can be selected explicitly:

```make
EMBERBSD_BUILD_ASCIIDOCTOR=/absolute/host/bin/asciidoctor
```

The path must be absolute and executable. Its successful `--version` output
must identify Asciidoctor 2.0.26 or later and earlier than 3.0.
This explicit selection replaces only the formatter build dependency.
It does not install gems or select a target Ruby runtime.
Requested documentation fails configuration if the formatter is absent.
The explicit pkgsrc `-doc` option retains its ordinary upstream behavior.

Run the actual-source CMake regression with a pristine pinned NNG tree:

```sh
python3 probes/kicad/nng/tests/check-docs.py \
    --source /absolute/nng-1.12.3 --cmake /absolute/host/bin/cmake \
    --asciidoctor /absolute/host/bin/asciidoctor --work /absolute/new-doc-check
```

Run native and cross recipe selection checks with an exported pkgsrc tree:

```sh
python3 probes/kicad/nng/tests/check-host-tool.py \
    --pkgsrc /absolute/export --makeconf /absolute/cross.mk.conf \
    --bmake /absolute/host/bin/bmake --asciidoctor /absolute/host/bin/asciidoctor \
    --work /absolute/new-host-tool-check
```

The GCC 16.2.0 AArch64 ordinary package passes checksum, zero-fuzz patch,
static packing-list, interpreter, permission, PIE, RELRO, runtime search-path
and work-directory-reference checks. It contains 694 payload files and links:
35 headers, `nngcat`, shared libraries and CMake exports, the MIT license,
325 manual pages and 325 HTML pages. The library keeps SONAME `libnng.so.1`.
The archive `nng-1.12.3.tgz` has SHA256
`ed18f3b5a68890ff3a38c8869541acba6bf62ebf04b727db275d321c870426d8`.

CMake 4.4.4 and real Asciidoctor 2.0.26 run on the macOS build host.
The formatter uses Ruby 4.0.1 with its standard `logger` gem. Its isolated
Asciidoctor gem matches the pinned pkgsrc 2.0.26 SHA512, BLAKE2s and size.
The actual-source documentation regression passes all four controls.
Native/cross recipe queries retain the normal formatter dependency by default
and accept the explicit real formatter and its executable symlink.
They reject unsupported versions, failed version commands, invalid banners,
non-executable files, relative paths and missing paths.
The host volume permission check reports its existing group-writable ancestor;
all package permission checks report zero errors.

The [source checkpoint](../../../probes/kicad/nng/README.md) records native tests
and analysis limits separately. The installed AArch64 library passes the bounded
REQ0/REP0 filesystem-IPC check documented there, including exact binary messages,
expected errors and provider hashes. Normal package removal/reinstallation and
KiCad request-server/API workflows remain pending. Native ordinary packaging
and full KiCad execution are separate gates.
