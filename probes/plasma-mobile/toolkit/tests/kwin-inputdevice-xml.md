# KWin input-device XML generation

The native Qt 6.12 `qdbuscpp2xml` tool needs native libdbus when it generates
signatures for complex Qt types. Qt's `QDBusArgumentPrivate::createSignature`
returns an empty signature when its dynamic loader cannot open libdbus.
The tool can then emit `type=""` while returning success.

This affected seven properties in KWin 6.8.0's installed input-device XML.
It prevented Plasma Desktop's real `qdbusxml2cpp` consumer from building.
The native generator dependency belongs to `cross/build-host-tools.sh`.
No KWin property, target Qt marshaller or D-Bus wire type is changed.

Set `HOST_DBUS_PREFIX` to a current native D-Bus development prefix when
running that builder. It must contain headers, the shared library,
`dbus-1.pc` and `lib/cmake/DBus1` exports. The builder links native QtDBus
directly. It records the selected library and metadata hashes.
It verifies both requested and effective direct-link feature values.
Target D-Bus libraries must not enter this host build.

## Repair an existing native build

Use the original native Qt source and build directories. Keep its generators
and other cached build settings. This bounded command rechecks packages and
builds only QtDBus and the two D-Bus generators:

```sh
cmake -S /absolute/host-qt/source/qtbase-everywhere-src-6.12.0 \
    -B /absolute/host-qt/qtbase \
    -UQT_INTERNAL_PREVIOUSLY_FOUND_PACKAGES \
    -UQT_INTERNAL_PREVIOUSLY_SEARCHED_PACKAGES \
    -DDBus1_DIR=/absolute/native-dbus/lib/cmake/DBus1 \
    -DDBus1_LIBRARY:FILEPATH=/absolute/native-dbus/lib/libdbus-1.dylib \
    -DDBus1_INCLUDE_DIR:PATH=/absolute/native-dbus/include/dbus-1.0 \
    -DDBus1_ARCH_INCLUDE_DIR:PATH=/absolute/native-dbus/lib/dbus-1.0/include \
    -DFEATURE_dbus=ON -DFEATURE_dbus_linked=ON
cmake --build /absolute/host-qt/qtbase --parallel 4 \
    --target DBus qdbuscpp2xml qdbusxml2cpp
```

The example uses the macOS shared-library name. The builder selects `.so`
on other hosts. Qt normally disables pkg-config on macOS. Supply the native
D-Bus library and include directories as standard `DBus1` finder inputs;
this avoids changing unrelated Qt feature discovery.

Qt developer builds cache unsuccessful dependency searches.
`QT_FIND_ALL_PACKAGES_ALWAYS` does not remove that cache.
The reset above follows Qt's own `cmake/QtFindPackageHelpers.cmake` contract.
Confirm `FEATURE_dbus_linked:BOOL=ON` and
`QT_FEATURE_dbus_linked:INTERNAL=ON` before accepting the update.
Keep the configuration and build logs with the native input hashes.
A repaired native build must pass the regression below.

Regenerate `KWinInputDBusInterfaces` through the normal KWin package build.
Package revision `nb3` distinguishes the corrected XML from `nb2`.
Rebuild its Plasma Desktop consumer against that package. Do not hand-edit
the installed XML or delete unknown properties to bypass the parser.

## Regression and validation boundary

The check uses the actual KWin `device.h`, both native Qt generators and
Qt's public metatype and marshalling interfaces. Supply the patched target
Qt source/build directory to compare the relevant marshaller sources.
It currently tests a macOS native Qt framework build.

```sh
BASELINE_XML=/absolute/before-fix/org.kde.kwin.InputDevice.xml \
HOST_CXX=/absolute/native/c++ \
    ruby probes/plasma-mobile/toolkit/tests/kwin-inputdevice-xml.rb \
    /absolute/host-qt/qtbase /absolute/kwin-6.8.0 \
    /absolute/target-qtbase-everywhere-src-6.12.0 /absolute/new-results
```

`BASELINE_XML` is optional. When supplied, it must reproduce all seven empty
signatures. The regression proves that no property was removed or added and
that unrelated property types and access flags remain unchanged.
The corrected signatures are `QSizeF=(dd)`, `QRectF=(dddd)` and
`QList<uint>=au`. The generated proxy must pass `qdbusxml2cpp`.
The same consumer must reject a deliberately empty signature.
The C++ test checks both metatype and actual marshalled signatures.
The output includes the real compiler command database and source hashes.

The Qt generator still warns about upstream `Qt::ScreenOrientation` and
`uint32_t` type names. This fix does not remove or hide those warnings.
Source parity and host execution are distinct from target execution.
The same C++ consumer can be cross-built and run on EmberBSD separately.
No target input device, D-Bus property exchange or complete desktop is accepted
by this host regression. It is not a Valgrind run.

## Prepare the target consumer

The same published C++ fixture cross-links with GCC 16.2, common Qt 6.12
and the scoped LLD23 specs. It retains strict compiler and linker diagnostics.
Set `CXX`, `SYSROOT`, `SPECS` and native `PKG_CONFIG` to the audited cross tools.
Set `OUTPUT` to a new file on the development host:

```sh
export PKG_CONFIG_SYSROOT_DIR="$SYSROOT"
export PKG_CONFIG_LIBDIR="$SYSROOT/usr/pkg/qt6/lib/pkgconfig:$SYSROOT/usr/pkg/lib/pkgconfig"
export PKG_CONFIG_PATH=
"$CXX" --sysroot="$SYSROOT" -std=c++20 -O2 -fPIC -Wall -Wextra -Werror \
    -specs="$SPECS" -fno-use-linker-plugin -Wl,-m,aarch64elf \
    -Wl,--no-undefined,--fatal-warnings,-z,relro,-z,now \
    -L"$SYSROOT/usr/pkg/gcc16/lib" -Wl,-rpath,/usr/pkg/gcc16/lib \
    -Wl,-rpath,/usr/pkg/qt6/lib -Wl,-rpath,/usr/pkg/lib \
    probes/plasma-mobile/toolkit/tests/kwin-inputdevice-xml.cpp \
    $("$PKG_CONFIG" --cflags --libs Qt6DBus Qt6Core) -o "$OUTPUT"
```

The prepared file is ELF64/AArch64 and uses `/libexec/ld.elf_so`.
Keep its SHA256, real compile command and input hashes with the package set.
Run that file as the ordinary target user with `timeout 30` and a clean
library environment. Expect three PASS lines and status zero.
This local marshalling check does not require a session bus or input device.
Its target execution remains pending. It does not replace the full-session test.

## Native source and memory checks

Use the generated compilation database for Cppcheck. Use the same native
Qt headers and framework paths for Clang Static Analyzer and ASan/UBSan:

```sh
qt=/absolute/host-qt/qtbase
results=/absolute/regression-results
source=probes/plasma-mobile/toolkit/tests/kwin-inputdevice-xml.cpp
cppcheck --clang=clang++ --project="$results/compile_commands.json" \
    --enable=warning,style,performance,portability --error-exitcode=1 --library=qt
clang++ -std=c++20 -F"$qt/lib" -I"$qt/include" \
    --analyze -Xanalyzer -analyzer-output=text "$source"
clang++ -std=c++20 -fsanitize=address,undefined -fno-omit-frame-pointer -g \
    -F"$qt/lib" -I"$qt/include" "$source" -framework QtCore -framework QtDBus \
    -Wl,-rpath,"$qt/lib" -o "$results/marshaller-sanitized"
ASAN_OPTIONS=halt_on_error=1 UBSAN_OPTIONS=halt_on_error=1:print_stacktrace=1 \
    "$results/marshaller-sanitized"
```

Clang 21 Static Analyzer and the instrumented consumer pass on macOS/arm64.
Cppcheck 2.22 cannot complete this Qt 6.12 fixture: its Clang importer reports
`internalAstError` for a built-in source location. Its ordinary parser cannot
resolve Qt's compiler builtins; actual Clang-preprocessed input also fails in
`qtypes.h`. These are analyzer limitations, not a clean Cppcheck result.
No diagnostics are suppressed. Keep the failed log and retry with a fixed
analyzer. No upstream Qt C++ source changes are part of this repair.

Valgrind does not support this macOS/arm64 host. ASan/UBSan instrument the
consumer only; the existing Qt frameworks are not rebuilt with sanitizers.
This check does not establish leak, uninitialized-value or target-runtime
coverage equivalent to a supported Valgrind Memcheck run.

Origin: EmberBSD (AI-assisted).
