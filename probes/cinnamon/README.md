# Cinnamon port probe: Wayland session, GTK3-free profile

Port of the Cinnamon desktop (Linux Mint) to EmberBSD, per the project
direction: the session runs on **Wayland** and the stack carries **no
GTK3** (consumers are ported to GTK4, as done for wingpanel in the
Pantheon probe).

Upstream line: `master.mint27` (the Cinnamon 6.8 development line where
the Wayland session is complete; 6.8 removes the "experimental" label).
No 6.8.x tags exist yet, so every component is pinned by commit SHA
(2026-10-16 clones, recorded in each `distinfo` and in the build
workspace `pinned-shas.txt`).

## Components and pins

| Recipe | Upstream | Pin (SHA) |
| --- | --- | --- |
| lang/mozjs140 | firefox-140.17.0esr source | archive.mozilla.org tarball, SHA512 in distinfo |
| lang/cjs | cjs 140.1 | 84e7840ce148b75f9d38b57d82cdc9a47dd3a7eb |
| x11/cinnamon-menus | 6.7.1 | 1461debf15c829672f4732b141d11fa00ec50d30 |
| x11/cinnamon-desktop | 6.7.9 | 6c6c48d7c87359b34b5812486d364fde3ed730ed |
| wm/muffin | 6.7.9 | 17c958413753feafdbd5d58dc1e420f72a5f1859 |
| x11/cinnamon (pending) | 6.7.9+ | c6313408f90e4eec62ec7cd3b7e8f0e90d2713e0 |
| cinnamon-session (pending) | 6.7.6 | 2f256e0acf0130e16b156cd3e8f53dd576b2e31a |
| cinnamon-settings-daemon (pending) | 6.7.6 | 56e13452712baba646e8b855cd6b8669d1be6b1a |
| xapp (excluded, see below) | 3.3.7 | 3e891b0e63f37d5b67c5198fd29543eb1f3b831d |
| nemo, control-center (pending) | 6.7.x | see pinned-shas.txt |

## Profile decisions

- **mozjs140** replaces the pkgsrc mozjs128 recipe basis: Firefox 140's
  js/src no longer references cbindgen (checked in the 140.17.0esr
  tarball), and `old-configure.in` is gone, so that patch is dropped.
  The build-only clang dependency is removed: everything compiles with
  the shared cross GCC16. Host rust comes from rust-bin +
  rust-std-aarch64-netbsd (librsvg cross pattern).
- **cjs** builds with no GTK at all (all gtk deps are optional upstream);
  the shell loads typelibs at runtime.
- **cinnamon-desktop** is cut to the Wayland-relevant subset: enums,
  wall clock, idle monitor, languages, pnp ids, xkb info, edid. The
  GTK3-era RandR, background and thumbnail code is not built; the
  mint27 wallpaper painter is the GTK4 + layer-shell daemon inside the
  cinnamon package itself.
- **muffin**: the GTK3 server-side decoration stack (ui.c/frames.c/
  theme.c) is replaced by no-op stubs (see patches); X11 clients under
  the Wayland session get no server-side decorations — recorded
  boundary. Remote desktop/screencast (PipeWire) is off; native DRM
  backend is on (libinput from libopeninput, gudev from libudev-bsd).
  Portability patches (dma-buf UAPI, sd-login fallback, memfd, Xwayland
  socket) are being ported by hand from probes/pantheon/mutter — the
  mutter 49 patches do not apply to muffin's older base.
- **xapp is excluded from the session core**: the shell uses none of its
  C API, and the only JS consumer (`XApp.GpuOffloadHelper`, meaningless
  without switcheroo hardware) is guarded in a patch. A GTK4 xapp port
  is a prerequisite debt for nemo and cinnamon-control-center.
- Shell start pins `Gtk/Gdk 3.0` in environment.js; the St port moves
  them to 4.0. St's GTK surface is small: GtkIconTheme in
  st-texture-cache (symbolic recoloring!), GtkSettings in
  st-theme-context, GtkDirectionType enums. GTK4 removed the pixbuf
  icon API, so symbolic icons will load through the icon's file via
  librsvg with a CSS color override (librsvg GIR is in the profile).
- **Translations** are not merged in this line (components ship
  LINGUAS but no .po; translations live in the separate
  cinnamon-translations repo and are merged at release packaging).
  English-only until that recipe lands.

## Cross workspace

- Tree: `build/cinnamon-cross/pkgsrc` (common-graphics profile).
- MAKECONF: `build/cinnamon-cross/mk.conf` (llvm23-cross base +
  common-graphics cross; host glib tools, wayland-scanner, python3.15).
- Chain driver: `build/cinnamon-cross/chain.sh`
  (mozjs140 → cjs → cinnamon-menus → cinnamon-desktop → gcr → muffin).
- GI query host: `ember-cm5-01.local` (config
  `build/cinnamon-cross/gi-query.json`; utmctl is unusable from SSH).
- Distfiles: `/private/tmp/ember-common-stack/distfiles` (symlinked to
  BigData). Firefox tarball 637 MB.

## Gotchas found

- pkgsrc caches the resolved dependency list in the work dir
  (`.depends`): recipe edits do not take effect until the work dir is
  cleaned.
- The common-graphics cross gate rejects native builds of packages
  that are not cross-aware tool recipes; do not add plain TOOL_DEPENDS
  (use host tools in TOOLBASE or special -tools recipes).
- The global gitignore hides `Makefile` names: `git add -f` for probe
  recipes.

## Status

- [x] Recipes: mozjs140, cjs, cinnamon-menus, cinnamon-desktop, muffin
- [ ] mozjs140 build (in progress; extraction of the Firefox tree is
      slow on the USB drive)
- [ ] cjs, cinnamon-menus, cinnamon-desktop builds
- [ ] muffin build + hand-ported NetBSD patches + GIR (Meta, Clutter,
      Cogl) through the CM5 query host
- [ ] cinnamon shell: St → GTK4, environment.js pins, tray cut,
      generic-container, gcr-base, polkit GIR check
- [ ] cinnamon-session, cinnamon-settings-daemon (GTK4 patches)
- [ ] VM acceptance: nested Wayland session under labwc
- [ ] Static analysis delta per project recipe
