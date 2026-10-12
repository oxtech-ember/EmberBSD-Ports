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

## Next steps

1. Build `gsettings-desktop-schemas` and `gnome-desktop4` natively in the
   prepared tree, then mutter with the patch set.
2. `mutter --headless --virtual-monitor` smoke test in the VM.
3. Promote the recipes into a `profiles/pantheon` profile with generated
   PLISTs and offer the portability patches upstream.
