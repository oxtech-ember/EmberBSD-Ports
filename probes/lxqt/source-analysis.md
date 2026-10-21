# LXQt source and helper checks

The upstream source pins and archive hashes are in [sources.tsv](sources.tsv).
The target packages use the common GCC16 AArch64 compiler and EmberBSD sysroot.
Clang Static Analyzer is analysis-only. It produces no target package objects.

## Qt platform plugin

Cppcheck 2.22 compares all five original C++ translation units with their
packaged sources. It uses the ordinary GCC16 compilation database, target
headers, captured target predefined macros and Qt's model. The only C++ source
difference is the package-prefix substitution in `lxqtplatformtheme.cpp`.
The unique findings are equal before and after that substitution.

The inherited `IconPixmap` width/height warnings do not establish a failing
path. The producer sets both fields before appending the pixmap. The D-Bus
reader reads both fields. The remaining reports concern constructors,
reference returns, shadowed names, pointer constness and algorithm selection.
No diagnostic category is suppressed.

The complete-header run retains a Cppcheck preprocessing limitation in Qt's
`qtypes.h` comparison with `SIZE_MAX`. This run is not a clean parser result.
Clang Static Analyzer 23.1.3 accepts `lxqtplatformtheme.cpp` with the actual
target flags and GCC16 C++ headers. Both variants have zero findings.

## libfm-qt optional file attributes

`FileInfo::setFromGFileInfo` can receive a special-file entry without the
optional `standard::content-type` and `unix::mode` attributes. Upstream then
passes the missing content type to `strcmp`. The port checks this pointer
before it derives a file mode. An existing mode is retained by the outer
condition. A special file of unknown type keeps mode zero.

`check-fileinfo-mode.py` extracts the real mode-selection block. It uses real
GIO objects, setters and getters. Thirteen independent cases cover the absent
type, preserved modes, known special types, unknown types and ordinary files.
The original block fails the null case under ASan; the other 12 cases pass.
The guarded block passes all 13 cases under ASan and UBSan.

```sh
python3 probes/lxqt/check-fileinfo-mode.py /absolute/original-libfm-qt \
    /absolute/new-baseline-results --baseline --compiler /absolute/native-cxx \
    --pkg-config /absolute/native-pkg-config \
    --pkgconfig-dir /absolute/native-prefix/lib/pkgconfig
python3 probes/lxqt/check-fileinfo-mode.py /absolute/patched-libfm-qt \
    /absolute/new-port-results --compiler /absolute/native-cxx \
    --pkg-config /absolute/native-pkg-config \
    --pkgconfig-dir /absolute/native-prefix/lib/pkgconfig
```

Cppcheck compares the full changed `fileinfo.cpp` translation unit with target
flags and headers. Its inherited findings remain equal. These include the
uninitialized `blksize_` and `blocks_` members; their complete use paths remain
upstream audit work. Clang Static Analyzer reproduces the null argument before
the guard and reports no finding after it. No ABI field or virtual API changes.

The complete revision-5 comparison covers 80 C++ and seven C source files with
separate actual GCC16 predefined macros and target compilation flags. Cppcheck
finds no new or removed diagnostic. Its C parser uses the C11 model for the
GNU C23 build. The Qt `qstdlibdetection.h` parser report and inherited findings
remain visible. This is not a complete clean source-analysis result.
GCC16 `-fanalyzer` checks the changed `vfs-menu.c` prefix-substitution module
before and after the port. Both runs have zero findings. Review of the other
file-manager paths remains pending.

These native checks instrument the extracted block, not the dependency
libraries or the complete file manager. Valgrind Memcheck does not support the
tested macOS/arm64 host. LeakSanitizer is also unavailable there. ASan/UBSan
are not a Memcheck or leak-checking pass. Target package lifecycle and a desktop
session require separate installed-target checks.

## qtermwidget 2.4.0

Cppcheck 2.22.0 checks all 36 C++ translation units from the ordinary
package compilation database. The recipe and manifest change no C++
source. Baseline and packaged sources have the same 54 diagnostic
lines. No diagnostic category is suppressed. Most findings are
inherited style reports or Cppcheck limitations around Qt-generated
MOC files and macros. Three uninitialized-buffer reports end in
`delete[]` paths without a read from the buffer. No source-level
Clang Static Analyzer run applies to this recipe-only change.

## LXQt helper regressions

The Wayland qdbus helper uses `/bin/sh`, calls Qt's installed qdbus path and
declares `qt6-qttools` as a runtime dependency. `check-wayland-qdbus.py`
applies the actual package patch to the pinned archive and exercises the
helper with a fake qdbus command under `dash`, which rejects Bash-only
parameter substitution. It checks the default labwc shortcuts Win+Enter,
Win+F and Print still invoke `run qterminal`, `run featherpad` and
`run screengrab`, then exercises those commands plus `openmenu`. The data paths
include spaces to check directory splitting and quoting:

```sh
python3 probes/lxqt/check-wayland-qdbus.py \
    /absolute/distfiles/lxqt-wayland-session-0.4.1.tar.xz \
    probes/lxqt/recipes/wayland/lxqt-wayland-session
```

The LXQt CMake finder for `xdg-user-dirs-update` checks a path and does not run
the target program. Cross builds pass the target `/usr/pkg/bin` path and check
that the executable exists in the sysroot. Run the source contract check with
the recipe and target sysroot paths:

```sh
python3 probes/lxqt/check-wayland-target-tool.py \
    probes/lxqt/recipes/wayland/lxqt-wayland-session \
    /absolute/target-sysroot
```

This check does not execute `xdg-user-dirs-update` or start a Wayland session.

The `lxqt-wayland-session-0.4.1nb5` package passes the GCC16 cross build and
pkgsrc package checks. Its archive installs the qdbus helper with a `/bin/sh`
shebang and declares `qt6-qttools` and `xdg-user-dirs` as runtime dependencies.
The configured CMake cache selects `/usr/pkg/bin/xdg-user-dirs-update` from the
target sysroot. The archive SHA256 is
`c3fb976aa621859b909f8038a5b8af6aeb1ef08d91ef5e0d23bfe6bf9dcecfc0`.
The installed helper passed `run qterminal`, `run featherpad`, `run screengrab`
and `openmenu` under host `dash` and `/bin/sh`; package install, removal and
reinstallation passed in an isolated target root. Actual EmberBSD runtime
execution and a full LXQt session remain separate acceptance gates.

The liblxqt backlight helper checks the driver before reading its files.
It accepts one integer from `scanf` and `fscanf` and rejects invalid input.
It releases a previous driver candidate before replacing that candidate.
The driver priority and valid brightness range are unchanged.

Run the regression against a clean original liblxqt archive and the same
source with `patch-backlight-null-driver` applied:

```sh
python3 probes/lxqt/check-backlight.py /absolute/original-liblxqt \
    /absolute/new-baseline-results --baseline
python3 probes/lxqt/check-backlight.py /absolute/patched-liblxqt \
    /absolute/new-port-results
```

The test includes the real source. It uses synthetic files and checks missing
devices, replaced allocation ownership, malformed input and valid boundaries.
It does not access a backlight device. The native run uses ASan and UBSan.
An explicit allocation counter checks the replaced driver strings because
LeakSanitizer is unavailable on the macOS/arm64 host.

Baseline and patched Cppcheck runs use the GCC16 target headers and macros.
The helper's null-driver finding and two GCC `-fanalyzer` ownership findings
are absent after the patch. Clang Static Analyzer checks both the C helper
and its C++ consumer with the target compilation flags. It is analysis-only.
The existing style findings remain visible.
The packaged GCC16 helper also passes the no-device stdin path under an
unprivileged VM user. This check requires an absent `/sys/class/backlight`
and supplies no brightness value. It does not test physical backlight control.

The Qt model uses `Q_MOC_OUTPUT_REVISION=69` from Qt 6.12.
The libqtxdg baseline and patched source have the same unique Cppcheck
diagnostics. Three `strPlusChar` and three `pointerOutOfBounds` reports in
`tst_xdgdirs.cpp` are Qt literal model errors. Qt's `operator""_L1` returns
`QLatin1StringView`; these expressions concatenate strings and `QChar` values.
Clang analysis and the target tests cover these expressions without error.
Cppcheck 2.22 cannot parse the complete expanded Qt system-header configuration;
this separate parser limitation is retained in the analysis receipts.

Two complete libqtxdg upstream test programs pass ten native ASan/UBSan cases
with the existing Qt 6.12 host libraries and common GLib 2.90.1 provider.
Both the library and the test executables use the sanitizer flags.
The native memory run does not cover the directory suite, because Darwin
`QStandardPaths` uses different default directories. The target run covers
all 21 cases.
The native Qt and GLib dependency libraries are not instrumented.
Leak checking remains outside this sanitizer coverage.

The luit recipe declares zlib and the existing common encodings package.
It selects target `locale.alias` and `encodings.dir` paths explicitly.
The configure patch preserves native file checks. In cross mode, the recipe
checks these files in the common sysroot before configuration.

```sh
python3 probes/lxqt/check-luit.py /usr/pkg/bin/luit /absolute/new-luit-results
python3 probes/lxqt/check-luit.py /usr/pkg/bin/luit /absolute/new-target-results \
    --ssh ember-test-host
```

All six upstream check modes and two exact-byte encoding conversions pass
with the GCC16 target binary. The same eight cases pass in a native
ASan/UBSan build. Valgrind Memcheck does not support the tested macOS/arm64
host or EmberBSD/aarch64 guest. These sanitizer runs are not Memcheck runs.

## lxqt-panel 2.4.1

Cppcheck 2.22.0 compares all 168 target compilation commands with GCC16
macros, target headers, Qt 6.12 and C++20. Upstream and packaged sources each
produce 865 normalized diagnostic lines, with no new or removed findings.
Two Qt header `syntaxError` reports remain parser limitations in `qtypes.h`
and `qpixelformat.h`. No diagnostic category is suppressed.

Clang Static Analyzer 23.1.3 checks the four C++ translation units changed by
pkgsrc path substitutions. All upstream and packaged runs exit successfully
with no diagnostics. Clang is used for analysis only; GCC16 builds the target.
