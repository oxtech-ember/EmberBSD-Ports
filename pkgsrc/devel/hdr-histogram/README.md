# HdrHistogram

The shared and static libraries use the common zlib provider. The optional
`HDR_BENCHMARKS=yes` build uses the common Google Benchmark package rather than
a vendored copy.

The 0.12.1 native Darwin/arm64 build passed all 9 upstream tests, plus shared
and static consumers checking recording, percentiles, and an out-of-range
value. The optional benchmark configuration and EmberBSD target execution
have not been checked by those results.
