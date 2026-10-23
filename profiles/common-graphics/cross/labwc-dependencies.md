# Current text and image dependencies for labwc

This is the package-building and installed text-rendering stage for the common
labwc stack. It uses the accepted macOS-to-AArch64 tools and one target
`/usr/pkg`. Text shaping, CPU rasterization and PNG roundtrips pass on AArch64.
It does not establish a working labwc session or SVG support.
The [Rust 1.99 std-only cross probe](../../../probes/rust-cross-std/README.md)
now passes allocation, threads, TLS destructors, unwind and C `dlopen` consumers
in AArch64. The [shared Rust/cargo-c and target std packages](../../common-build-tools/rust.md)
are now installed and accepted; full librsvg remains a separate stage.
The accepted wlroots renderer and DRM scenarios remain documented in
[wlroots](wlroots.md) and [DRM/input](drm-input.md).

## Sources and composition

The profile exports current upstream recipes for GLib 2.90.1, PCRE2 10.49,
FriBidi 1.0.17, libpng 1.6.59, FreeType 2.14.3, HarfBuzz 15.0.0, Cairo 1.18.6
and LZO 2.10. Exact archive URLs and SHA256 hashes are in
[`sources.tsv`](../sources.tsv); pkgsrc checks the archives and patches again.
GLib's tools, D-Bus code generator and introspection recipe share its version.
They do not select an older GLib for build-host tools.

The pinned pkgsrc tree already supplies current Brotli 1.2.0, fontconfig 2.18.3
and Graphite 1.3.15. Their unchanged recipes remain in that tree. The profile
also exports Pango 1.58.2 and libXt 1.3.1 with cross-build corrections below.
The required native gperf 3.3 and GLib Python tools use the existing common
host prefix. LLVM, Mesa, compilers and Python are reused.

Release checks use the upstream
[GLib index](https://download.gnome.org/sources/glib/2.90/),
[PCRE2 release](https://github.com/PCRE2Project/pcre2/releases/tag/pcre2-10.49),
[FriBidi release](https://github.com/fribidi/fribidi/releases/tag/v1.0.17),
[libpng announcement](https://libpng.org/pub/png/libpng.html),
[FreeType news](https://freetype.org/index.html),
[HarfBuzz release](https://github.com/harfbuzz/harfbuzz/releases/tag/15.0.0),
[Cairo releases](https://cairographics.org/releases/), and
[LZO's current release and published fix](https://www.oberhumer.com/opensource/lzo/).
The APNG option retains its matching 1.6.59 upstream patch and checksums.

## Cross-build changes

GLib's build-time Python is `TOOL_PYTHONBIN`; installed scripts retain the
normal target interpreter. Its portability patches are refreshed against the
exact 2.90.1 sources. The new upstream FreeBSD `environ` implementation is
preserved. The traffic-class test checks socket-option availability individually:
NetBSD's missing `IP_RECVTOS` does not disable its available IPv6 test.
Compilation does not establish that this IPv6 runtime test passes.

Cairo's Quartz and FreeType's Carbon selection now require target `OPSYS=Darwin`.
A framework directory on a macOS build host does not enable that target backend.
Native Darwin selection is unchanged. NetBSD's usual Cairo X11 backend remains
enabled. FreeType also receives the existing common profile's absolute build
compiler as `CC_BUILD`. Otherwise its empty pkgsrc `NATIVE_CC` let `gcc` resolve
to a target wrapper and produced an ELF `apinames` generator for the Mac.
The corrected build produces a real host executable and target libraries.

FriBidi explicitly declares its new `pkg-config` build requirement. Its release
archive includes `fribidi.1`; cross builds retain that exact page instead of
executing the target binary through `help2man`. An absent page fails. Native
generation keeps the original rule. The installed package includes the page.

LZO 2.10 remains the latest release. The profile applies its authors' published
one-byte LZO1F safe-decoder bounds fix, with attribution in the patch. The
regression reproduces the original heap overread under AddressSanitizer and
checks that the corrected decoder returns `LZO_E_INPUT_OVERRUN` with no output.
This is a native source-level check, not target runtime acceptance.

libXt's common cross recipe keeps the verified host compiler as `CC_FOR_BUILD`
and excludes target headers from that host generator. The original recipe's
empty `NATIVE_CC` overwrote the configured compiler and produced an AArch64
ELF `makestrs`, which macOS cannot execute. The corrected Mach-O generator
reproduces all three upstream C/header outputs byte for byte. Native selection
is unchanged; Pango's X11 option remains enabled.

Pango's target utilities need its in-tree `libpangoft2` while linking through
`libpangocairo`. The macOS cross linker cannot resolve that indirect dependency
from a target runtime path. A NetBSD cross-only `-rpath-link` supplies the build
directory without adding it to installed ELF RPATH. The original actual link
fails and the same command with this one flag succeeds. Native flags remain
unchanged. Run this regression before installing Pango into the sysroot,
otherwise an installed `libpangoft2` could conceal the original failure.

## Reproduction

Prepare the `common-graphics` export and use the composed cross configuration
described in [the cross-build guide](README.md). Select a new absolute work
directory, an existing shared distfile cache, and at most two build jobs.
Keep the recipe snapshot immutable during a build. Use the actual native
Python/Meson, accepted GCC16 tools, and current target sysroot.

Build ordinary pkgsrc `package` targets in dependency order: PCRE2, GLib,
FriBidi, PNG, FreeType, fontconfig, HarfBuzz, Cairo and Pango. pkgsrc resolves
the remaining normal prerequisites. Host-only `glib2-tools` and `gdbus-codegen`
use the same exported GLib family with `USE_CROSS_COMPILE=no`. Install packages
into the cross sysroot with its standard pkgsrc install command; do not suppress
dependency, PLIST, ELF, RPATH or work-reference checks.

When changing a configure input after a failed build, clean that package's
work before retrying. A package revision change alone need not invalidate a
partially completed configure stage. Preserve the failed log and causal artifact.
A PLIST-only correction can restage the already built files without changing
their compile flags.

Focused tests use real package parsing, generated upstream rules and source:

```sh
BMAKE=/path/to/host/bin/bmake ruby tests/cairo-cross.rb \
  /path/to/pkgsrc /path/to/cross.mk /path/to/new-cairo-check
BMAKE=/path/to/host/bin/bmake ruby tests/freetype-cross.rb \
  /path/to/pkgsrc /path/to/cross.mk /path/to/new-freetype-check
GMAKE=/path/to/host/bin/gmake ruby tests/fribidi-cross.rb \
  /path/to/built/fribidi-1.0.17 /path/to/new-fribidi-check
HOST_CC=/path/to/native/clang ruby tests/lzo-overread.rb \
  /path/to/lzo-2.10.tar.gz /path/to/new-lzo-check
BMAKE=/path/to/host/bin/bmake ruby tests/libxt-cross.rb \
  /path/to/pkgsrc /path/to/cross.mk /path/to/original-libXt-source \
  /path/to/built-libXt-source /path/to/new-libxt-check
BMAKE=/path/to/host/bin/bmake READELF=/path/to/target-readelf \
  ruby tests/pango-cross-link.rb /path/to/pkgsrc /path/to/cross.mk \
  /path/to/built-pango-source /path/to/original-build.log /path/to/new-link-check
```

Run these commands from `profiles/common-graphics`. The first two regressions
require macOS with its actual framework directories. Their original controls
reproduce the cross-selection errors, then check corrected target behavior and
unchanged native selection. The FriBidi check needs the completed target ELF;
it does not substitute a fake executable. Each test preserves inputs and logs.

## Acceptance boundary

On 2026-10-08, ordinary package creation and installation in the AArch64 cross
sysroot passed for the following stack. pkgsrc's PLIST, interpreter, permissions,
ELF, RPATH and work-reference checks remained enabled.

| Package | Version |
| --- | --- |
| PCRE2 | 10.49 |
| GLib | 2.90.1 |
| FriBidi | 1.0.17 |
| libpng | 1.6.59 |
| Brotli | 1.2.0 |
| FreeType | 2.14.3nb1 |
| fontconfig | 2.18.3 |
| Graphite | 1.3.15 |
| HarfBuzz | 14.6.0 |
| LZO | 2.10nb1 |
| Cairo | 1.18.6 |
| libXext / libXrender | 1.3.7 / 0.9.12 |
| libXt / libXft | 1.3.1nb1 / 2.3.9 |
| Pango | 1.58.2nb2 |

Native GLib generators and `gdbus-codegen` 2.90.1, plus gperf 3.3, also passed
normal pkgsrc package checks. All six focused regressions above passed. The
frozen exporter passed 67 refusal controls and all six profile compositions;
it validates 27 source pins. Pango's X11, Cairo and fontconfig options remain
enabled. Its four installed DSOs have canonical target runtime paths only.

The installed consumer below also passes in an isolated EmberBSD/NetBSD 11
AArch64 VM. The eventual labwc client/compositor scenario remains separate
acceptance. The matching APNG patch is retained, but this package run used the
unchanged default without APNG; it does not establish APNG runtime support.

The separate [GLib introspection package](introspection.md#glib-2901-metadata-package)
now cross-builds all seven GIR/typelib pairs with native generators and real
target GType queries. Its installed metadata passes four load/invoke cycles on
CM5. Full SVG still needs the current librsvg provider and its accepted
Rust/tooling closure; that application acceptance remains separate.

## Installed text and PNG acceptance

[`prepare-text-render.rb`](prepare-text-render.rb) compiles
[`text-render.c`](text-render.c) against the installed package headers and
pkg-config modules, using the accepted GCC16 tools. Supply an accepted DRM
bundle, the exact current package archives including their full dependency
closure, the pinned Pango release archive, and the unchanged upstream
[DejaVu font license](https://raw.githubusercontent.com/dejavu-fonts/dejavu-fonts/version_2_37/LICENSE).
The helper checks archive identities, installed payloads, recursive ELF
dependencies, source/license hashes and canonical runtime paths. It includes
the unmodified DejaVu font from Pango's release archive and its full license.

```sh
ruby prepare-text-render.rb /path/to/cross-tools /path/to/sysroot \
  /path/to/host/bin/pkg-config /path/to/accepted-drm-bundle \
  /path/to/pango-1.58.2.tar.xz /path/to/DejaVu-LICENSE \
  /path/to/new-text-work /path/to/packages/*.tgz
# On the matching target, with those packages installed under /usr/pkg:
mkdir /absolute/private/text-bundle
tar -xzf text-render.tar.gz -C /absolute/private/text-bundle
sh /absolute/private/text-bundle/run-text-render.sh \
  /absolute/private/text-bundle /absolute/private/new-text-logs
```

Pass a directory containing only the selected target archives, not host
packages or old versions. The target needs its normal base libraries and
utilities, including `libintl`, `libbz2`, `ldd`, `sha256` and `timeout`. A minimal
synthetic root must supply those too; package-only verification is insufficient.
No library search override or installed font cache is needed. A private
Fontconfig configuration admits exactly the sealed fixture, checked again for
every Pango run. The target runner checks payload hashes before and after use
and records actual loaded providers, including dynamically opened libraries.

Four create/draw/destroy cycles passed: GLib's real PCRE2 capture, FreeType font
loading, HarfBuzz `ffi` ligatures on/off, three Latin/Cyrillic/Arabic lines,
three Pango runs and 16 glyphs without missing characters. Each cycle changed
3023 pixels inside the declared ink bounds on a 640x192 image. PNG encoding
and decoding preserved every color and alpha value. The two generated negative
controls must return 1 at their exact oracle: omitted drawing fails the pixel
check; disabled ligatures fail shaping. A loader error or timeout is a failure
of the check, not a passing negative control. The decoded image was also
visually inspected; its per-glyph geometry has no golden-image assertion.

This validates CPU text composition and PNG through the installed common
stack. It does not exercise GPU glyph rendering, Wayland client surfaces,
X11/Xft drawing, SVG, APNG, target introspection or a complete desktop session.

The next [desktop-support stage](desktop-support.md) supplies current libsfdo,
D-Bus and font/theme data with normal cross-package checks. Its session-bus
and freedesktop-library checks are separate from this text-rendering acceptance.
