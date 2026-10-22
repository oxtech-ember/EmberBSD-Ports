# Electron runtime probe for NetBSD/aarch64 (E12 Blanc browser)

Goal: run Blanc v1.25.0 on EmberBSD/aarch64. Blanc uses Electron and has no
engine abstraction, so this port needs the native Electron runtime.

## Source pins

| Component | Pin | Source |
|---|---|---|
| Electron | 44.9.3 (`c542df1ecbc2c2978e8f53f8c7baf602404d166f`) | GitHub tag `v44.9.3` |
| Chromium | 152.0.7977.167 (`dd78960ccd8a03a2fe1f629543d27783885b78e9`) | Electron `DEPS` |
| Node.js | 24.22.0 | Electron `DEPS` |
| Blanc | 1.25.0 (`ff55d5948f5c71e802ba2ac464659ef96e055ca9`) | GitHub tag `v1.25.0` |

Electron's `DEPS` graph is the Chromium source of record. Do not substitute the
pkgsrc `.82` archive. Chromium sources require `gclient`; the older archive does
not match Electron's pinned revision.

| Distfile | Size | SHA256 |
|---|---:|---|
| `v44.9.3.tar.gz` | 20,838,185 | `e4e84b70a501c7dffec78bf037309bfe336daee6886289f94f9ac035ec54d80f` |
| `node-v24.22.0.tar.xz` | 57,606,320 | `41f97cff2c666f1f8293dc5f85c65e8dd605c16b43fd9febd49ede32ee1e0329` |
| `blanc-1.25.0.tar.gz` | 155,108,408 | `b241d6b135b0fab5839f5dea6f64fafbdefa4f213b46ffa4a2f78820cb880971` |

## Target contract

- Build on the developer host. Cross-compile all target objects for
  `aarch64--netbsd` with GCC 16.2.0 and the exported EmberBSD sysroot.
- Keep host tools separate. Xcode Clang may build host-only tools; target
  compilation must use GCC16.
- Enable Linux-conditioned Chromium source dependencies only to fetch their
  shared code. Do not use a Linux sysroot or Linux target objects.
- Adapt the `chromium-nb` and Electron patch sets to the exact Chromium pin.
  Record the overlay revision and every required drift fix.
- Keep Electron's Chromium sandbox enabled. Do not replace Chromium or Electron
  with another browser engine.

## Current status

- Electron and Node distfiles are pinned to the current supported Electron 44.x
  release and its exact Chromium revision.
- The pkgsrc Chromium baseline is 152.0.7977.82 with `chromium-nb` 151.1. A
  per-patch dry run against Electron's 152.0.7977.167 source applied 1,622 of
  1,641 patches. Five patch hunks need adaptation and fourteen targets are
  absent from the Electron tree. A dry run does not establish patch ordering or
  build correctness.
- The NetBSD GCC16 toolchain and cross sysroot are available. Chromium's GN
  target dispatch and the remaining NetBSD source adaptations still need a
  successful generation and build.
- No complete Chromium link, Electron runtime package, Blanc package, or target
  application acceptance run exists yet. Do not treat partial object builds as
  completion.
- Full runtime and application package lifecycle checks remain pending.
- The Blanc source patches select an explicit NetBSD capture descriptor. It
  uses the existing generic Electron/DOM/WebRTC broker, preload and helper.
  All nine runtime and fourteen shared permission hashes remain unchanged.
  A causal host Node24 test fails with `Unsupported capture platform` before
  the change; the patched source passes all 76 focused capture tests. This
  verifies source dispatch and locks. It does not verify native Electron
  startup or NetBSD media capture. Changes to these generic files require
  impact review for Windows and NetBSD.

## Acceptance

Run the installed package in the target VM. Check HTTPS navigation, tabs,
Russian text input, file download, ad blocking, persistent profiles, private
profile cleanup, site permissions, sandbox behavior, and package lifecycle.
Check touch input, media codecs, and hardware acceleration separately. Record
VM image identity, kernel revision, package hashes, and test results.

Blanc is MIT licensed. Its filter lists are CC BY-SA 3.0+, and its name and
logos are trademarks. Resolve redistribution terms before publishing Blanc or
its filter lists.

Owner: Ports (recipe) and OS (kernel/libc gaps).
Task: E12 in the private debt registry.
