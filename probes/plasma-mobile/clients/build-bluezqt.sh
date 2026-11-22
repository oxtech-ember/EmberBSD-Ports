#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors. AI-assisted portability probe.
set -eu
# This diagnostic cohort uses NetBSD base libstdc++.so.9.
export CC=/usr/bin/cc CXX=/usr/bin/c++
work=${WORK:-"$HOME/.cache/emberbsd-plasma-support"}
export PATH=/usr/pkg/qt6/bin:/usr/pkg/bin:/usr/bin:/bin
export LC_ALL=en_US.UTF-8
cd "$work"
qt-cmake -S src/bluez-qt-6.26.0 -B build-bluezqt -G Ninja \
 -DCMAKE_C_COMPILER=/usr/bin/cc -DCMAKE_CXX_COMPILER=/usr/bin/c++ \
 -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="$work/prefix" \
 -DCMAKE_SHARED_LINKER_FLAGS=-Wl,--no-fatal-warnings \
 -DCMAKE_MODULE_LINKER_FLAGS=-Wl,--no-fatal-warnings \
 -DKDE_INSTALL_USE_QT_SYS_PATHS=OFF -DBUILD_TESTING=ON \
 -DKF_IGNORE_PLATFORM_CHECK=OFF > logs/bluezqt-configure.log 2>&1
cmake --build build-bluezqt --parallel "${JOBS:-1}" \
 --target KF6BluezQt bluezqtextensionplugin \
 > logs/bluezqt-library-build.log 2>&1
cmake --install build-bluezqt > logs/bluezqt-install.log 2>&1
[ "${CLIENT_LIBRARIES_ONLY:-0}" = 1 ] && exit 0
cmake --build build-bluezqt --parallel "${JOBS:-1}" --target fakebluez managertest qmltests > logs/bluezqt-build.log 2>&1
QT_QPA_PLATFORM=offscreen dbus-run-session -- ctest --test-dir build-bluezqt \
 --output-on-failure --parallel 1 -R '^bluezqt-(managertest|qmltests)$' > logs/bluezqt-test.log 2>&1
