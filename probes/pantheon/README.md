# Pantheon port probe: mutter and its new dependencies

First implementation step of the project's Pantheon direction (registry
debt E25): port **mutter** so that **gala** and the rest of the elementary
desktop can run on EmberBSD. Strategy: only current upstream releases;
every NetBSD adaptation lives in recipe patches here and is offered
upstream once it builds.

## Version pairing

| Component | Version | Source |
| --- | --- | --- |
| mutter | 46.9 (last micro of the line gala declares: `libmutter-14`) | download.gnome.org, SHA512 pinned |
| gsettings-desktop-schemas | 51.0 | download.gnome.org, SHA512 pinned |
| gnome-desktop (the `gnome-desktop-4` library) | 51.0 | download.gnome.org, SHA512 pinned |
| gala | 8.6.2 | later probe |

Freshness audit of the native build chain (2026-10-12): gtk 3.24.52 and
4.22.4, pango 1.58.2, cairo 1.18.6, gdk-pixbuf 2.44.8,
gobject-introspection 1.86.0, glib2 2.90.1, cmake 4.4.3 — current lines of
the pinned quarterly; the graphics profile pins Mesa 26.2.4,
libdrm 2.4.134, wayland 1.26.0 and wayland-protocols 1.49. No component of
the chain requires a version bump; fixes are patches only, per project
policy.

## Validation record (2026-10-12)

- Distfiles fetched from the original GNOME server; SHA512 recorded in
  each `distinfo`. `gnome-desktop` 51.0 confirmed to still build the
  `gnome-desktop-4` library; the GTK3 variant stays disabled.
- Six mutter portability patches authored against the pristine 46.9 tree,
  following the FreeBSD `x11-wm/mutter` reference for the gaps both BSDs
  share: local dma-buf UAPI definitions instead of `<linux/dma-buf.h>`
  (three files), no abstract unix sockets for Xwayland, optional
  `udev`/`udevdir` in meson (NetBSD uses `libudev-bsd`, which provides
  `libudev.pc`), and `HAVE_LIBSYSTEMD` guards with an XDG_SESSION_TYPE
  fallback for sd-login. All six apply cleanly to the pristine tree
  (verified with `patch -N -p1` on a fresh extract).
- `libopeninput` in the prepared common-graphics tree provides the
  `libinput` pkg-config module (soname-compatible libinput port), and
  `devel/libgudev` is 238, so `g_udev_device_get_current_tags` is
  available without the fallback patch FreeBSD needs.
- pkgsrc tree prepared with `scripts/prepare-pkgsrc.sh … common-graphics`
  on the project storage volume; probe recipes live here and graduate to
  a profile after the first successful build.

## Not yet done

- Native build of any of the three recipes (meson configure will finalize
  the dependency link set; PLIST files are placeholders until then).
- gala, wingpanel, plank, granite and the session components.
- Headless mutter smoke test in the AArch64 VM and hardware acceptance.

## Dependency fixes

### gtexinfo 7.3 under GCC 16

The gtk3 dependency chain builds `devel/gtexinfo` (texinfo 7.3). Its two
bundled gnulib `gettext.h` copies collide with an earlier-included
`gettext.h`: that header defines the `pgettext*_expr` shortener macros, and
the bundled copy then defines same-named functions, which the preprocessor
expands into a syntax error (`expected declaration specifiers before '('`,
first hit `tta/gnulib/lib/gettext.h:283`). The toolchain is not rolled
back; the port carries a patch.

[`patches/gtexinfo-7.3-gettext-h-collision.patch`](patches/gtexinfo-7.3-gettext-h-collision.patch)
(SHA1 `a82d6b5e1427a9052dfeb20ae4ac140b766e4963`) adds `#undef` for the
twelve `pgettext*` family macros after the include guard of both bundled
copies. Apply by copying it into `devel/gtexinfo/patches/` and recording
its SHA1 in that recipe's `distinfo`, or directly into an extracted tree.

Static analysis (Cppcheck 2.22.0, per-file delta on the patched files,
`--enable=warning,portability`): upstream 0 findings, patched 0 findings
on both headers and on all five patched mutter sources. A full corpus run
per the project recipe happens with profile promotion, not at probe stage.

Second finding in the same native VM build (shared `/usr/pkg` prefix,
aarch64): linking the `ctexi2any` program with `-pie` against the shared
`libtexinfo*` fails with `R_AARCH64_ADR_PREL_PG_HI21 ... recompile with
-fPIC` on `digit_chars`. Handled as build-profile policy, not a recipe
fork: a per-package `CFLAGS+= -fPIC` for `devel/gtexinfo` in the native
mk.conf. The development-toolchain Texinfo 7.3 recipe update
(`current-prerequisites.patch`) is already present in this tree and kept
as the base; neither pkgsrc HEAD nor the profile carried a PIC fix, and
their staging environment did not hit the shared-prefix case.

## Next steps

1. Build `gsettings-desktop-schemas` and `gnome-desktop4` natively in the
   prepared tree, then mutter with the patch set.
2. `mutter --headless --virtual-monitor` smoke test in the VM.
3. Promote the recipes into a `profiles/pantheon` profile with generated
   PLISTs and offer the portability patches upstream.
