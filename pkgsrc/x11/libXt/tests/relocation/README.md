# Native relocation checks

The fixture uses a selected native Clang and libX11/libXt build outputs, no X
server. `probe.c` checks relocated XErrorDB, unique XKeysymDB entry, the
locale search directory, and XSupportsLocale. `xt-probe.c` initializes an Xt
application context and checks its relocated XtErrorDB. Run old and new dylibs
from separate relocated prefixes through a loader path containing only the
respective relocated libraries. Seed each prefix with the fixture resource
files and the owner locale data. The expected old result is failure; the new
result is success. Use DYLD_PRINT_LIBRARIES to confirm actual loaded dylibs on
Darwin. Explicit XKEYSYMDB and XLOCALEDIR must continue to win or precede the
relocated default; do not use a path that alters unrelated host library loads.

The small `probe/xt-test` exercises the actual Xt template lexer and common
private resolver on `%:`, `%%:`, trailing `%`, `%D`, `%N`, external paths, and
`%N/..`. It is a helper test, not an actual XtResolvePathname/X server test.
