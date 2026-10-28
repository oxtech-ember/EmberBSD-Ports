# tcb/span

This is the common single-header C++11 span provider used by LIEF. Upstream
has no tagged release; the recipe selects its current master commit
`836dc6a0efd9849cb194e88e4aa2387436bb079b` (2022-06-15), checked on
2026-10-28. The GitHub source archive SHA256 is
`66650479f85b92c6a6230706e4ac4a1bca18a7c7102fc7e02ad332f86548c9b6`.
The Boost Software License is installed alongside the package.

`tests/consumer.cpp` checks array views, slicing, mutation and empty spans
against the installed header with the selected C++ compiler. A host consumer
is distinct from cross-package or target execution validation.
