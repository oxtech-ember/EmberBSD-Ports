# Cppcheck constexpr specialization parser limitation

Cppcheck 2.22.0's built-in parser reports `syntaxError` on line 11 of
`constexpr-specialization.cc` when the GNU `warn_unused_result` attribute
precedes an explicit specialization whose non-type argument is a constexpr
member call. Removing that attribute allows analysis. The selected SDK Clang
23.1.4 accepts the original input:

```sh
"$HOST_PREFIX/bin/clang++" -std=c++20 -fsyntax-only pkgsrc/devel/cppcheck/tests/constexpr-specialization.cc
"$HOST_PREFIX/bin/cppcheck" --std=c++20 --enable=warning --error-exitcode=1 pkgsrc/devel/cppcheck/tests/constexpr-specialization.cc
```

The same parser limitation appears in the actual preprocessed Node 26.13.1
`crypto_context.cc` at `v8-fast-api-calls.h:764`. Cppcheck's `--clang` mode
on that full translation unit separately aborts in `token.cpp:195`
(`update_property_info`); it is not a successful analysis. Keep diagnostics
visible. Use the selected compiler's static analyzer and scoped sanitizer
checks as separately reported evidence until the Cppcheck owner fixes and
verifies both cases; this fixture alone does not cover the second abort.
