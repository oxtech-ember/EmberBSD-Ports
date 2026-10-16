# Electron runtime probe for NetBSD/aarch64 (E12 Blanc browser)

Goal: run the Blanc browser on EmberBSD/ARM64. Blanc v1.25.0 is an
Electron 44.5.1 application without an engine abstraction, so the port
needs a native Electron runtime first.

## Upstream facts (verified 2026-10-16)

- Blanc v1.25.0: Electron 44.5.1, MIT license, npm + electron-updater.
  Filter lists are CC BY-SA 3.0+; Blanc/Bananify names and logos are
  trademarks. Build for internal acceptance; do not redistribute.
- Electron 44.5.1 bundles Chromium 152.0.7977.130 and Node 24.21.0.
- The official Chromium bucket publishes 152.0.7977.**82** only
  (chromium-browser-official). The .130 patchlevel is not published as
  a tarball. Plan: build the .**82** tree (exact match of the pkgsrc
  `www/chromium` pin and its `chromium-nb` overlay) and adapt the
  Electron patch series from .130 to .82. Both are patch releases of
  the same 152.0.7977 build branch.

## Distfiles (SHA256)

| File | Size | SHA256 | Source |
|---|---|---|---|
| electron-44.5.1.tar.gz | 20284163 | 798e7647950ce10d6715892b5ee3c05af71d7f785dddb23d87c6f26f18b37363 | github.com/electron/electron tag v44.5.1 |
| node-v24.21.0.tar.xz | 57357488 | a6f54defb6fd7c84f41dba13d61e78e9b4e0961712cf61f29715c05f5ced94fc | nodejs.org/dist/v24.21.0 |
| blanc-1.25.0.tar.gz | 155108408 | b241d6b135b0fab5839f5dea6f64fafbdefa4f213b46ffa4a2f78820cb880971 | github.com/bnfy/blanc tag v1.25.0 |
| chromium-152.0.7977.82.tar.xz | 5916124416 | pending download (disk space gate) | commondatastorage.googleapis.com/chromium-browser-official |

Stored under `/Volumes/BigData/EmberBSD/distfiles/e12-electron/` on the
build host. The npm dependency trees for Electron's JS build and for
Blanc are fetched to an offline mirror with the host Node 24 toolchain
during the fetch phase, following the `local-chat/mattermost` pattern:
Node runs on the host, its products are target artifacts.

## Build plan

1. Extract the Chromium 152.0.7977.82 tree; it is self-contained like
   the pkgsrc `www/chromium` distfile.
2. Apply the `chromium-nb` overlay knowledge from the vendored pkgsrc
   pin (`upstream/pkgsrc/www/chromium`, submodule `fff4deb639a1`):
   GN arguments, NetBSD system-library substitutions, and the patch
   series for exactly this Chromium version.
3. Apply the Electron patch series (`patches/chromium` of the Electron
   tag) re-targeted from .130 to .82; record every drift fix.
4. Build Electron's Node 24.21.0 and the JS toolchain parts on the
   host; compile native code with the cross compiler for
   `aarch64--netbsd`.
5. Cross toolchain (owner decision 2026-10-16): the shared GCC16
   cross toolchain (ember-gcc16-toolchain 16.2.0) with the shared
   EmberBSD sysroot, like every other EmberBSD cross profile. The
   upstream `is_clang` default is turned off and the resulting build
   breaks are fixed by patches with recorded provenance; missing
   modern capability is recorded and the port continues.

## Status and boundaries

- Recipe skeletons only; nothing builds yet.
- Gate: the build host volume needs ~120 GiB free for the Chromium
  tree and build output; see the space audit before expanding.
- FreeBSD ports carry `devel/electron42` (Chromium 148) at most; use it
  as a structural reference, not as a version match.

Owner: Ports (recipe) and OS (kernel/libc gaps found by the build).
Task: E12 in the private debt registry.
