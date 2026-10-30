# Qalculate 5.13.2 validation boundary

The source is the upstream 5.13.1 distribution plus the complete upstream
`d3672af9cf6e05a39bd4206b7b7d6b1e0d194caa` delta for tag 5.13.2. That tag
publishes Windows binaries; its source tree retains the 5.13.1 version string.

The EmberBSD amd64 package has SONAME `libqalculate.so.23`, uses the common
gettext, iconv, ICU, GMP, MPFR and curl providers, and built its `fixpo`
generator with the selected native C++ compiler. On Nick an isolated target C++
consumer passed arithmetic and the bounded function/print depth boundaries
1500/1501 and 500/501. The same arithmetic and bounded guard cases passed in an isolated native
ASan/UBSan build with leak detection enabled. A separate intentional-leak
control confirmed that the selected runtime detects leaks. This does not
claim the Plasma calculator runner.

Clang Static Analyzer was run on the five changed target translation units
using their actual build arguments. Baseline 5.13.1 and the patched tag had
identical diagnostics at corresponding source lines; existing upstream
findings remain, so this is not a claim of a clean upstream analysis.

Cppcheck 2.22 could not complete the target-header configuration: the selected
libc++ uses `__has_cpp_attribute`, which the tool could not evaluate. Running
Cppcheck on the actual target Clang-preprocessed Number.cc also stopped with
`syntaxError: Unmatched '}'` at target `locale.h`. The earlier partial
`danglingLifetime` report in Number::print reproduced on the 5.13.1 baseline.
No Cppcheck pass or Valgrind run is claimed.
