# PFFFT consumer checks

Build `roundtrip.c` against the installed `PFFFT::PFFFT` provider and run it
on the selected host or target. It checks a known real spectrum and inverse
transform. Run upstream CTest and the standalone float, double, and C++ FFT
binaries as well; they cover more transform sizes and convolution.

`unaligned.c` deliberately violates the 16-byte SIMD FFT precondition. In a
checked build with assertions enabled, it must stop at the alignment assertion.
Do not execute this negative case against a release build with assertions
removed. For NEON, run the upstream `--test-simd` checks and the aligned FFT
cases under UBSan. Repeat applicable tests for scalar and other target backends.

## Chromium compatibility

The common owner adapts [Chromium's PFFFT patches at revision
`40c5dfa29b9818dbd7acf7f083e03c5334e02160`](https://chromium.googlesource.com/chromium/src/+/40c5dfa29b9818dbd7acf7f083e03c5334e02160/third_party/pffft/patches/):
`01-rmv_printf`,
`02-decl_validate_simd`, and `03-malloca` changes: legacy SIMD validation is
silent and declared, and the MSVC scratch allocation is released for both
precisions and scalar/SIMD paths. If MSVC cannot allocate required internal
scratch, the void API terminates rather than using a null pointer; externally
provided scratch remains usable when the small fallback allocation fails.
Chromium's `04-fix_ptr_cast` is already
covered by upstream's `uintptr_t` alignment checks. Its `05-fix-arch-detection`
is covered for Clang/GCC by upstream's SSE feature detection and Ports'
AArch64 NEON patch. Pure MSVC keeps the existing backend fallback. The explicit extended SIMD
diagnostic API retains its output.

Run `chromium-compat.py --cc SELECTED_CC --source PREPARED_SOURCE`, adding
`--cc-arg=OPTION` for the selected toolchain's sysroot flags. Add
`--msvc-simulation` to count fake `_malloca`/`_freea` calls or `--scalar` to
exercise the scalar path; this simulation is not a Windows runtime test.
`--compile-only` builds a target executable without trying to run it. Run
`arch-guards.py --cc SELECTED_CC --source PREPARED_SOURCE` to check the
preprocessor's ARM selection without requiring an ARM execution host.
