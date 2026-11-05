# Explicit target regressions

After the provider has been built and staged, run the package's explicit
`bmake telegram-regressions` target with the selected target SDK configuration.
It uses only the already resolved normal/build Cargo graph, compiles four target
ELFs into the work directory, and never runs target code on the host. Run those
ELFs on the selected target; they use synthetic public test inputs, no network,
no real account and no real wallet key.

The RustCrypto secretbox/box vectors originate in crypto_secretbox and
crypto_box upstream tests (MIT OR Apache-2.0). Tolk hashes and wallet addresses
come from public donor wallet tests. The mnemonic is an upstream public fixture.
The C++ test exercises the generated package headers and static archive.

`crypto-inout-features.rs` additionally exercises detached out-of-place
encryption/decryption, failed-tag output preservation, and optional features.
It was tested using an explicit separate all-features test graph; that graph
is not added to the regular provider build. Vectors originate from RustCrypto
crypto_box/crypto_secretbox upstream tests (MIT OR Apache-2.0).

`bmake telegram-crypto-features` explicitly fetches and verifies five test-only
crates through pkgsrc, builds a separate offline test graph over the same patched
shared crates, checks both no-alloc modes and builds the combined feature probe.
Run the resulting target executable on the target. The optional
`EMBER_CRYPTO_TEST_RUSTFLAGS` sets additional target linker flags when required.
