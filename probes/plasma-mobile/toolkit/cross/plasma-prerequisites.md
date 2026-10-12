# Current Plasma prerequisites and real button events

The complete KWayland, KDecoration, layer-shell-qt and KNightTime 6.7.5
packages cross-build with GCC 16.2, common Qt 6.12 and Frameworks 6.31.
They install into the common EmberBSD sysroot. Native generators execute on
the build host; these packages do not require board compilation. Source URLs
and SHA256 are recorded in [sources.tsv](../sources.tsv).

KGlobalAccelD has a prepared source recipe but has not completed packaging.
KIO/KWallet and the full KWin/Plasma session remain separate acceptance gates.
These library packages alone do not establish a working accelerated desktop.

## KWayland mouse-button fix

The imported pkgsrc `fakeinput.cpp` patch guarded Linux input codes behind
`Q_OS_LINUX`. On the target BSD ABI this silently converted supported Qt
buttons to wire button zero. Drop that patch and use the original upstream
mapping with the common `input-headers` build dependency. The raw-code overload
and rejection of unsupported Qt buttons retain upstream behavior.

`tests/kwayland-input/main.cpp` connects the actual installed KWayland client
to a private Wayland server over a socket pair. Four create/destroy cycles
check 56 exact button requests: left, right, middle and a raw side-button code.
Unsupported Qt buttons produce no requests. It does not inject desktop input.

```sh
PKG_CONFIG=/absolute/pkg-config ruby ../tests/kwayland-input/build.rb \
    /absolute/cross-tools /absolute/sysroot /absolute/wayland-scanner \
    /absolute/new-work \
    /absolute/configured-kwayland-source /absolute/original-pkgsrc-patch
```

The optional final arguments build the original faulty implementation with
the same consumer. On CM5, the original fails on event zero (`code=0`, expected
`0x110`); the installed corrected library passes before and after that control.
Normal target package installation and verification of its 52 files passed.
The DSO SHA256 is `37181ae70d106226634bb5aef59a3cb4d5d4d2c8e9c53fde3fa2ae01e63728fc`.
No physical input device or complete compositor was tested by this fixture.

Cppcheck 2.22 was attempted on both actual target-preprocessed implementations.
Both stop at an unsupported `__END_DECLS` construct in the target system header;
this is not a clean static-analysis result. Valgrind was not run: a supported
runner for this target is unavailable. No memory-safety acceptance is claimed.

## Cross-build dependency repairs

- KDE install directories explicitly select target Qt plugins, QML, metatypes
  and documentation. Otherwise ECM queries native Qt and stages host paths.
- CMake pkg-config queries use the common target sysroot. KNotifications now
  finds libcanberra headers there rather than at a nonexistent host `/usr/pkg`.
- layer-shell-qt uses native Qt generators already selected by `QT_HOST_PATH`;
  remove its unused QtTools tool dependency, which rebuilt native LLVM.
- KHolidays uses upstream Flex 2.6.4 from the native tool prefix. Apple Flex
  reports the same release number but generates a different C++ scanner ABI.
  Only the generator is required; the target uses its upstream scanner header
  and `yywrap`. Do not introduce a target libfl dependency for this generator.
- libcanberra 0.30nb25 preserves GTK3, GStreamer and OSS. Its installed logout
  script retains `/bin/sh` rather than the native pkgsrc shell. Upstream's
  latest release remains 0.30; no audio playback has been accepted here.
- [KDocTools native imports](doctools.md) avoid target-root rewriting. KService
  now includes the upstream German and Russian manual pages in its manifest.

Normal complete-package dependency, manifest, interpreter, permissions,
PIE, RELRO, RPATH and build-path checks passed on 2026-10-12.
The selection check covers native/cross target directories and rejects old
Plasma versions and unprepared recipes. Compilation of upstream test binaries
is not their execution; KNightTime and KHolidays runtime acceptance is pending.

| Package | SHA256 |
| --- | --- |
| plasma6-kwayland-6.7.5 | `c9b128079532d5187e977081f1dc6bd085cbb19dd94b54a8efe6462de4228aab` |
| plasma6-kdecoration-6.7.5 | `d69409a1821f5e9770184712486a37c4bc601c245ff7cbda1aaf0fc6fdeb95de` |
| plasma6-layer-shell-qt-6.7.5 | `140b3d891e6b28c5f0cf96cf4e0a3557fbb675d24d3477f3b24dc9b4a01909c3` |
| plasma6-knighttime-6.7.5 | `b9ab17fdb1cb380cf25dad77f04046bcae777a4a2c13433da1712ca45db0e648` |
| kf6-kholidays-6.31.0 | `7917e972154af81b2e20a6a17c88502d93f0a28586a4d070a290f4cc308d4cbd` |
| libcanberra-0.30nb25 | `8f3691dc5122e805b623a754c40f7bef16d1a11ee7e2d551637c83943a4944d0` |
