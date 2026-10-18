# Electron runtime probe for NetBSD/aarch64 (E12 Blanc browser)

Goal: run Blanc v1.25.0 on EmberBSD/ARM64. Blanc uses Electron and has
no engine abstraction, so this port needs a native Electron runtime.

## Upstream facts (verified 2026-10-17)

- Electron 44.9.0 (latest stable of the 44 line, 2026-10-17) bundles
  Chromium 152.0.7977.167 and Node 24.22.0. The port tracks the latest
  44.x patch release per the current-versions rule; Blanc pins its own
  application JS and runs on this runtime.
- Blanc v1.25.0 uses Electron 44.5.1, MIT license, npm and
  electron-updater. Filter lists are CC BY-SA 3.0+. Blanc/Bananify names
  and logos are trademarks. Do not redistribute Blanc or its lists
  without resolving their terms.
- The official Chromium bucket publishes 152.0.7977.**82** only
  (chromium-browser-official). The .130 patchlevel is not published as
  a tarball. Plan: build the .**82** tree (exact match of the pkgsrc
  `www/chromium` pin and its `chromium-nb` overlay) and adapt the
  Electron patch series from .130 to .82. Both are patch releases of
  the same 152.0.7977 build branch.

## Distfiles (SHA256)

| File | Size | SHA256 | Source |
|---|---|---|---|
| electron-44.9.0.tar.gz | 20553845 | 2b3eef38277bd50537685c67cc3d1674885efa14e5380bc31185992871a65bc3 | github.com/electron/electron tag v44.9.0 |
| node-v24.22.0.tar.xz | 57606320 | 41f97cff2c666f1f8293dc5f85c65e8dd605c16b43fd9febd49ede32ee1e0329 | nodejs.org/dist/v24.22.0 |
| blanc-1.25.0.tar.gz | 155108408 | b241d6b135b0fab5839f5dea6f64fafbdefa4f213b46ffa4a2f78820cb880971 | github.com/bnfy/blanc tag v1.25.0 |
| chromium-152.0.7977.82.tar.xz | 5916124416 | 82a42a16cd9caa49a5bd6d8f226bb2de2646031356e620da05f92cbfddeb35c3 | commondatastorage.googleapis.com/chromium-browser-official |

Stored in the build host's E12 distfile cache. The npm dependency trees
for Electron's JS build and for
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
4. Build Electron's Node 24.22.0 and the JS toolchain parts on the
   host; compile native code with the cross compiler for
   `aarch64--netbsd`.
5. Cross toolchain (owner decision 2026-10-16): the shared GCC16
   cross toolchain (ember-gcc16-toolchain 16.2.0) with the shared
   EmberBSD sysroot, like every other EmberBSD cross profile. The
   upstream `is_clang` default is turned off and the resulting build
   breaks are fixed by patches with recorded provenance; missing
   modern capability is recorded and the port continues.

## Status and boundaries

- Chromium's `libbase.a` milestone is complete. A previous full Chrome
  pass stopped at 41,268 of 85,087 steps with 460 failed jobs.
- The GCC16 cross build of `crypto/nss_util.o` passes with NSS and NSPR
  metadata from the EmberBSD sysroot. The NTLM buffer writer object also
  builds after changing ambiguous parenthesized initialization to brace
  initialization (`SpanWriter` was parsed as a function declaration).
- Fontconfig's bindgen action now generates its Rust bindings from the
  EmberBSD target sysroot with the `aarch64-unknown-netbsd` target triple.
  Its depfile contains EmberBSD headers and no macOS SDK headers. Host
  `libclang` parses the C declarations; GCC16 compiles target C/C++ objects.
  A separate GCC16.2.0 probe that includes the same Fontconfig header emitted
  an AArch64 NetBSD ELF object.
- A full pass on 2026-10-18 was interrupted at 2,142 of 76,506 tasks while
  isolating the bindgen failure. A later regenerated graph scheduled 74,406
  tasks. That attempt reached 771 tasks and failed 271 target actions with
  exit code 127 because the GCC16 toolchain directory was missing from
  `PATH`; those are environment failures, not compiler diagnostics. Resume
  with the common GCC16 `bin` directory in `PATH`.
- The corrected full pass used GCC16 and scheduled 73,904 tasks. It reached
  1,909 tasks before five related failures exposed a GCC error: the defaulted
  `LanguageTag` move constructor was marked `constexpr` while its
  `ImmutableString` member move constructor is not. Removing `constexpr` from
  that constructor fixed the cause. GCC16.2.0 then rebuilt
  `base/i18n/break_iterator.o` successfully. The full pass is being resumed;
  Chromium has not linked yet.
- The resumed graph then exposed two Fontconfig target-OS assumptions. NetBSD
  provides `vasprintf_l` but not `uselocale`, and provides
  `statvfs.f_fstypename`/`fstatvfs`; the bundled Meson config did not select
  those interfaces. NetBSD-specific config fixups now select the locale-safe
  formatter and the `statvfs` branch. GCC16.2.0 rebuilt `fccompat.o` and
  `fcstat.o`. Cppcheck 2.22, GCC16 `-fanalyzer`, and Clang Static Analyzer 21
  reported no findings on those files. The full `chrome` graph is being
  resumed; Chromium has not linked yet.
- No complete Chromium link, Electron runtime, or Blanc package exists.
  Continue the Chrome build and classify actual compiler failures. Partial
  targets are not a Blanc result.
- The source-level adaptation patch is kept separately from this public
  probe summary. It does not imply a complete Chromium build.
- Measure free space before each build. The Chromium source tree and
  build output require about 120 GiB of working space.
- FreeBSD ports carry `devel/electron42` (Chromium 148) at most; use it
  as a structural reference, not as a version match.

Owner: Ports (recipe) and OS (kernel/libc gaps found by the build).
Task: E12 in the private debt registry.
