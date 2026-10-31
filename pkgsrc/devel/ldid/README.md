# Native Mach-O signer

The common ldid recipe builds the upstream signer with the selected Ports
libcrypto and libplist. Its OpenSSL 4 patch keeps certificate signing and
uses an implicit cdhash requirement for ad-hoc signing.

On Darwin, run `files/test-adhoc-signing.py` with `--cc`, `--ldid`, and
`--verifier` set to the selected native compiler, signer, and macOS codesign
verifier. It checks an entitlement, strict verification, and rejection after
tampering. A native build, Clang Static Analyzer, and ASan/UBSan signing runs
were also exercised. A temporary self-signed key exercised certificate-signing
output; this does not establish a trusted certificate chain.

Cppcheck's native parser could not parse the OpenSSL ASN.1 macro, and its Clang
AST importer terminated on an assertion. Those checks remain outstanding until
the analyzer can process this translation unit.
