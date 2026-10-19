# LXQt extension source checks

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

The broader initial libfm-qt comparison covers 80 C++ and seven C source files.
Its C++ macro profile does not qualify the C subset. Its system-header parser
reports and inherited findings remain visible. This comparison establishes no
complete source-analysis pass. Separate C analysis and review of the remaining
file-manager paths remain pending.

These native checks instrument the extracted block, not the dependency
libraries or the complete file manager. Valgrind Memcheck does not support the
tested macOS/arm64 host. LeakSanitizer is also unavailable there. ASan/UBSan
are not a Memcheck or leak-checking pass. Target package lifecycle and a desktop
session require separate installed-target checks.
