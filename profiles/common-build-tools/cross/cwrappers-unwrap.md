# Libtool archive directory boundaries

The common profile supplies `cwrappers-20220403nb1` from the pinned pkgsrc
sources. Its [source patch](../patches/pkgsrc-cwrappers-unwrap-boundary.patch)
repairs installed Libtool archive rewriting. A rule for `/sdk/runtime`
previously also rewrote `/sdk/runtime-other/libexample.la`, because the
archive path check examined its final slash instead of the character after
the matched prefix. The repaired check requires that directory separator.
Both `libexample.la` and module names such as `plugin.la` retain their
existing behavior inside the selected directory. The compiler-wrapper
dependency minimum requires the repaired package.

The same module now releases its temporary output pathname after a successful
file replacement. No compiler flags, native/target selection, or wrapper
diagnostics are disabled.

Run the [native regression](../tests/cwrappers-unwrap.rb) with prepared native
pkgsrc tools, genuine Libtool, GCC16.2.0 and Valgrind:

```sh
CC='/absolute/native/gcc -B/usr/bin/' \
NATIVE_MAKECONF=/absolute/native.mk.conf \
ruby profiles/common-build-tools/tests/cwrappers-unwrap.rb \
  /absolute/prepared-pkgsrc /absolute/native-prefix \
  /absolute/native-prefix/bin/libtool /absolute/new-check-directory
```

The check builds the real upstream wrapper programs in private directories.
Two genuine native shared libraries expose the original installed-metadata
error through Libtool link and install. The repaired wrapper maps the intended
directory and preserves the sibling archive. Additional actual-module checks
cover both archive basename branches, nested directories, short unrelated
paths, and the existing exact/child/sibling `-L` behavior. With
`NATIVE_MAKECONF`, real package metadata also checks the package revision and
ordinary consumer dependency minimum. No package database is modified.

These checks pass on Linux with GCC16.2.0 and Libtool2.6.2. The bounded module
contract releases its own arguments and process-lifetime rewrite rules;
strict Memcheck3.24 reports the original 33-byte temporary-path leak in two
blocks and zero errors/leaks after repair. This is not a whole-program leak
claim. The separate complete wrapper invocation still fails strict Memcheck:
configuration and argument storage in `common.c` and `base-wrapper.c` remains
allocated at exit. The measured before/after definite loss is 498/457 bytes;
1,252 bytes remain reachable in both. These preexisting CLI ownership findings
belong to a separate cwrappers cleanup; no suppressions were used.

GCC16 `-fanalyzer` and Clang19 Static Analyzer report no diagnostics for the
changed module and its contract. Cppcheck2.22's direct source analysis retains
unchanged variable-scope/const-pointer style findings and isolated-module
unused-function reports. It also reports unavailable system includes while
reading the real nbcompat headers. Analysis of the fully GCC-preprocessed
translation unit stops at glibc's `__signed__ __int128` declaration, so no
complete Cppcheck acceptance is claimed. Native package installation,
integration with cross-library path rules, and target execution remain
separate checks.
