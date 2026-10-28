# GNU grep common source

This package tracks GNU grep 3.12, distributed under GPL-3.0-or-later.
The pkgsrc patch retains its existing working-grep adjustment. The EmberBSD
`--with-base-libintl` option is for consumers that intentionally link the OS
base gettext API; it verifies the public API by linking and leaves the default
pkgsrc NLS and PCRE2 options unchanged. The configure and configure.ac patches
are maintained together and have not yet been submitted upstream.

The source helper in `scripts/source-inputs/grep` prepares this recipe's full
patch set for native OS integration; it does not install a package. Test the
base gettext option using `tests/base-intl.py` with an explicitly selected
cross compiler, linker, shell and target sysroot. This tests linking, not target
execution or translations.

The `rawmemchr` patch adapts the upstream gnulib sanitizer-compatible path:
instrumented builds use bytewise reads while normal builds retain upstream's
word-at-a-time implementation. This enables ordinary sanitizer checks; it
does not claim to eliminate that production implementation's documented
object-bound overread or establish complete memory safety.
