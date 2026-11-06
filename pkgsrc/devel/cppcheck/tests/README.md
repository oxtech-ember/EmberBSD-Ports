# Cppcheck preprocessor-limit fixtures

`preprocessor/has-feature.cpp` and `preprocessor/has-include-next.cpp` are
accepted by the selected EmberBSD target Clang 23.1.4 (`aarch64-unknown-netbsd`)
with the actual libc++ and Clang include search paths. Cppcheck 2.22.0 reports
`[syntaxError]` for the function-like `__has_feature(...)` and
`__has_include_next(...)` expressions in these minimal fixtures.

Use the selected target compiler and flags to compile both files with
`-fsyntax-only`; add `-I tests/preprocessor/include-next` for the second file.
For Cppcheck, use the selected source `cfg/std.cfg`, `--std=c++17`, and
`--platform=unix64`; add the same `-I` directory for the second file. Cppcheck
returns status 0 despite printing `[syntaxError]`, so inspect diagnostics rather
than treating its exit status as proof that preprocessing succeeded.

With actual SDK system include paths, Cppcheck 2.22.0 also stops on compiler
preprocessing constructs inside libc++/NetBSD headers, including
`__has_feature`, `__has_include_next`, and `_Pragma`. This is a scoped parser
limitation; these fixtures do not claim broader standard-library analysis.
