# Cppcheck Darwin pthread parser limitation

With Cppcheck 2.22.0 and the selected SDK Clang 23.1.4 on Darwin arm64,
preprocessing the two-line `darwin-pthread.c` using the host OS SDK and then
checking the result causes Cppcheck's builtin parser to report `syntaxError`
at `_mach_port_t.h:50`: `syntax error: "pragma" .. typedef`. The same input
is accepted by Clang. Set `HOST_PREFIX` to the selected native SDK and
`DARWIN_SDK` to the host SDK actually used by that toolchain:

```sh
"$HOST_PREFIX/bin/clang" -isysroot "$DARWIN_SDK" -E pkgsrc/devel/cppcheck/tests/darwin-pthread.c -o /tmp/cppcheck-darwin-pthread.i
"$HOST_PREFIX/bin/clang" -isysroot "$DARWIN_SDK" -fsyntax-only /tmp/cppcheck-darwin-pthread.i
"$HOST_PREFIX/bin/cppcheck" --language=c --error-exitcode=1 /tmp/cppcheck-darwin-pthread.i
```

The last command currently fails; this is not an acceptance pass. The next
result is for the Cppcheck owner to repair the parser and analyze this input,
then recheck real affected translation units. Keep generated SDK headers and
preprocessed output local; do not commit them.
