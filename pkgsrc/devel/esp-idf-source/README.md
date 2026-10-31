# ESP-IDF component source

This package supplies the upstream ESP-IDF 6.1 `components` tree, with the
Wi-Fi and PHY binary-library submodules pinned by that release. It preserves
their original source, binary files, license notices and submodule READMEs;
no upstream patches are applied. Other ESP-IDF submodules, the IDF build tools,
examples and documentation are not packaged. This is a source input, not a
complete ESP-IDF SDK or an EmberBSD driver.

The Wi-Fi and PHY archive READMEs state that their binary Object form is
provided under Apache-2.0. The component tree also contains code and notices
under MIT, BSD, ISC, CC0 and GPL terms. Consumers must retain the applicable
notices, choose their own target ABI and tools, and verify compatibility at
any boundary with the binary libraries.

For `components/linux/fls.c`, the package includes the original
BSD-4-Clause-UC text as `COPYING.BSD-4-Clause-UC`; `fls.c` carries its
Regents' copyright notice. The University of California subsequently
[removed the advertising clause](https://spdx.org/licenses/BSD-4-Clause-UC.html)
retroactively, which is reflected in the package's `modified-bsd` metadata.
Some files use the deprecated SPDX identifier `BSD-2-Clause-FreeBSD`;
`COPYING.BSD-2-Clause-FreeBSD` records its reference text including the views
disclaimer. Original file-specific notices remain with the component sources.

The shared path is `${ESP_IDF_SOURCE_DIR}` from `Makefile.common`. Consumers
should use the common component source rather than another embedded copy.
The bundled WPA, cryptography and other third-party sources do not replace
their common Ports recipes. Consumers select the corresponding common
sources and runtimes; this package owns the IDF-specific glue and vendor ABI.
