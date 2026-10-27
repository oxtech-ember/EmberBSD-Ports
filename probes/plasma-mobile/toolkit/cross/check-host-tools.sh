#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Exercise matching native Qt generators.
set -eu
[ "$#" = 2 ] || { echo "Usage: $0 HOST_QT NEW_WORK" >&2; exit 2; }
qt=$1 work=$2
: "${HOST_CC:?Set the native C compiler}"
: "${HOST_CXX:?Set the native C++ compiler}"
: "${CMAKE:?Set native CMake}"
: "${NINJA:?Set native Ninja}"
: "${FILE:?Set the file inspection command}"
profile=${QT_HOST_TOOLS_PROFILE:-full}
case "$profile" in full|quick) ;; *) echo 'Invalid Qt host profile' >&2; exit 2;; esac
case "$qt:$work" in /*:/*) ;; *) echo 'Absolute paths required' >&2; exit 2;; esac
[ "$("$qt/bin/qmake" -query QT_VERSION)" = 6.12.0 ]
mkdir "$work"
cd "$work"
cat > probe.h <<'SRC'
#include <QtCore/QObject>
#include <QtQml/qqmlregistration.h>
class Probe : public QObject {
    Q_OBJECT
    QML_ELEMENT
    Q_PROPERTY(int value READ value CONSTANT)
public:
    int value() const { return 42; }
};
SRC
cat > form.ui <<'SRC'
<ui version="4.0"><class>Form</class><widget class="QWidget" name="Form">
<property name="windowTitle"><string>Ember host probe</string></property>
</widget><resources/><connections/></ui>
SRC
printf 'Ember Qt host generator check\n' > payload.txt
cat > resources.qrc <<'SRC'
<RCC><qresource prefix="/probe"><file>payload.txt</file></qresource></RCC>
SRC
cat > translation.ts <<'SRC'
<TS version="2.1" language="en"><context><name>Probe</name><message>
<source>input</source><translation>translated</translation>
</message></context></TS>
SRC
"$qt/libexec/moc" -F"$qt/lib" -I"$qt/include" --output-json probe.h -o moc_probe.cpp
"$qt/libexec/uic" form.ui -o ui_form.h
"$qt/libexec/rcc" resources.qrc -o qrc_probe.cpp
if [ "$profile" = full ]; then
    "$qt/bin/lrelease" translation.ts -qm translation.qm > lrelease.log 2>&1
fi
"$qt/libexec/qmltyperegistrar" --import-name Ember.Probe --major-version 1 \
    --minor-version 0 --foreign-types "$qt/src/corelib/meta_types/qt6core_metatypes.json" --generate-qmltypes probe.qmltypes \
    -o qmltypes.cpp moc_probe.cpp.json > qmltyperegistrar.log 2>&1
[ ! -s qmltyperegistrar.log ]
grep -q 'Probe' probe.qmltypes
cat > main.cpp <<'SRC'
#include "probe.h"
#include "ui_form.h"
#include <QtCore/QCoreApplication>
#include <QtCore/QFile>
#include <QtCore/QTranslator>
void compile_ui(QWidget *widget) { Ui::Form form; form.setupUi(widget); }
int main(int argc, char **argv) {
    QCoreApplication app(argc, argv);
    Probe object;
    QFile file(":/probe/payload.txt");
    if (object.property("value").toInt() != 42 || !file.open(QIODevice::ReadOnly)
        || file.readAll() != "Ember Qt host generator check\n") return 1;
#ifdef CHECK_TRANSLATIONS
    QTranslator translator;
    if (!translator.load("translation.qm")) return 2;
    app.installTranslator(&translator);
    if (QCoreApplication::translate("Probe", "input") != "translated") return 3;
#endif
    return 0;
}
SRC
cat > CMakeLists.txt <<'SRC'
cmake_minimum_required(VERSION 3.24)
project(QtGeneratorCheck LANGUAGES C CXX)
find_package(Qt6 6.12 REQUIRED COMPONENTS Core Gui Widgets Qml)
add_executable(probe main.cpp moc_probe.cpp qrc_probe.cpp qmltypes.cpp)
target_compile_features(probe PRIVATE cxx_std_17)
target_include_directories(probe PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}")
target_link_libraries(probe PRIVATE Qt6::Core Qt6::Gui Qt6::Widgets Qt6::Qml)
if(CHECK_TRANSLATIONS)
    target_compile_definitions(probe PRIVATE CHECK_TRANSLATIONS)
endif()
SRC
translations=OFF
[ "$profile" != full ] || translations=ON
"$CMAKE" -S . -B build -G Ninja -DCMAKE_MAKE_PROGRAM="$NINJA" \
    -DCMAKE_C_COMPILER="$HOST_CC" -DCMAKE_CXX_COMPILER="$HOST_CXX" \
    -DCMAKE_PREFIX_PATH="$qt" -DCHECK_TRANSLATIONS="$translations" > configure.log 2>&1
"$CMAKE" --build build > compile.log 2>&1
./build/probe
cat > shader.vert <<'SRC'
#version 440
layout(location = 0) in vec4 position;
void main() { gl_Position = position; }
SRC
"$qt/bin/qsb" --glsl '100 es,120,150' --hlsl 50 --msl 12 shader.vert \
    -o shader.qsb > qsb.log 2>&1
"$qt/bin/qsb" -d shader.qsb > shader.dump
test -s shader.qsb
cat > main.qml <<'SRC'
import QtQml
QtObject { property int answer: 6 * 7 }
SRC
"$qt/libexec/qmlcachegen" --only-bytecode --resource-path /main.qml \
    -o qmlcache.cpp main.qml > qmlcachegen.log 2>&1
test -s qmlcache.cpp
printf 'not valid GLSL\n' > invalid.vert
if "$qt/bin/qsb" invalid.vert -o invalid.qsb > invalid-shader.log 2>&1; then
    echo 'Invalid shader was accepted' >&2; exit 1
fi
printf 'import QtQml\nQtObject { property int broken: }\n' > invalid.qml
if "$qt/libexec/qmlcachegen" --only-bytecode --resource-path /invalid.qml \
    -o invalid.cpp invalid.qml > invalid-qml.log 2>&1; then
    echo 'Invalid QML was accepted' >&2; exit 1
fi
cat > protocol.xml <<'SRC'
<protocol name="ember_probe"><interface name="ember_probe" version="1">
<request name="destroy" type="destructor"/><event name="value"><arg name="value" type="uint"/></event>
</interface></protocol>
SRC
"$qt/libexec/qtwaylandscanner" client-header protocol.xml > protocol.h
"$qt/libexec/qtwaylandscanner" server-header protocol.xml > server.h
grep -Eq 'class[[:space:]]+ember_probe' protocol.h
grep -Eq 'class[[:space:]]+ember_probe' server.h
cat > vector.svg <<'SRC'
<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16">
<path d="M 1 1 L 15 1 L 8 15 Z" fill="#e03020"/>
</svg>
SRC
QT_QPA_PLATFORM=minimal "$qt/bin/svgtoqml" --no-assume-trusted-source \
    vector.svg vector.qml > svgtoqml.log 2>&1
grep -q 'ShapePath' vector.qml
"$qt/libexec/qmlcachegen" --only-bytecode --resource-path /vector.qml \
    -o vector-cache.cpp vector.qml > vector-cache.log 2>&1
[ -s vector-cache.cpp ]
if QT_QPA_PLATFORM=minimal "$qt/bin/svgtoqml" missing.svg missing.qml > missing-svg.log 2>&1; then
    echo 'Missing SVG was accepted' >&2; exit 1
fi
"$FILE" build/probe > architecture.txt
shasum -a 256 build/probe shader.qsb qmlcache.cpp vector.qml vector-cache.cpp > outputs.sha256
[ "$profile" != full ] || shasum -a 256 translation.qm >> outputs.sha256
printf '%s\n' "PASS: Qt 6.12 $profile host generators, compiled fixture, SVG/shader/QML rejection and Wayland generation"
