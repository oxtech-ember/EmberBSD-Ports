# Expat

This common recipe selects [Expat 2.10.0](https://github.com/libexpat/libexpat/releases/tag/R_2_10_0).
The official release archive SHA256 is
`5466a341f9c692ef7a958a6881311be597f8e1ce345984cf78414f54793dea4c`.
The recipe retains the NetBSD pkgsrc attribution and the upstream license.
It applies no Expat implementation patch.

Upstream examples and tests remain enabled. Examples are not installed.
Run `bmake test` for the native upstream suite. Cross-built test executables
require a target runner. A successful package build does not establish target execution.

The pkgsrc package API and ABI dependency floors are 2.10.0 for native and cross consumers.
Built-in provider selection retains the pkgsrc API contract.
The release retains SONAME `libexpat.so.1`. The upstream libtool version is 14:1:13.

[CVE-2025-66382](https://github.com/libexpat/libexpat/issues/1076) remains open upstream.
This recipe does not suppress the vulnerability audit or claim that issue is fixed.
Package, consumer and target runtime checks remain separate acceptance gates.
