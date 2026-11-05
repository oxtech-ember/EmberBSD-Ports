# Chromium WOFF2 source parity

Chromium uses upstream WOFF2 commit 1c69169e9e1811dccd6c54c532fedda300233968;
this patch backports the complete include/ and src/ delta from v1.0.2
(tag 1bccf208bca986e53a647dfe4811322adb06ecf8). It includes upstream
glyf overflow checks, overlapSimple bitmap support, safe type-punning,
128 MiB output limit and 32-bit buffer bounds fixes. The existing cstdint
patch is equivalent to the upstream stdint include. Chromium's Brotli
submodule is intentionally not used; the shared Ports Brotli remains selected.
Upstream code retains its original MIT license and authorship.

`buffer-test.cc` exercises rejected out-of-range offsets, boundary reads,
and a normal read; compile it with the selected C++ compiler and `-Isrc`.
