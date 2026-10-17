# Host GMP test adaptation

`gmp-t-rand-varargs.patch` is an EmberBSD/AI-assisted local adaptation of
GMP 6.3.0 `tests/rand/t-rand.c`, from the original archive pinned in
`../host-sources.tsv`. It is not an accepted upstream backport.
The affected test is copyright Free Software Foundation, GPL-3.0-or-later;
its copyright/license header is preserved in the extracted source.

The [GMP API](https://gmplib.org/manual/Random-State-Initialization) requires
an `unsigned long` third variadic argument for the obsolete `gmp_randinit`.
The upstream test passes `int` values, while `rand/rand.c` reads
`va_arg(ap, unsigned long)`. On Apple Silicon macOS with GCC16.2, the original
test exits with an invalid-argument error before its value comparisons.
An explicit cast makes its integer/float table checks pass against the same
unchanged static library. The print-mode call is corrected as well.

The adaptation changes only argument types. It preserves all expected values,
algorithms and tests; no test is skipped and no library code changes.
`host-math.sh` verifies and records the patch hash, applies it with zero fuzz,
and still requires the full upstream GMP/MPFR/MPC suites and host contracts.
