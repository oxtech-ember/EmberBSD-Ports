# RustCrypto API migration

The common stable crates remain crypto_box 0.9.1 and crypto_secretbox 0.1.1.
The four Rust source files carry the upstream RustCrypto API migration,
from crypto_box 0.10.0-pre.0 commit 9d021008360d05bc27ff248f33eb6123da0214ac
and crypto_secretbox 0.2.0-pre.0 commit a3b43a64bb655ec2f8193768a62d696d83a9f3a7.
Both sources are dual licensed MIT OR Apache-2.0. Original stable tests/lib.rs
and their vectors remain unchanged. The target graph uses crypto_box alloc,
salsa20 and std, and crypto_secretbox salsa20. The aead 0.6 trait transition
no longer exposes the old heapless and stream features; this migration does not
claim support for those features. The explicit provider feature tests exercise both crates and preserved vectors on
the target, including detached out-of-place operation and failed-tag handling. No real wallet keys or transactions are used.
