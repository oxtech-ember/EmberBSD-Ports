# libxml2 source provenance

Prepared with AI assistance on 2026-10-07. The recipe and C consumer use the
accompanying MIT license. Upstream remains libxml2, with Daniel Veillard's,
The Libxml2 Contributors' and other per-file copyright notices preserved.

The original release archive is from
https://download.gnome.org/sources/libxml2/2.15/libxml2-2.15.4.tar.xz.
Its SHA256 is pinned in `sources.tsv` and matches the upstream `.sha256sum`.
The official directory published it on 2026-09-04; the included NEWS dates
the release 2026-09-01. The canonical schema-option patch uses an unsigned mask
for the sign-bit check. GCC16 UBSan proves the original failure and patched
success. No nested download occurs. Two unchanged CMake test drivers omitted
from the archive are supplied from the verified v2.15.4 tag; their provenance
and hashes live in the common media recipe.
The corresponding source repository is https://gitlab.gnome.org/GNOME/libxml2.

The archive's `Copyright` contains the MIT permission notice; `dict.c` and
`list.c` contain separate permissive notices. Installation copies all three
notices into `share/ember-libxml2/licenses`, retaining their original text.
The pinned archive retains every remaining source-file notice.

CMake's upstream `LIBXML_MINOR_COMPAT=14` selects ELF SONAME `libxml2.so.16`.
NEWS for 2.14.0 explicitly restricts binary compatibility to 2.14 or newer.
This provider does not impersonate old `libxml2.so.2`. Version 2.15 removed
the built-in HTTP client and LZMA support. No symbol renaming or ABI patch is
applied. Consumers must link explicitly to this provider and be checked.

The shared build keeps upstream's normal DTD, HTML, XPath, schemas, reader,
writer, serialization, threads and iconv functionality. Python, documentation,
legacy APIs, ICU, HTTP compatibility and zlib are disabled. Optional language
bindings are not installed; the CMake build does not invoke Python with those
options. Iconv and threads are supplied by the build platform, not vendored.
The C consumer resolves this exact installed CMake package and uses `dladdr`
and the runtime version to detect accidental linkage to another libxml2.

The oversized-input test checks libxml2's normal text-node limit without
`XML_PARSE_HUGE`; it is not a general application input-size policy. The test
uses no external document, DTD, network endpoint or physical device.
GCC16 cross compilation, real package installation and this provider contract
now pass in EmberBSD AArch64 QEMU. The current FFmpeg CPU package uses the
same library. Other consumers and physical platforms remain separate work.
The original project-prefix helper and the cross package retain their distinct
installation scopes.
