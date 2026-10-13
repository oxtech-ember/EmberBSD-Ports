# Common Qt and Frameworks source candidate

This layer prepares **Qt 6.12.0 LTS** and **KDE Frameworks 6.31.0** for the
common GCC 16 / LLVM 23 userspace migration. It extends the existing
[common build-tools profile](../../../profiles/common-build-tools/README.md).
It does not install another Qt prefix for Plasma. Final package paths remain
`/usr/pkg` and `/usr/pkg/qt6` inside the common staging environment.

**Qtbase, SVG, ShaderTools, ImageFormats, LanguageServer and Declarative 6.12.0 cross packages pass normal package
checks and installation into the build sysroot.** Their [package receipt](cross/qt-packages.md)
also links the accepted CM5 Core/Gui/SVG runtime consumer.
The [Wayland/EGL consumer](tests/qt-wayland-gl/README.md) also passes on V3D
with an isolated labwc output. The [Qt Quick consumer](tests/qt-quick-gpu/README.md)
also passes compiled QML scene/layer pixels on V3D. Each linked receipt defines its package and runtime
scope. Complete Plasma Desktop and HDMI acceptance remain pending.
See the [migration sequence](MIGRATION.md) and the
[actual Mobile graphics contract](../kwin/MOBILE-GRAPHICS-CONTRACT.md).

## Prepare the source tree

```sh
git submodule update --init --depth 1 upstream/pkgsrc
sh scripts/prepare-pkgsrc.sh /absolute/new-pkgsrc plasma-mobile
```

The new export contains the unchanged common Python/Meson/LLVM family and
development-toolchain recipe deltas, followed by this toolkit layer. The
default, `development-toolchain` and `common-build-tools` modes retain their
previous selection. No existing pkgsrc directory is overwritten.

The toolkit also carries iso-codes 4.20.1, the libinotify cross adaptation,
and [tested litehtml 0.10nb1 / gumbo 0.14.1 packages](cross/html.md) for QtTools.

The toolkit includes 22 Qt modules and all 68 Frameworks recipes present
in the pinned pkgsrc, plus Extra CMake Modules. Their original recipes come
from pkgsrc `fff4deb639a1a640476203c80f752fb77b6cb14b`. The shared version files
reject older command-line versions and unprepared Qt/Frameworks recipe paths.
Buildlink requirements select the new versions, including transitive consumers.
Qt's common build and consumer files require GCC 16.2.

[Qt TextToSpeech](tests/qt-speech/README.md) and [KCMUtils](cross/kcmutils.md)
now have complete cross packages and bounded CM5 acceptance.
[libplasma and PlasmaActivities](cross/libplasma.md) also have complete packages;
native KPackage tooling and the non-GLVND EGL provider are checked separately.
[Current Noto fonts](cross/fonts.md) pass installed-data and indexing checks.
[The full KWin dependency migration](cross/desktop-session.md) retains the screen
locker and KCMs. ConsoleKit's real session launcher passes CM5 regressions;
complete desktop, ordinary-user login and device ownership remain pending.
[Full KWin on CM5](cross/cm5-kwin.md) now passes OpenGL/V3D selection and
two Qt Quick pixel lifecycles on a virtual output. HDMI and the separate
Plasma Desktop shell remain outside that acceptance. The separate Desktop 6.7.5
recipe is a source candidate; its complete cross package is not yet accepted.

The [prepared-package workflow](cross/desktop-package-set.md) collects the complete
runtime closure and compiled checks. It includes checksum verification before
installation and isolated Desktop/full-session acceptance runners. Their host
controls pass; a new CM5 session has not yet been executed.

Cross-build on the development host using the [cross workflow](cross/README.md).
The board installs the resulting packages and runs acceptance tests.
For an alternative native build, a private MAKECONF includes the exported
`EMBERBSD-COMMON-TOOLS-MK.CONF`, then
`EMBERBSD-COMMON-GRAPHICS-MK.CONF`,
`EMBERBSD-COMMON-MEDIA-MK.CONF` and finally
`EMBERBSD-PLASMA-TOOLKIT-MK.CONF`. The latter selects GCC 16.2, one worker and
release compiler flags without changing `/etc/mk.conf`. The migrated
Qt Multimedia/KFileMetadata recipes use the
[common FFmpeg9 profile](../../../profiles/common-media/README.md).
The toolkit requires the [common graphics source profile](../../../profiles/common-graphics/README.md)
with Mesa26.2.4nb4/libdrm2.4.134nb2 and disables native GL/GLU/DRM providers.
Qtbase selects its EGL-device PLIST from the canonical package header;
Qtbase configuration and target check-files pass. Runtime plugin discovery remains a gate.
Cross builds use the [cross workflow](cross/README.md). Native tools retain
their host compiler; the cross caller selects parallelism. Package and consumer
acceptance remains separate from source checks.

## Current desktop providers

The toolkit rejects GTK2, SDL 1 and SDL2 recipes. Port each consumer before
adding it to this profile. The policy regression uses the production file:

```sh
BMAKE=/absolute/bmake sh tests/modern-providers.sh mk.conf /absolute/new-results
```

SDL3 3.4.18 now passes full cross packaging and installed CM5 checks.
The migrated Plasma game-controller source passes eight CM5 cases, also with UBSan.
[Provider acceptance and limits](cross/desktop-providers.md) distinguish this
component result from the complete Desktop. Cross builds use the native Wayland scanner.
D-Bus, common Mesa OpenGL, DRM, Wayland and X11 are selected by default.
SDL's IBus backend remains an explicit option. PipeWire, sndio, libudev and
io_uring retain the inherited recipe limits; those backends are not accepted here.

Plasma selects Fcitx5/Qt6 and core libcanberra without mandatory GTK.
The current Fcitx source candidates retain Wayland and the KF6 configuration UI.
Their target packages and the complete desktop closure still require acceptance.
A policy check alone does not establish that every transitive provider is current.

## Provenance and patch decisions

Original pkgsrc RCS identifiers, recipe ownership, upstream licences and
patch explanations are retained. The manifest and adaptations are
AI-assisted EmberBSD work; these changes have not been submitted or accepted
upstream. [sources.tsv](sources.tsv) records original archive URLs and SHA256.
Qt hashes were compared with the official `.sha256` responses. Frameworks 6.31 archive
hashes are checked against the release server's `.sha256` files; this is not a claim
of release-signature verification. The recipes also record BLAKE2s, SHA512,
size and pkgsrc's RCS-filtered patch SHA1.

| Imported patch | Decision for the current toolkit |
| --- | --- |
| QDoc supported-Clang list | Drop: Qt 6.12 already names Clang 23.1 and 22.1. |
| QDoc QualTypeNames include workaround | Drop: Qt's vendored implementation now contains the LLVM 22+ API adaptation and its QDoc-specific behavior. |
| Qt icon theme fallback | Drop: upstream change 763319 is present in the archive. |
| Eight KCodecs `std::format` replacements | Drop: these only compensated for GCC 12. The current profile requires GCC 16 and retains upstream C++20. Native KCodecs checks are still required. |
| Qt file-transfer portal | Require a successful target `O_PATH` compile check. Plain Wayland URI transfer remains available when path-only descriptors are absent; read-only opens are not an equivalent substitute for the portal descriptor contract. |
| Qt syncqt build ordering | Refresh context around the additional generated documentation headers; preserve the pkgsrc dependency. |
| Qt archive-API configure switch | Refresh context; preserve the pkgsrc libarchive workaround. |
| Qt NetBSD thread naming | Refresh context around the VxWorks addition; preserve the NetBSD signature. |
| Qt Quick Test Solaris linker option | Refresh context around the Android target block. |
| Qt audio temporary buffer | Refresh context around the upstream nonblocking annotation; retain the NetBSD alloca branch. |
| Qt FFmpeg VAAPI linkage | Link VAAPI directly on platforms where the Linux/Android stub helpers are unavailable, even when FFmpeg metadata lists `va`. Preserve Linux/Android stub selection. |

The [CUPS dependency delta](current-cups.patch) selects OpenPrinting CUPS 2.4.20
(2026-10-05) for Qt printing. It records the original release archive and SHA256,
updates pkgsrc checksums and retains the existing portability patches. It also
selects GSS headers by target OS and uses pkgsrc's selected Kerberos configuration
script, preventing Darwin framework flags from entering an EmberBSD build.
On 2026-10-11, the GCC16 macOS-to-AArch64 libcups package build, staging checks
and `tests/cups-cross-settings.sh` passed. The test checks the actual configure
outputs and linked target ELF; printing and target runtime are not yet accepted.

The [network prerequisites](cross/network-dependencies.md) now include current
libidn2/GSettings releases and native cross-build generators for libproxy.
The [security prerequisites](cross/security-dependencies.md) and
[KArchive package](cross/archive.md) also have cross-build corrections and
bounded CM5 consumer checks.
[Current libsecret 0.21.8.2](cross/libsecret.md) retains introspection, Vala and
reference documentation. Its native peer-credential regression passes on CM5.
[QCA 2.3.12](cross/qca.md) now includes its OpenSSL provider, target trust store
and relocatable CMake exports. All 25 selected upstream invocations complete
on CM5 after relocating one test-data directory; optional unsupported algorithms
remain untested. Installed KWallet passes 19 upstream rows and independent
D-Bus activation for both compatibility names on CM5.
[KIO and the shortcut service](cross/desktop-frameworks.md) also have full
cross packages and focused installed CM5 tests; the complete desktop is pending.
Their focused source checks, curl metadata regression and CM5 API tests pass;
complete installed desktop acceptance remains pending.

[Native KDocTools](cross/doctools.md) generates documentation without a second
host QtTools/LLVM dependency tree. Its full target package and DocBook recipe
checks pass; target execution remains pending.

[Plasma 6.7.5 prerequisites](cross/plasma-prerequisites.md) now include complete
KWayland, KDecoration, layer-shell-qt and KNightTime cross packages. The installed
KWayland mouse-button wire regression passes on CM5; KWin and the full Plasma
session are not yet accepted.

[Designer plugin recipes](cross/designer-plugins.md) retain the full target payload.
[Breeze generator repairs](cross/breeze.md) preserve input SVG files and reject
XML conversion failures, with native regression and sanitizer checks.

The [Frameworks cross workflow](cross/frameworks.md) records accepted KI18n,
KCoreAddons, KConfig, KCodecs, KGuiAddons and KWindowSystem package builds.
CM5 checks cover configuration persistence, native file events and locale lookup.
Shared-cache operation, remaining Frameworks runtimes and Plasma remain pending.

The remaining pkgsrc patches apply to the verified sources with zero fuzz.
Frameworks 6.31.0 was released on 9 October 2026. Its 69 Frameworks/ECM
archives replace the unbuilt 6.30 candidate; they do not add a parallel provider.
Retaining a portability patch does not establish runtime support for every
platform mentioned by it. No upstream source archive or binary is stored here.

[Current spelling dependencies](cross/spelling.md) now cross-package Aspell,
Hunspell and full Sonnet. CM5 checks cover the Aspell suffix regression, upstream
text/Unicode cases, 172 Hunspell cases and matching native/target language models.
KWin and a complete accelerated Plasma session remain unfinished.

## Reproduce the source checks

Download the original archives listed in sources.tsv to a private directory.
The checks require BSD make, CMake, tar, patch, shasum and OpenSSL with
BLAKE2s support. Set `BMAKE`, `CMAKE` and `OPENSSL` when necessary.

```sh
sh probes/plasma-mobile/toolkit/tests/source-profile.sh \
    /absolute/verified-distfiles /absolute/new-source-check
```

The check covers all 114 archives, recorded patch hashes and forward applications,
corrupted archive rejection, repeated/missing patch rejection, incorrect
unfiltered RCS hashes, recipe/version selection and exact toolkit export.
It compares the exported common recipes and configuration with their existing
owners without repeating their previously accepted source contracts.

`tests/selection.sh TOOLKIT NEW_WORK` executes the production selection blocks
with BSD make. External pkgsrc includes are omitted; it does not replace full
native recipe parsing. It allows the 90 shared-version recipes and rejects
four unprepared recipes and two old version overrides.

`tests/ffmpeg-vaapi.sh PATCHED_QTMULTIMEDIA NEW_WORK` executes the production
CMake VAAPI branch for six platform/metadata combinations. Target creation
is recorded by the fixture; no native library or multimedia playback is
claimed. The original non-Linux `va` branch calls an unavailable stub helper.

`tests/dependencies.sh NEW_WORK` checks common-media selection, old-provider rejection
and the Mesa version/built-in-library constraints through actual BSD make.
`tests/export-lifecycle.sh NEW_WORK` performs successful and injected-failure
exports, checking temporary-archive cleanup and preservation of a caller-owned
archive with the same name as a toolkit distfile. It needs space for two exports.

Package manifests, installed tools, QDoc with real LLVM 23, Qt plugins,
Wayland/OpenGL, codecs, and the complete Mobile workflow require target acceptance.
