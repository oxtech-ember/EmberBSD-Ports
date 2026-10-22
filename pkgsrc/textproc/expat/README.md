# Expat

This common recipe selects [Expat 2.9.0](https://github.com/libexpat/libexpat/releases/tag/R_2_9_0).
The official release archive SHA256 is
`16afbb9cefead2aa278105cf27d9f597bde7fbf3dbb85015857ca7ca6a4e89ba`.
The recipe retains the NetBSD pkgsrc attribution and the upstream license.
It applies no Expat implementation patch.

Upstream examples and tests remain enabled. Examples are not installed.
Run `bmake test` for the native upstream suite. Cross-built test executables
require a target runner. A successful package build does not establish target execution.

The pkgsrc package ABI dependency floor is 2.9.0 for native and cross consumers.
Built-in provider selection retains the pkgsrc API contract.
The release retains SONAME `libexpat.so.1`. The dropped attribute-info interface
was disabled in the previous package configuration.

[CVE-2025-66382](https://github.com/libexpat/libexpat/issues/1076) remains open upstream.
This recipe does not suppress the vulnerability audit or claim that issue is fixed.
Package, consumer and target runtime checks remain separate acceptance gates.
