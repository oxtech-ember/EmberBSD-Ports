# HTML dependencies for QtTools

Qt Assistant uses the shared litehtml renderer. The toolkit selects
[litehtml 0.10](https://github.com/litehtml/litehtml/releases/tag/v0.10) and
[gumbo-parser 0.14.1](https://codeberg.org/grisha/gumbo-parser/src/tag/0.14.1).
Original archives, SHA256 and recipe checksums are in
[the toolkit manifest](../sources.tsv). Original pkgsrc recipe ownership and
upstream licences are retained. These packages belong to EmberBSD-Ports.

The litehtml recipe retains the shared-library and private gumbo-link patches.
Its full PLIST includes the new parser, encoding, gradient and font headers;
the removed `tstring_view.h` is no longer listed. Consumers use one external
gumbo library. Both the shared and static gumbo libraries remain packaged.

## Confirmed on CM5

On 2026-10-12, GCC16 cross builds passed ordinary package checks for files,
ELF dependencies, interpreters, permissions, PIE, RELRO, RPATH and work paths.
Both packages installed normally on CM5 and in the common build sysroot.
The board is CM5 Rev 1.0, BCM2712D0, 4 GiB RAM, on a Waveshare CM5-NANO-B.
Kernel `EMBERV3DRENDER #1` has SHA256
`6c5aa74d3c33fb6e84ea5c04d6f3df48928deb021cdc908ee972a42df03c7bf5`.

| Package | SHA256 |
| --- | --- |
| gumbo-parser-0.14.1.tgz | `7d124c0a88b5e4f04bfcdbad59596326fd3a0fba55b690baee4cddfde30b208d` |
| litehtml-0.10nb1.tgz | `17f29bcb796012eab020a0342d7ec67731291ea255af5dff96944760aaa0b8e3` |

All 220 original gumbo tests passed against the installed `libgumbo.so.4`.
Run the cross-built `gumbo_test` in a directory containing the original
`tests/` fixtures, as in upstream's Meson test definition. The target must
use the installed library; no private `LD_LIBRARY_PATH` is needed.

The [litehtml runtime runner](../tests/litehtml-runtime/README.md) passes its
unchanged upstream UTF-8 test and two additional CSS flag regressions.
The tests ran in the same boot. Installed library hashes are:

- `libgumbo.so.4.0.1`: `39d5a41bfd50c30d318342254ce4a686e7f39d6a0ef2809bef92919374af4223`.
- `liblitehtml.so.0.0.0`: `dcdc617173f089983c6b24fe631b2450bdd86b4e1f1732d3f06fe4e729f29695`.

## Source analysis and correction

Cppcheck 2.22 checked the actual 12-file gumbo and 59-file litehtml compile
configurations. It found two negative shifts in litehtml's CSS keyword parser.
`none` and `over` have index zero and a zero mask, but upstream calculated
`1 << (index - 1)`. On CM5 the unpatched library returned `-2147483648`
instead of zero, and corrupted combinations such as `over right`.

The [0.10nb1 patch](../recipes/www/litehtml/patches/patch-src_style.cpp)
only shifts positive indexes. Both regressions fail before the patch and pass
after package replacement. Rechecking the changed source reports neither
negative-shift error. The new regression source also passes GCC16's analyzer.

This is not a warning-free analysis of the whole upstream library. Other
Cppcheck reports include initialization, cast and performance diagnostics.
Its moved-box paths assume `inserted` remains false after the code sets it
true; its `parse_keyword` report points at a forward declaration rather than
a read of the output parameter. Gumbo has one pointer-to-integer portability
report for its existing enum stack representation. No unrelated algorithm
was rewritten to silence these reports.

Full image-comparison tests, Valgrind on the target, the installed Qt Assistant
consumer and the complete QtTools package remain separate acceptance steps.
[Full QtTools](qt-packages.md#full-qttools-package) now cross-packages against
this shared HTML provider, including Assistant and QDoc. Its target runtime
remains unaccepted. These parser tests do not establish HDMI output, KWin or
accelerated Plasma.
