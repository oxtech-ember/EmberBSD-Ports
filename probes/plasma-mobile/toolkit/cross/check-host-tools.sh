#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Exercise matching native Qt generators.
set -eu
[ "$#" = 2 ] || { echo "Usage: $0 HOST_QT NEW_WORK" >&2; exit 2; }
qt=$1 work=$2
: "${HOST_CXX:=/usr/bin/c++}"
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
"$qt/bin/lrelease" translation.ts -qm translation.qm > lrelease.log 2>&1
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
    QTranslator translator;
    if (object.property("value").toInt() != 42 || !file.open(QIODevice::ReadOnly)
        || file.readAll() != "Ember Qt host generator check\n"
        || !translator.load("translation.qm")) return 1;
    app.installTranslator(&translator);
    return QCoreApplication::translate("Probe", "input") == "translated" ? 0 : 2;
}
SRC
# These are native macOS framework libraries, never target sysroot libraries.
"$HOST_CXX" -std=c++17 -F"$qt/lib" -I"$qt/include" -I. main.cpp moc_probe.cpp qrc_probe.cpp \
    qmltypes.cpp -framework QtCore -framework QtGui -framework QtWidgets \
    -framework QtQml -Wl,-rpath,"$qt/lib" -o probe > compile.log 2>&1
./probe
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
file probe > architecture.txt
shasum -a 256 probe shader.qsb qmlcache.cpp translation.qm > outputs.sha256
printf '%s\n' 'PASS: Qt 6.12 moc/uic/rcc/lrelease/QML registration, shader/QML rejection and Wayland generation'
