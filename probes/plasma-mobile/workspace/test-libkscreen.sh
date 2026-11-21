#!/bin/sh
# SPDX-License-Identifier: BSD-3-Clause
set -eu
: "${WORKSPACE_ROOT:=$HOME/.cache/emberbsd-plasma-workspace}"
export PATH=/usr/pkg/bin:/usr/pkg/qt6/bin:/usr/X11R7/bin:/usr/bin:/bin
cd "$WORKSPACE_ROOT"
cmake -S src/libkscreen-6.8.3 -B build-libkscreen -DBUILD_TESTING=ON > logs/libkscreen-tests-configure.log 2>&1
cmake --build build-libkscreen --parallel 1 --target testscreenconfig testconfigserializer > logs/libkscreen-tests-build.log 2>&1
export QT_QPA_PLATFORM=offscreen QT_PLUGIN_PATH="$WORKSPACE_ROOT/build-libkscreen/bin"
dbus-run-session -- build-libkscreen/bin/testscreenconfig > logs/libkscreen-tests-screenconfig.log 2>&1
dbus-run-session -- build-libkscreen/bin/testconfigserializer > logs/libkscreen-tests-serializer.log 2>&1
grep Totals: logs/libkscreen-tests-screenconfig.log logs/libkscreen-tests-serializer.log
