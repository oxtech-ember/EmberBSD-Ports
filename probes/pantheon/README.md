# Pantheon port probe: mutter and its new dependencies

First implementation step of the project's Pantheon direction (registry
debt E25): port **mutter** so that **gala** and the rest of the elementary
desktop can run on EmberBSD. Strategy: only current upstream releases;
every NetBSD adaptation lives in recipe patches here and is offered
upstream once it builds.

## Version pairing

| Component | Version | Source |
| --- | --- | --- |
| mutter | 49.8 (`libmutter-17`, the line gala 8.6.x declares) | download.gnome.org, SHA512 pinned |
| gsettings-desktop-schemas | 51.0 | download.gnome.org, SHA512 pinned |
| gnome-desktop (the `gnome-desktop-4` library) | 51.0 | download.gnome.org, SHA512 pinned |
| gala | 8.6.2 | later probe |

Freshness audit of the native build chain : gtk 3.24.52 and
4.22.4, pango 1.58.2, cairo 1.18.6, gdk-pixbuf 2.44.8,
gobject-introspection 1.86.0, glib2 2.90.1, cmake 4.4.3 — current lines of
the pinned quarterly; the graphics profile pins Mesa 26.2.4,
libdrm 2.4.134, wayland 1.26.0 and wayland-protocols 1.49. No component of
the chain requires a version bump; fixes are patches only, per project
policy.

## Validation record 

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

## Cross-build record

All cross builds run on the development host; boards and VMs receive binary
packages only. Chain state after this pass:

- **ibus 1.5.34nb3** cross-installed in a GTK4 profile: `--disable-gtk3
  --disable-gtk2 --enable-gtk4 --disable-ui --disable-xim --disable-tests`
  (XIM requires gtk2 when gtk3 is off; the GTK3/Vala panel is not built).
  The `im-ibus.so` GTK4 immodule builds. `patch-cross-generators` builds the
  three noinst generators (`gen-internal-compose-table`, `emoji-parser`,
  `unicode-parser`) with `CC_FOR_BUILD` against the host glib, bypasses
  libtool for their links, keeps the dist-shipped compose sequences behind a
  guard, and replaces `G_FILE_TEST_EXISTS` with `G_FILE_TEST_IS_REGULAR`
  (case-insensitive host filesystems match the `compose/` directory).
  Host-run tools (`glib-compile-resources`, `gdbus-codegen`,
  `glib-compile-schemas`, `wayland-scanner`, wayland-protocols datadir) are
  forced through `MAKE_FLAGS` so the install phase sees them too.
- **colord 1.4.8nb2** cross-installed as a library-only profile:
  `-Ddaemon=false -Dgenerated_data=false -Dman=false` plus the new
  `generated_data` meson option (patch guards the `cd-it8` /
  `cd-create_profile` data subdirs). The daemon needs logind-class sessions
  and runs its data generators at build time; both are impossible in cross
  today. Mutter links `libcolord`; the daemon stays a separate follow-up.
- **dbus-glib 0.114nb2** cross-built with the host-built
  `dbus-binding-tool` (homebrew dbus + host glib; scratch prefix) and a
  patch skipping the unguarded `dbus/examples` subdirectory.
- **libgudev 238, libgusb 0.4.9nb1** cross-built with introspection and
  vapi options off (`PKG_OPTIONS.libgudev= -introspection -vapi`).
- **mutter 49.8** recipe corrections: `-Dsystemd=false` is gone in 49.8
  (now `-Dlogind=false`); `-Dtests=disabled` (feature type); gtk3,
  gnome-settings-daemon and startup-notification buildlinks dropped
  (tests-only or optional deps); colord buildlink added (unconditional
  upstream). The six patch SHA1s in `distinfo` were recomputed (the staged
  hashes did not match the patch files) and `patch-mdk_mdk-stream.c`
  joined the set.

**mutter 49.8 cross-built and installed .**
`gvdb` turned out to ship in the mutter tarball (no wrap download);
`glycin-2` is now fully ported:

- **glycin 2.0.8** (new recipe, now in the shared overlay `pkgsrc/graphics/glycin/`): libglycin only
  (`-Dglycin-loaders=false -Dglycin-thumbnailer=false -Dlibglycin-gtk4=false
  -Dintrospection=false`), cross cargo via the packaged rust-bin 1.99 +
  rust-std-aarch64-netbsd (`RUST_TYPE=native`, target linker = wrapper cc).
  A `triplet` meson option patches `--target aarch64-unknown-netbsd` into
  every cargo call (upstream builds for the host only); the meson `rust`
  language is dropped from project() because its cross sanity check cannot
  run; a host-python rst2man-style fix covers `crates-version.py` (tomllib).
  Crate patch: NetBSD has no memfd_create(2), no file seals, no seccomp and
  no bwrap — shared memory falls back to POSIX shm (unlinked object,
  descriptor lifetime), `seal_fd` becomes a no-op and the Linux sandbox
  machinery is cfg-gated; the loader runs unsandboxed until a pledge(2)
  sandbox lands (debt).
- **mutter 49.8** now builds with twelve additional patches beyond the
  original six: pango autoptr redefinition, glibc-only `uint`, vendored
  RenderDoc header platform list, the dma-buf `export_sync_file` UAPI,
  linux-only gating of the `linux-drm-syncobj` staging protocol (sources,
  protocol list and six integration sites), a Linux-only backlight helper,
  a cross `-initfd` detection guard and a direct `meta-backend.h` include.
  Recipe flags: `-Dlogind=false -Dnative_backend=false -Dudev=false
  -Dtests=disabled -Dstartup_notification=false -Dprofiler=false
  -Dxwayland_path=/usr/X11R7/bin/Xwayland` plus the x11-client buildlinks
  (gtk4, the X libraries, atk, lcms2, libei, libdrm, pixman, pango,
  harfbuzz, gsettings-desktop-schemas, gnome-desktop4, glycin,
  libdisplay-info). An install-time rpath fix pre-extends LDFLAGS with
  `/usr/pkg/lib/mutter-17`; meson-generated python tools get the target
  python shebang.
- **granite 7.8.1 cross-built and installed.** The vala language needs a
  host valac: homebrew vala 0.56.19 (the same line as the sysroot) through
  wrappers that add both sysroot vapi directories; meson ignores the
  native-file valac entry, so the tools take PATH precedence
  (`TOOLS_CREATE`). sassc (host brew install) compiles the stylesheets.
  libgee ships no installed vapi in this profile - `gee-0.8.vapi` was
  installed from the dist tarball into the sysroot vapi dir. PLIST
  generated from the destdir.
- **gala 8.6.2 cross-built and installed** (the chain head: `bin/gala`,
  `bin/gala-daemon`, `lib/libgala.so`, plugins). valac via the same
  wrappers with the second vapi dir (granite-7 installs to
  `share/vala/vapi`, not `share/vala-0.56/`); `vapigen` stays unfound so
  gala uses its bundled libmutter-17 vapi files (no GIR needed). ibus-1.0
  vapi was installed from the ibus dist tarball. Recipe work: the GTK3
  fallback dialog daemon is behind a new `gtk3-daemon` option (off); the
  full libmutter-17 pc closure is declared (lcms2, libdisplay-info, the X
  set, colord, glycin, cairo/graphene/gdk-pixbuf/json-glib/schemas/
  libopeninput/libxcb/xkeyboard-config); GCC16 needs
  `-Wno-int-conversion` plus `-Dsighandler_t=sig_t` (the posix vapi types
  SIG_IGN with the glibc-only sighandler_t); and the meson install rpath
  rewrite gets a pass-through slot for the sysroot libmutter-17 path
  (`BUILDLINK_PASSTHRU_RPATHDIRS`), since the pc files are correct and the
  entry only leaks through meson's dependency rpath logic. The
  `gnome-bg-4.vapi` installed by gnome-desktop4 points at
  `libgnome-desktop/gnome-bg*.h`; the headers live under `gnome-bg/` - the
  sysroot copy was corrected in place (gnome-desktop4 recipe needs the
  same fix at promotion time).

**The full Pantheon chain is now cross-built:** mutter 49.8 (libmutter-17)
+ granite 7.8.1 + gala 8.6.2, all installed in the private sysroot with
`gala` as a target ELF.

## Dock chain 

elementary replaced plank with **dock 8.3.3** (GTK4 + granite-7 +
libadwaita). New recipes: **libxmlb 0.3.29nb1** (introspection off - the
shared GI cross machinery is recorded as a promotion-time follow-up for
this leaf), **appstream 1.1.6nb1** (stemming/libstemmer and man off; itstool
comes as a host tool through a cross branch in `mk/tools/itstool.mk`;
host appstreamcli brew binary serves the native release-metadata lookups),
**libadwaita 1.9.4** (library only for now: introspection and vapi are
prepared for the GI cross machinery but blocked on a live query target).
The gtk4 recipe gains the GI cross block and a meson patch (host
generators with `--use-ldd-wrapper`); its GIR build got as far as the Gdk
GType query, which needs the query target back on the network
(ember-rpi5-01.local dropped off mDNS mid-build; ember-vm-01 is not
resolvable from SSH either). Dock itself stops at `--pkg libadwaita-1`:
the vapi is generated from the libadwaita GIR. Nothing here is committed
as done until dock links.

## wingpanel GTK4 port (in progress, not committed)

wingpanel 8.0.4 upstream is still GTK3. Per the project direction the
panel is being ported to GTK4 + granite-7 in `pkgsrc/x11/wingpanel`
(cross tree, WIP): the meson deps move to gtk4/gtk4-wayland/gtk4-x11 +
granite-7; mutter-49 (libmutter-17) support is declared in
wingpanel-interface; the mutter-17 vapi set is taken from the gala
tarball at post-extract; Switch/Container/OverlayIcon/Separator take the
upstream gtk4-branch rewrites (Gtk.Bin removal, style classes, no
GtkSeparator subclassing); FocusManager gains a HAS_MUTTER49
begin_grab_op branch. Eight vala errors remain, and the principal one is
structural: GTK4 no longer exports the wl_surface of a Gdk.Window, which
8.0.4 uses to hand the panel to gala through pantheon-desktop-shell. The
upstream gtk4 branch solves this with gtk4-layer-shell - that small
library is the next port, or the migration waits for upstream.

## Deploy set for ember-rpi5-01 (updated 2026-10-15)

The cross tree collects the deploy set under `rpi5-deploy/`:
`packages/` holds the Pantheon chain (21 packages) and
`packages-full/` holds the complete 118-package dependency closure as
installed and verified on the local QEMU acceptance VM, with an
`install-and-test.sh` that installs both sets, compiles the gsettings
schemas, checks binaries, smokes `--help` for wingpanel and dock, and
prints the console command for the interactive compositor run.

## Validation record : GIR, dock, VM acceptance

- The GIR chain is complete in the cross sysroot through the local QEMU
  acceptance VM (ssh alias `ember-vm-query`, 127.0.0.1:2222): gtk4,
  graphene, and libadwaita (Adw-1.gir, Adw-1.typelib,
  libadwaita-1.vapi). The libadwaita introspect binary links
  `-lgirepository-1.0`; the pkgsrc compiler wrapper strips foreign
  sysroot `-L` paths, so the recipe lifts libgirepository-1.0 into
  `.buildlink/lib` in pre-configure, which the wrapper keeps.
- Two pkgsrc-level fixes were needed on the Darwin cross host and remain
  in the build tree pending fork review: `mk/check/check-files.mk` sorts
  the expected/added file lists with `LC_ALL=C` (the host locale sorted
  `pt_BR` before `pt`, failing every locale-carrying package), and the
  mutter runtime needs `libeis.so.1`, provided by libei 1.6.0nb1 (the
  accepted CM5 Plasma kit binary); the older 1.4.1 recipe disabled
  libeis and its package lacks the library.
- dock 8.3.3 cross-built (GTK4 + granite-7 + libadwaita): valac through
  the host wrappers, protocol code from the host wayland-scanner 1.26.0
  (rebuilt after the /tmp scratch loss; sources now under
  `/Volumes/BigData/EmberBSD/work/ember-wayland26-cross`).
  `bin/io.elementary.dock` is an AArch64 PIE ELF in the sysroot.
- VM acceptance: the full 118-package closure installed with
  `pkg_add -U` on the QEMU VM; `gala --help`, `wingpanel --help`, and
  `dock --help` all load their libraries.

## Not yet done

- colord daemon profile (data generation, sensor plugins, session glue).
- Interactive compositor run on the board console (DRM/KMS) and the E25
  screenshot; the VM smoke covers library loading only.
- libei recipe alignment at 1.6.0 with `libeis` enabled in the profile
  the mutter consumers build from.
- elementary session files (session launcher, portal configuration).

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
