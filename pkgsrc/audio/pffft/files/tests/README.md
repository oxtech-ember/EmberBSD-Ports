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
