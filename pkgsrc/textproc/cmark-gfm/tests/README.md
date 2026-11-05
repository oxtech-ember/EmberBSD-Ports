# Parser policy regression

`quote-depth.c` links to the built cmark-gfm library. Compile with the selected
SDK compiler, target sysroot, include and library directories for this package;
run the resulting binary on the matching target. It checks the original
unlimited default, an explicit 512 cap, preservation over parser reuse, and
restoring the default. A pre-patch library lacks the new API and must not be
reported as passing. The fork's upstream pathological cases remain in the
ordinary package test suite; this test specifically verifies shared policy.

`abort.c` verifies that an asserted external flag aborts parsing, that the
pointer survives parser reuse, and that setting it to NULL detaches it. Keep
the flag alive and do not write it concurrently while parsing. Run the binary
under the same memory instrumentation as the library.
