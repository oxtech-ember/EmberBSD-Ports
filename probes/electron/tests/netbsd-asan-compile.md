# NetBSD sanitizer compile validation

NetBSD declares `backtrace(void **, size_t)` with a `size_t` result; the
NetBSD branch passes the span length directly. Other platforms retain their
existing conversion and saturation. The path provider keeps `NOTREACHED()`
fatal and no longer has an unreachable return.

For Electron 45.3.2 NetBSD amd64 and Clang 23.1.4, actual saved ASan/UBSan/vptr
target compile commands passed for the changed translation units. The revised
`stack_trace_posix.cc` SHA-256 is
`88bba44102b7490179eba0a195bf56a1eee41b3251cf8208f6ce5f3135634aee`;
`base_paths_posix.cc` is
`ae6e86d68dbfe78b6ccbc2a2749dd53eda973af957fc78f9d07c03f2bbca1e35`.
Actual production target compile commands also passed before and after.
The resulting code, relocations, and read-only data matched for both units;
the path comparison used the same source pathname and preserved line numbers
to account for `__FILE__` and `__LINE__`. This verifies these two translation
units, not the complete application or a native sanitizer test run.
